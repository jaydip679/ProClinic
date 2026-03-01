from datetime import timedelta

from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from accounts.models import CustomUser
from audit.models import AuditLog
from billing.models import Invoice
from patients.models import Patient
from appointments.models import Appointment
from publications.models import Publication
from prescriptions.models import Prescription, PrescriptionItem


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('choose_login')


def design_system(request):
    return render(request, 'prototype/design_system.html')


def prototype_prescription_a4(request):
    return render(
        request,
        'prototype/prescription_a4.html',
        {'today': timezone.localdate()},
    )


def prototype_invoice_a4(request):
    return render(
        request,
        'prototype/invoice_a4.html',
        {'today': timezone.localdate()},
    )


def permission_error(request):
    return render(request, 'prototype/permission_error.html', status=403)


@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    context = {
        'role': user.role,
        'today': today,
    }

    if user.role == 'ADMIN':
        context.update({
            'total_staff': CustomUser.objects.exclude(role='PATIENT').count(),
            'total_patients': Patient.objects.count(),
            'today_appointments': Appointment.objects.filter(scheduled_time__date=today).count(),
            'daily_logins': AuditLog.objects.filter(action_type='LOGIN', timestamp__date=today).count(),
            'pending_papers': Publication.objects.filter(status='PENDING').count(),
            'audit_feed': AuditLog.objects.order_by('-timestamp')[:8],
            'deletion_logs': AuditLog.objects.filter(action_type='DELETE').order_by('-timestamp')[:5],
            'support_queue': Appointment.objects.filter(status__in=['CANCELLED', 'NOSHOW']).count(),
        })

    elif user.role == 'DOCTOR':
        context.update({
            'upcoming_appointments': Appointment.objects.filter(
                doctor=user,
                status='SCHEDULED',
                scheduled_time__gte=now,
            ).select_related('patient').order_by('scheduled_time')[:8],
            'my_patient_count': Patient.objects.filter(appointments__doctor=user).distinct().count(),
            'my_prescription_count': Prescription.objects.filter(doctor=user).count(),
            'my_pending_research': Publication.objects.filter(doctor=user, status='PENDING').count(),
            'my_recent_visits': Appointment.objects.filter(
                doctor=user
            ).select_related('patient').order_by('-scheduled_time')[:6],
        })

    elif user.role == 'RECEPTIONIST':
        context.update({
            'today_bookings': Appointment.objects.filter(
                created_by=user,
                created_at__date=today,
            ).count(),
            'total_today_slots': Appointment.objects.filter(scheduled_time__date=today).count(),
            'new_patient_registrations': Patient.objects.filter(created_at__gte=week_ago).count(),
            'walk_in_followups': Appointment.objects.filter(
                status='SCHEDULED',
                scheduled_time__date=today,
            ).select_related('patient', 'doctor').order_by('scheduled_time')[:10],
            'reschedule_queue': Appointment.objects.filter(
                status__in=['CANCELLED', 'NOSHOW']
            ).select_related('patient', 'doctor').order_by('-created_at')[:8],
        })

    elif user.role == 'ACCOUNTANT':
        paid_total = Invoice.objects.filter(status='PAID').aggregate(total=Sum('total_amount'))['total'] or 0
        pending_total = Invoice.objects.filter(status__in=['UNPAID', 'PARTIAL']).aggregate(total=Sum('total_amount'))['total'] or 0
        context.update({
            'paid_total': paid_total,
            'pending_total': pending_total,
            'gst_estimate': paid_total * 0.18,
            'unpaid_invoices': Invoice.objects.filter(status='UNPAID').count(),
            'recent_invoices': Invoice.objects.select_related('patient').order_by('-updated_at')[:10],
        })

    elif user.role == 'PHARMACIST':
        context.update({
            'today_prescriptions': Prescription.objects.filter(created_at__date=today).count(),
            'total_medicine_lines': PrescriptionItem.objects.count(),
            'dispense_queue': Prescription.objects.select_related('patient', 'doctor').order_by('-created_at')[:10],
            'recent_prescriptions': Prescription.objects.select_related('patient', 'doctor').order_by('-created_at')[:8],
        })

    elif user.role == 'PATIENT':
        patient_profile = Patient.objects.filter(
            Q(email=user.email) | Q(contact_number=user.phone_number) | Q(contact_number=user.username)
        ).first()

        my_history = Appointment.objects.none()
        my_past_history = Appointment.objects.none()
        my_upcoming_appointments = Appointment.objects.none()
        my_prescriptions = Prescription.objects.none()
        my_invoices = Invoice.objects.none()
        if patient_profile:
            my_history = Appointment.objects.filter(patient=patient_profile).select_related('doctor').order_by('-scheduled_time')
            my_past_history = my_history.filter(scheduled_time__lt=now).order_by('-scheduled_time')
            my_upcoming_appointments = my_history.filter(
                scheduled_time__gte=now,
                status='SCHEDULED',
            ).order_by('scheduled_time')
            my_prescriptions = Prescription.objects.filter(patient=patient_profile).select_related('doctor').order_by('-created_at')
            my_invoices = Invoice.objects.filter(patient=patient_profile).order_by('-updated_at')

        context.update({
            'patient_profile': patient_profile,
            'my_past_history': my_past_history[:10],
            'my_upcoming_appointments': my_upcoming_appointments[:10],
            'my_prescriptions': my_prescriptions[:10],
            'my_total_visits': my_history.count(),
            'my_invoice_due': my_invoices.filter(status__in=['UNPAID', 'PARTIAL']).aggregate(total=Sum('total_amount'))['total'] or 0,
            'helpdesk_message': "Ask anything about appointment booking, prescriptions, and billing in the AI Help Desk.",
        })

    return render(request, 'dashboard.html', context)
