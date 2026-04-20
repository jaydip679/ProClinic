from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_appointment_notification(appointment, action='created'):
    """
    Send an email notification for appointment events (created, rescheduled, cancelled).
    Since email backend might not be configured in development, we catch exceptions.
    """
    if not appointment.patient.email:
        logger.warning(f"No email for patient {appointment.patient.first_name}, skipping notification.")
        return False
        
    subject = f"Appointment {action.capitalize()} - ProClinic"
    
    date_str = appointment.scheduled_time.strftime('%Y-%m-%d %H:%M')
    message = (
        f"Dear {appointment.patient.first_name},\n\n"
        f"Your appointment has been {action}.\n"
        f"Doctor: Dr. {appointment.doctor.get_full_name()}\n"
        f"Time: {date_str}\n\n"
        "Thank you,\nProClinic Team"
    )
    
    try:
        sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@proclinic.local')
        send_mail(
            subject=subject,
            message=message,
            from_email=sender_email,
            recipient_list=[appointment.patient.email],
            fail_silently=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
