"""
api/pagination.py
─────────────────
Shared pagination classes for all ProClinic API viewsets.
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Default pagination for all staff-facing API viewsets.

    Query params:
      ?page=<n>             — page number (1-indexed)
      ?page_size=<n>        — override default page size (max 100)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'


class LargeResultsSetPagination(PageNumberPagination):
    """Used for endpoints where a larger default makes sense (e.g. publications)."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    page_query_param = 'page'
