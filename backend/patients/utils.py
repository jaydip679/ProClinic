from django.db.models import Q
from patients.models import Patient

def get_patient_profile(user):
    """Return the Patient linked to a user, or None."""
    if not user.is_authenticated:
        return None
    profile = getattr(user, 'patient_profile', None)
    if profile is not None:
        return profile
    profile = Patient.objects.filter(
        Q(email=user.email)
        | Q(contact_number=user.phone_number)
        | Q(contact_number=user.username)
    ).first()

    # Repair: attach FK for future lookups
    if profile and profile.user_id is None:
        profile.user = user
        profile.save(update_fields=['user'])

    return profile
