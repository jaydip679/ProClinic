from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from .models import AuditLog

@user_passes_test(lambda u: u.is_staff)
def audit_log_list(request):
    # Fetch the 50 most recent actions
    logs = AuditLog.objects.select_related('actor').order_by('-timestamp')[:50]
    return render(request, 'audit/log_list.html', {'logs': logs})