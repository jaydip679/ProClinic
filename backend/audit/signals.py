"""
audit/signals.py
────────────────
Automatic AuditLog entries via Django signals for all key models.

Tracked models
--------------
  Patient        — patients.models
  Appointment    — appointments.models
  Prescription   — prescriptions.models
  Invoice        — billing.models
  Publication    — publications.models
  LabReport      — patients.models

Signal hooks
------------
  pre_save   → snapshot old field values for UPDATE diff
  post_save  → write CREATE or UPDATE log
  post_delete → write DELETE log

Notes
-----
* Actor is pulled from thread-local storage (populated by AuditUserMiddleware).
* Logging failures are swallowed so they never break the main transaction.
* Sensitive field values (passwords, tokens) are never logged.
* When update_fields is supplied, only those fields appear in the diff.
"""

import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .middleware import get_current_user
from .models import AuditLog

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Field exclusion — never log values for these field names
# ──────────────────────────────────────────────────────────────────────────────

_SENSITIVE_FIELDS = frozenset({
    'password', 'token', 'secret', 'api_key', 'access_token',
    'refresh_token', 'otp', 'pin',
})

# Fields whose values we snapshot but are too large/unreadable to store in JSON
_SKIP_VALUE_FIELDS = frozenset({
    'pdf_file', 'profile_picture', 'photo', 'image', 'file',
})


def _safe_value(field_name, value):
    """Return a JSON-serialisable form of a field value, or a placeholder."""
    if field_name in _SENSITIVE_FIELDS:
        return '***'
    if field_name in _SKIP_VALUE_FIELDS:
        return '<file>'
    if hasattr(value, 'pk'):          # related object → store pk
        return value.pk
    if hasattr(value, 'isoformat'):   # datetime/date
        return value.isoformat()
    try:
        # Basic JSON-serialisable types
        import json
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _snapshot(instance, fields=None):
    """
    Return a dict of {field_name: current_value} for the instance.
    If `fields` is given, only snapshot those field names.
    """
    snap = {}
    for field in instance._meta.concrete_fields:
        name = field.name
        if fields is not None and name not in fields:
            continue
        if name in _SENSITIVE_FIELDS:
            continue
        try:
            snap[name] = _safe_value(name, field.value_from_object(instance))
        except Exception:
            pass
    return snap


# ──────────────────────────────────────────────────────────────────────────────
# Registry — models to track (import-safe lazy references)
# ──────────────────────────────────────────────────────────────────────────────

_TRACKED_MODELS = {}   # populated in _get_tracked() after apps are ready


def _get_tracked():
    """Lazy-load model classes to avoid AppRegistryNotReady errors."""
    if not _TRACKED_MODELS:
        from appointments.models import Appointment
        from billing.models import Invoice
        from patients.models import LabReport, Patient
        from prescriptions.models import Prescription
        from publications.models import Publication

        _TRACKED_MODELS.update({
            'Patient':      Patient,
            'Appointment':  Appointment,
            'Prescription': Prescription,
            'Invoice':      Invoice,
            'Publication':  Publication,
            'LabReport':    LabReport,
        })
    return _TRACKED_MODELS


def _entity_name(instance):
    """Return the display name for this model instance."""
    tracked = _get_tracked()
    for name, cls in tracked.items():
        if type(instance) is cls:
            return name
    return type(instance).__name__


def _is_tracked(instance):
    """Return True if this model instance should be audited."""
    tracked = _get_tracked()
    return isinstance(instance, tuple(tracked.values()))


def _write_log(*, actor, action_type, entity_type, entity_id, changes=None):
    """Write one AuditLog row, swallowing errors so the main tx is safe."""
    try:
        AuditLog.objects.create(
            actor=actor,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes or {},
        )
    except Exception:
        logger.exception(
            'AuditLog write failed: action=%s entity=%s id=%s',
            action_type, entity_type, entity_id,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Signal: pre_save — capture old values before write
# ──────────────────────────────────────────────────────────────────────────────

@receiver(pre_save)
def _capture_old_state(sender, instance, **kwargs):
    """Store a snapshot of the current DB state on the instance before save."""
    if not _is_tracked(instance):
        return
    if instance.pk is None:
        # New record — nothing to capture
        instance._audit_old_state = {}
        return

    try:
        fields = kwargs.get('update_fields')
        db_instance = sender.objects.only(
            *(fields if fields else [f.name for f in sender._meta.concrete_fields])
        ).get(pk=instance.pk)
        instance._audit_old_state = _snapshot(db_instance, fields)
    except sender.DoesNotExist:
        instance._audit_old_state = {}
    except Exception:
        instance._audit_old_state = {}


# ──────────────────────────────────────────────────────────────────────────────
# Signal: post_save — log CREATE or UPDATE
# ──────────────────────────────────────────────────────────────────────────────

@receiver(post_save)
def _log_save(sender, instance, created, **kwargs):
    """Write CREATE or UPDATE log after a successful save."""
    if not _is_tracked(instance):
        return

    actor       = get_current_user()
    entity_type = _entity_name(instance)
    action      = 'CREATE' if created else 'UPDATE'

    if created:
        changes = _snapshot(instance)
    else:
        # Build diff: only fields that actually changed
        old = getattr(instance, '_audit_old_state', {})
        new = _snapshot(instance, fields=kwargs.get('update_fields'))
        changes = {
            field: {'before': old.get(field), 'after': new_val}
            for field, new_val in new.items()
            if new_val != old.get(field)
        }
        if not changes:
            return   # nothing actually changed — skip the log

    _write_log(
        actor=actor,
        action_type=action,
        entity_type=entity_type,
        entity_id=instance.pk,
        changes=changes,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Signal: post_delete — log DELETE
# ──────────────────────────────────────────────────────────────────────────────

@receiver(post_delete)
def _log_delete(sender, instance, **kwargs):
    """Write a DELETE log after a record is removed from the database."""
    if not _is_tracked(instance):
        return

    actor       = get_current_user()
    entity_type = _entity_name(instance)

    # Capture a brief summary of what was deleted (no sensitive fields)
    summary = {}
    for field in ('title', 'name', 'first_name', 'last_name', 'status', 'created_at'):
        val = getattr(instance, field, None)
        if val is not None:
            summary[field] = _safe_value(field, val)

    _write_log(
        actor=actor,
        action_type='DELETE',
        entity_type=entity_type,
        entity_id=instance.pk,
        changes={'deleted_summary': summary},
    )
