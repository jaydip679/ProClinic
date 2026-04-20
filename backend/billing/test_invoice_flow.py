"""
billing/test_invoice_flow.py
─────────────────────────────
Tests for:
  A. Appointment time display (timezone correctness in API)
  B. Invoice total calculation (grand_total persisted correctly)
"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from billing.models import Invoice, InvoiceItem
from patients.models import Patient

User = get_user_model()


class AppointmentTimeDisplayTest(TestCase):
    """
    Issue A: api_patient_appointments must return local time, not UTC.

    The system uses Asia/Kolkata (UTC+5:30).  An appointment stored at
    UTC 20:00 on day D is actually 01:30 IST on day D+1.  The API label
    must show 01:30, not 20:00.
    """

    def setUp(self):
        self.client = Client()
        self.accountant = User.objects.create_user(
            username='acct_tz', password='pw', role='ACCOUNTANT'
        )
        self.doctor = User.objects.create_user(
            username='dr_tz', password='pw', role='DOCTOR'
        )
        self.patient_user = User.objects.create_user(
            username='pat_tz', password='pw', role='PATIENT'
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='Timezone',
            last_name='Test',
            date_of_birth='1990-01-01',
        )

        # Create a completed appointment with a known UTC time.
        # UTC 20:00 → IST 01:30 (next calendar day).
        # Create with a safe future time first then use queryset.update() to
        # bypass clean() validation (which rejects past times).
        future = timezone.now() + timedelta(hours=1)
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_time=future,
            status='SCHEDULED',
            created_by=self.doctor,
        )
        target_time = timezone.datetime(2026, 5, 10, 20, 0, 0, tzinfo=__import__('datetime').timezone.utc)
        Appointment.objects.filter(pk=appt.pk).update(
            scheduled_time=target_time,
            status='COMPLETED',
        )
        appt.refresh_from_db()
        self.appt = appt

    def test_api_returns_local_time_not_utc(self):
        """Label must contain '01:30', not '20:00'."""
        self.client.login(username='acct_tz', password='pw')
        url = reverse('api_patient_appointments') + f'?patient_id={self.patient.pk}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['appointments']), 1)
        label = data['appointments'][0]['label']
        # IST time should be 01:30
        self.assertIn('01:30', label,
                      f"Expected IST time '01:30' in label, got: {label}")
        # UTC time must NOT appear
        self.assertNotIn('20:00', label,
                         f"UTC time '20:00' must not appear in label, got: {label}")


class InvoiceTotalCalculationTest(TestCase):
    """
    Issue B: Invoice totals must persist correctly for line items totalling
    much more than the ₹50 default consultation fee.
    """

    def setUp(self):
        self.client = Client()
        self.accountant = User.objects.create_user(
            username='acct_total', password='pw', role='ACCOUNTANT'
        )
        self.doctor = User.objects.create_user(
            username='dr_total', password='pw', role='DOCTOR'
        )
        self.patient_user = User.objects.create_user(
            username='pat_total', password='pw', role='PATIENT'
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='Bill',
            last_name='Test',
            date_of_birth='1990-01-01',
        )

    def _post_invoice(self, subtotal, grand_total, paid=0, discount=0, tax=0,
                      items=None):
        """Helper: POST to generate_invoice with explicit totals."""
        if items is None:
            items = [
                ('CONSULTATION', 'General Consultation', '', 1, 50.00),
                ('MEDICINE', 'Paracetamol', 'After food', 2, 225.00),
            ]
        post = {
            'patient': self.patient.pk,
            'status': 'UNPAID',
            'subtotal': str(subtotal),
            'grand_total': str(grand_total),
            'paid_amount': str(paid),
            'due_amount': str(grand_total - paid),
            'discount_amount': str(discount),
            'tax_amount': str(tax),
        }
        for (itype, name, notes, qty, cost) in items:
            post.setdefault('item_type[]', []).append(itype)
            post.setdefault('service_name[]', []).append(name)
            post.setdefault('notes[]', []).append(notes)
            post.setdefault('quantity[]', []).append(qty)
            post.setdefault('unit_cost[]', []).append(cost)

        self.client.login(username='acct_total', password='pw')
        return self.client.post(reverse('generate_invoice'), post, follow=True)

    def test_invoice_total_500_saved_correctly(self):
        """₹500 total (₹50 consult + 2×₹225 medicine) is persisted."""
        items = [
            ('CONSULTATION', 'Consultation', '', 1, 50.00),
            ('MEDICINE', 'Paracetamol', 'After food', 2, 225.00),
        ]
        self._post_invoice(subtotal=500, grand_total=500, items=items)

        invoice = Invoice.objects.filter(patient=self.patient).order_by('-created_at').first()
        self.assertIsNotNone(invoice)
        from decimal import Decimal
        self.assertEqual(invoice.grand_total, Decimal('500.00'))
        self.assertEqual(invoice.subtotal, Decimal('500.00'))
        self.assertNotEqual(invoice.grand_total, Decimal('50.00'),
                            "Grand total must not be locked at ₹50 consultation fee")

    def test_invoice_total_1000_saved_correctly(self):
        """₹1000 total is persisted correctly."""
        items = [
            ('CONSULTATION', 'Consultation', '', 1, 50.00),
            ('MEDICINE', 'Amoxicillin', '3×daily', 5, 190.00),
        ]
        self._post_invoice(subtotal=1000, grand_total=1000, items=items)

        invoice = Invoice.objects.filter(patient=self.patient).order_by('-created_at').first()
        self.assertIsNotNone(invoice)
        from decimal import Decimal
        self.assertEqual(invoice.grand_total, Decimal('1000.00'))

    def test_consultation_fee_does_not_override_total(self):
        """Consultation fee of ₹50 must not reset a ₹750 total."""
        items = [
            ('CONSULTATION', 'Consultation', '', 1, 50.00),
            ('MEDICINE', 'Metformin', 'Daily', 10, 70.00),
        ]
        self._post_invoice(subtotal=750, grand_total=750, items=items)

        invoice = Invoice.objects.filter(patient=self.patient).order_by('-created_at').first()
        self.assertIsNotNone(invoice)
        from decimal import Decimal
        self.assertEqual(invoice.grand_total, Decimal('750.00'))

    def test_invoice_line_items_saved(self):
        """Line items matching the POST data are saved to the database."""
        items = [
            ('CONSULTATION', 'Consultation', '', 1, 50.00),
            ('MEDICINE', 'Ibuprofen', '2×daily', 3, 150.00),
        ]
        self._post_invoice(subtotal=500, grand_total=500, items=items)

        invoice = Invoice.objects.filter(patient=self.patient).order_by('-created_at').first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.items.count(), 2)

    def test_totals_correct_after_reopen(self):
        """Grand total is the same when the invoice is fetched from the DB."""
        items = [
            ('CONSULTATION', 'Consultation', '', 1, 50.00),
            ('MEDICINE', 'Panadol', 'TDS', 4, 100.00),
        ]
        self._post_invoice(subtotal=450, grand_total=450, items=items)

        invoice = Invoice.objects.filter(patient=self.patient).order_by('-created_at').first()
        from decimal import Decimal
        pk = invoice.pk
        # Re-fetch from DB (simulate reopening)
        refreshed = Invoice.objects.get(pk=pk)
        self.assertEqual(refreshed.grand_total, Decimal('450.00'))
