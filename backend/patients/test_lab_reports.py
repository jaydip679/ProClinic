from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import CustomUser
from .models import Patient, LabReport

class LabReportValidationTests(TestCase):
    def setUp(self):
        user = CustomUser.objects.create_user(
            username='patient1',
            role='PATIENT'
        )
        self.patient = Patient.objects.create(
            user=user,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='Male'
        )

    def test_upload_invalid_mime_type(self):
        from django.core.exceptions import ValidationError
        bad_file = SimpleUploadedFile(
            "report.jpg", 
            b"file_content", 
            content_type="image/jpeg"
        )
        report = LabReport(
            patient=self.patient,
            test_name="Blood Test",
            pdf_file=bad_file
        )
        with self.assertRaises(ValidationError) as context:
            report.clean_fields()
        self.assertIn('Only PDF files are accepted', str(context.exception))

    def test_upload_oversized_file(self):
        from django.core.exceptions import ValidationError
        large_file = SimpleUploadedFile(
            "large_report.pdf",
            b"0" * (6 * 1024 * 1024), # 6 MB
            content_type="application/pdf"
        )
        report = LabReport(
            patient=self.patient,
            test_name="MRI Scan",
            pdf_file=large_file
        )
        with self.assertRaises(ValidationError) as context:
            report.clean_fields()
        self.assertIn('File size must not exceed', str(context.exception))
