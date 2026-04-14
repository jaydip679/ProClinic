from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from .models import AuditLog


@login_required
def audit_log_list(request):
    """Audit log viewer — ADMIN role only. Supports filtering and pagination."""
    if request.user.role != 'ADMIN':
        return redirect('dashboard')

    logs = AuditLog.objects.select_related('actor').order_by('-timestamp')

    # ── Filters ───────────────────────────────────────────────────────────────
    action_type = request.GET.get('action_type', '').strip()
    if action_type:
        logs = logs.filter(action_type=action_type)

    entity_type = request.GET.get('entity_type', '').strip()
    if entity_type:
        logs = logs.filter(entity_type=entity_type)

    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)

    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    # ── Pagination ────────────────────────────────────────────────────────────
    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Distinct choices for filter dropdowns
    action_choices  = AuditLog.objects.values_list('action_type', flat=True).distinct().order_by('action_type')
    entity_choices  = AuditLog.objects.values_list('entity_type', flat=True).distinct().order_by('entity_type')

    return render(request, 'audit/log_list.html', {
        'page_obj': page_obj,
        'action_choices': action_choices,
        'entity_choices': entity_choices,
        'current_action_type': action_type,
        'current_entity_type': entity_type,
        'current_date_from': date_from,
        'current_date_to': date_to,
    })