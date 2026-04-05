from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .forms import InvoiceForm, InvoiceItemFormSet
from .models import Invoice
from patients.models import Patient

@login_required
def generate_invoice(request):
    if request.user.role not in {'ACCOUNTANT', 'ADMIN', 'RECEPTIONIST'}:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            invoice = form.save()
            formset.instance = invoice
            formset.save()
            
            # Logic Tier: Calculate total after items are saved
            total = sum(item.line_total for item in invoice.items.all())
            invoice.total_amount = total
            invoice.save()
            
            return redirect('patient_list')
    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet()
        
    return render(request, 'billing/generate_invoice.html', {
        'form': form,
        'formset': formset
    })

@login_required
def patient_invoices(request):
    if request.user.role != 'PATIENT':
        return redirect('dashboard')
        
    # Get the patient profile securely
    patient_profile = getattr(request.user, 'patient_profile', None)
    if patient_profile is None:
        patient_profile = Patient.objects.filter(
            Q(email=request.user.email) | 
            Q(contact_number=request.user.phone_number) | 
            Q(contact_number=request.user.username)
        ).first()
        
    if not patient_profile:
        return redirect('dashboard')
        
    invoices = Invoice.objects.filter(patient=patient_profile).prefetch_related('items', 'appointment__doctor').order_by('-created_at')
    
    return render(request, 'billing/patient_invoices.html', {
        'invoices': invoices
    })