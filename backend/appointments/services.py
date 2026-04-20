"""
appointments/services.py
────────────────────────
Reusable service functions for appointment business logic.
Import these from management commands, views, or scheduled tasks.
"""
from __future__ import annotations

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# Statuses that represent an "active" (not yet finalised) slot that the
# no-show rule should inspect.
_NOSHOW_ELIGIBLE_STATUSES = {'SCHEDULED', 'RESCHEDULED'}

# Statuses that must NEVER be touched by the auto-no-show rule.
_NOSHOW_IMMUNE_STATUSES = {'CHECKED_IN', 'COMPLETED', 'CANCELLED', 'NOSHOW'}


def auto_mark_noshow(grace_minutes: int = 30) -> int:
    """Mark appointments as NOSHOW when the patient has not checked in
    within *grace_minutes* after the scheduled start time.

    Only appointments whose status is SCHEDULED or RESCHEDULED are
    considered.  CHECKED_IN, COMPLETED, CANCELLED, and NOSHOW appointments
    are never touched.

    Returns:
        int: Number of appointments that were updated to NOSHOW.
    """
    from appointments.models import Appointment

    cutoff = timezone.now() - timezone.timedelta(minutes=grace_minutes)

    eligible_qs = Appointment.objects.filter(
        status__in=_NOSHOW_ELIGIBLE_STATUSES,
        scheduled_time__lte=cutoff,
    )

    count = 0
    for appt in eligible_qs.select_related('patient', 'doctor'):
        appt.status = 'NOSHOW'
        # Use update_fields to bypass full_clean (which would reject a past
        # scheduled_time as invalid for a new booking).
        appt.save(update_fields=['status'])
        logger.info(
            "Auto-NOSHOW: appointment #%s (%s with Dr. %s at %s)",
            appt.pk,
            appt.patient,
            appt.doctor.get_full_name() or appt.doctor.username,
            timezone.localtime(appt.scheduled_time).strftime("%Y-%m-%d %H:%M"),
        )
        count += 1

    if count:
        logger.info("auto_mark_noshow: marked %d appointment(s) as NOSHOW.", count)
    return count
