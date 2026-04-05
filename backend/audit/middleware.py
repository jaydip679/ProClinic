"""
audit/middleware.py
───────────────────
Thread-local middleware that stores the current authenticated user so that
signal handlers (which have no access to `request`) can attach an actor to
automatically-generated AuditLog entries.

Usage
-----
Add to MIDDLEWARE in settings.py (after AuthenticationMiddleware):

    'audit.middleware.AuditUserMiddleware',
"""

import threading

_local = threading.local()


def get_current_user():
    """Return the authenticated user stored for this thread, or None."""
    return getattr(_local, 'user', None)


def set_current_user(user):
    """Store user for the current thread."""
    _local.user = user


class AuditUserMiddleware:
    """
    Captures request.user at the start of each request and makes it
    available to signal handlers via `get_current_user()`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        # Only store authenticated, non-anonymous users
        if user and getattr(user, 'is_authenticated', False):
            set_current_user(user)
        else:
            set_current_user(None)

        response = self.get_response(request)

        # Clear after request to prevent leaking across threads in pooled servers
        set_current_user(None)
        return response
