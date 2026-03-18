from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import InvoiceForm, InvoiceItemFormSet

@login_required
def generate_invoice(request):
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