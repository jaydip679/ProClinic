"""Lightweight helper to create AuditLog entries from anywhere in the app."""

from .models import AuditLog


def log_action(*, actor, action_type, entity_type, entity_id=None, changes=None):
    """
    Create an AuditLog entry.

    Parameters
    ----------
    actor : CustomUser or None
        The user performing the action.
    action_type : str
        One of 'CREATE', 'UPDATE', 'DELETE', 'LOGIN'.
    entity_type : str
        Human-readable label, e.g. 'Appointment', 'Patient'.
    entity_id : int or None
        PK of the affected record.
    changes : dict or None
        Optional JSON-serialisable before/after diff.
    """
    AuditLog.objects.create(
        actor=actor,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
    )
