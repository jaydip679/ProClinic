"""
prescriptions/utils.py
──────────────────────
WeasyPrint-based PDF generation utilities for prescriptions.
"""
from __future__ import annotations

import io
import logging
from datetime import date

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

_TEMPLATE = "prescriptions/pdf_template.html"


def _build_context(prescription) -> dict:
    """Return the template context dict for a Prescription instance."""
    visit = prescription.visit
    items = list(prescription.items.all().order_by("id"))

    return {
        "prescription": prescription,
        "visit": visit,
        "items": items,
        "issued_date": prescription.created_at.strftime("%d %B %Y"),
    }


def render_prescription_html(prescription) -> str:
    """Render the PDF template to an HTML string."""
    return render_to_string(_TEMPLATE, _build_context(prescription))


def generate_prescription_pdf(prescription) -> bytes:
    """
    Render the prescription template and convert it to PDF bytes using WeasyPrint.

    Raises RuntimeError if WeasyPrint is not installed or PDF generation fails.
    """
    try:
        from weasyprint import HTML as WeasyHTML  # lazy import — avoids startup cost
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is not installed. Add 'weasyprint' to requirements.txt "
            "and install system dependencies (libpango, libcairo2, etc.)."
        ) from exc

    html_string = render_prescription_html(prescription)

    try:
        pdf_bytes = WeasyHTML(string=html_string).write_pdf()
    except Exception as exc:
        logger.exception("WeasyPrint PDF generation failed for prescription %s", prescription.pk)
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    return pdf_bytes


def prescription_pdf_response(prescription) -> HttpResponse:
    """
    Generate a prescription PDF and return it as an inline HTTP response.

    The PDF is also saved to prescription.pdf_file so subsequent requests
    can serve the cached file directly without re-rendering.
    """
    # Return cached file if it already exists
    if prescription.pdf_file:
        try:
            with prescription.pdf_file.open("rb") as fh:
                return _make_response(fh.read(), prescription)
        except Exception:
            # Cached file is missing on disk — re-generate
            pass

    pdf_bytes = generate_prescription_pdf(prescription)

    # Persist the generated PDF to storage
    filename = f"prescription_{prescription.pk}_{date.today().isoformat()}.pdf"
    prescription.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    logger.info("Saved PDF for prescription %s → %s", prescription.pk, prescription.pdf_file.name)

    return _make_response(pdf_bytes, prescription)


def _make_response(pdf_bytes: bytes, prescription) -> HttpResponse:
    """Wrap raw PDF bytes in an HttpResponse with correct headers."""
    filename = f"prescription_{prescription.pk}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response["Content-Length"] = len(pdf_bytes)
    return response
