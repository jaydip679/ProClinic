"""
management/commands/mark_noshow.py
───────────────────────────────────
Management command that marks overdue appointments as NOSHOW.

Usage:
    python manage.py mark_noshow
    python manage.py mark_noshow --grace 15   # 15-minute grace period

Schedule with cron (example — runs every 5 minutes):
    */5 * * * * /path/to/venv/bin/python /path/to/manage.py mark_noshow >> /var/log/proclinic/noshow.log 2>&1
"""
from django.core.management.base import BaseCommand

from appointments.services import auto_mark_noshow


class Command(BaseCommand):
    help = (
        "Mark appointments as NOSHOW when the patient has not checked in "
        "within the configured grace period after the scheduled start time."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--grace',
            type=int,
            default=30,
            metavar='MINUTES',
            help=(
                "Number of minutes after the scheduled start time before an "
                "appointment is automatically marked NOSHOW (default: 30)."
            ),
        )

    def handle(self, *args, **options):
        grace = options['grace']
        self.stdout.write(
            f"Checking for appointments overdue by {grace} minute(s)…"
        )
        count = auto_mark_noshow(grace_minutes=grace)
        if count:
            self.stdout.write(
                self.style.SUCCESS(f"Marked {count} appointment(s) as NOSHOW.")
            )
        else:
            self.stdout.write("No appointments needed to be marked as NOSHOW.")
