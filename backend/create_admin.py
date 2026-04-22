"""
create_admin.py — Run by Render startCommand after migrate.
Upserts the admin superuser so credentials are always correct on every deploy.
Safe on re-deploy: get_or_create means an existing user is updated, not duplicated.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402 (must be after setup)

User = get_user_model()

u, created = User.objects.get_or_create(
    username="admin",
    defaults={"email": "admin@proclinic.com"},
)

u.email = "admin@proclinic.com"
u.role = "ADMIN"
u.is_staff = True
u.is_superuser = True
u.set_password("Admin@12345")
u.save()

print(f"Admin {'created' if created else 'updated'} OK — username=admin")
