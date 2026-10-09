from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
from datetime import datetime
from django.utils import timezone

from .models import Exam, Invoice, Payment, ResourceMaterial, SchoolClass, SupportTicket, User


class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            email="student@example.com",
            first_name="Aisha",
            last_name="Njeri",
            role="student",
        )
        cls.user.set_password("student-pass")
        cls.user.save()

    def test_public_pages_render(self):
        for page in ("index", "library", "classes", "exams", "support", "contact"):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(reverse(page)).status_code, 200)

    def test_health_check_verifies_database_connectivity(self):
        response = self.client.get(reverse("health_check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(response["Content-Type"], "text/plain")

    def test_protected_pages_redirect_to_login(self):
        for page in ("dashboard", "billing"):
            with self.subTest(page=page):
                response = self.client.get(reverse(page))
                self.assertRedirects(response, reverse("login"))

    def test_login_and_logout(self):
        response = self.client.post(
            reverse("login"),
            {"email": "student@example.com", "password": "student-pass"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.client.get(reverse("logout"))
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("login"))

    def test_support_ticket_submission(self):
        response = self.client.post(
            reverse("support"),
            {
                "user_name": "Parent Example",
                "user_email": "parent@example.com",
                "subject": "School fees",
                "message": "Please help with my invoice.",
            },
        )
        self.assertRedirects(response, reverse("support"))
        self.assertEqual(SupportTicket.objects.count(), 1)

    def test_video_resources_render_zoom_controls(self):
        ResourceMaterial.objects.create(
            title="Fractions lesson",
            subject="Mathematics",
            grade_level="Grade 5",
            resource_type="Video",
            term="Term 1",
            academic_year="2026",
            file_url="https://media.example.org/fractions.mp4",
            uploaded_by="Teacher",
        )

        response = self.client.get(reverse("library"))

        self.assertContains(response, "Fractions lesson")
        self.assertContains(response, "data-video-player")
        self.assertContains(response, "data-zoom-in")
        self.assertContains(response, "data-zoom-out")
        self.assertContains(response, "data-zoom-reset")

    def test_uploaded_media_is_served_from_storage(self):
        with patch("school.views.default_storage.open", return_value=BytesIO(b"sample material")):
            response = self.client.get("/media/library/sample.pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"sample material")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_staff_room_restricts_access_and_uploads_library_material(self):
        response = self.client.get(reverse("staff_room"))
        self.assertRedirects(response, reverse("login"))

        self.client.post(
            reverse("login"),
            {"email": "student@example.com", "password": "student-pass"},
        )
        response = self.client.get(reverse("staff_room"))
        self.assertRedirects(response, reverse("login"))
        self.client.get(reverse("logout"))

        teacher = User(
            email="teacher@example.com",
            first_name="John",
            last_name="Mwangi",
            role="teacher",
        )
        teacher.set_password("teacher-pass")
        teacher.save()
        self.client.post(
            reverse("login"),
            {"email": "teacher@example.com", "password": "teacher-pass"},
        )
        self.assertEqual(self.client.get(reverse("staff_room")).status_code, 200)

        with patch("school.views.default_storage.save", return_value="library/lesson.pdf"):
            response = self.client.post(
                reverse("staff_room"),
                {
                    "title": "Fractions lesson",
                    "subject": "Mathematics",
                    "grade_level": "Grade 5",
                    "resource_type": "PDF",
                    "term": "Term 1",
                    "academic_year": "2026",
                    "material_file": SimpleUploadedFile("lesson.pdf", b"%PDF demo", content_type="application/pdf"),
                },
            )

        self.assertRedirects(response, reverse("staff_room"))
        material = ResourceMaterial.objects.get(title="Fractions lesson")
        self.assertEqual(material.file_url, "/media/library/lesson.pdf")
        self.assertEqual(material.uploaded_by, "John Mwangi")
        self.assertContains(self.client.get(reverse("library")), "Fractions lesson")

    def test_teacher_can_schedule_one_hour_zoom_lesson(self):
        response = self.client.post(
            reverse("classes"),
            {"title": "Science", "subject": "Biology", "start_at": "2030-05-10T09:00"},
        )
        self.assertRedirects(response, reverse("login"))
        self.assertEqual(SchoolClass.objects.count(), 0)

        teacher = User(
            email="teacher@example.com",
            first_name="John",
            last_name="Mwangi",
            role="teacher",
        )
        teacher.set_password("teacher-pass")
        teacher.save()
        self.client.post(
            reverse("login"),
            {"email": "teacher@example.com", "password": "teacher-pass"},
        )
        start_at = timezone.make_aware(datetime(2030, 5, 10, 9, 0), timezone.get_current_timezone())
        fake_meeting = {
            "join_url": "https://zoom.us/j/123",
            "start_url": "https://zoom.us/s/123",
            "meeting_id": "123",
            "passcode": "456",
        }
        with patch("school.views.zoom.create_meeting", return_value=fake_meeting) as create_meeting:
            response = self.client.post(
                reverse("classes"),
                {"title": "Science", "subject": "Biology", "start_at": "2030-05-10T09:00"},
            )

        self.assertRedirects(response, reverse("classes"))
        self.assertEqual(create_meeting.call_args.args[0], "Science")
        self.assertEqual(create_meeting.call_args.args[1][-1], "Z")
        self.assertEqual(create_meeting.call_args.kwargs["duration_minutes"], 60)
        lesson = SchoolClass.objects.get(title="Science")
        self.assertEqual(lesson.end_time, "10:00 AM")
        self.assertEqual(lesson.lesson_date.isoformat(), "2030-05-10")
        self.assertEqual(lesson.zoom_meeting_id, "123")

        with patch("school.views.zoom.create_meeting") as create_again:
            response = self.client.post(reverse("class_go_live", args=[lesson.pk]))
        self.assertRedirects(response, reverse("classes"))
        create_again.assert_not_called()
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, "Live")

    def test_invoice_payment_updates_status(self):
        invoice = Invoice.objects.create(
            student_name="Aisha Njeri",
            invoice_number="INV-TEST-1",
            term="Term 1",
            due_date="2026-10-15",
            total_amount=1000,
            amount_paid=0,
            status="Pending",
        )
        self.client.post(
            reverse("login"),
            {"email": "student@example.com", "password": "student-pass"},
        )
        response = self.client.post(
            reverse("pay_invoice", args=[invoice.pk]),
            {"amount": "1000", "method": "mpesa", "phone": "0712345678"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("mpesa_start"))
        # Daraja is not configured in tests, so a demo payment is recorded.
        response = self.client.get(reverse("mpesa_start"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("billing"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, 1000)
        self.assertEqual(invoice.status, "Paid")
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)

    def test_exam_pdf_upload_requires_staff(self):
        pdf = SimpleUploadedFile("exam.pdf", b"%PDF-1.4 demo", content_type="application/pdf")
        response = self.client.post(reverse("exams"), {"title": "Midterm", "pdf_file": pdf})
        self.assertRedirects(response, reverse("login"))
        self.assertEqual(Exam.objects.count(), 0)

        teacher = User(
            email="teacher@example.com",
            first_name="John",
            last_name="Mwangi",
            role="teacher",
        )
        teacher.set_password("teacher-pass")
        teacher.save()
        self.client.post(
            reverse("login"),
            {"email": "teacher@example.com", "password": "teacher-pass"},
        )
        pdf = SimpleUploadedFile("exam.pdf", b"%PDF-1.4 demo", content_type="application/pdf")
        response = self.client.post(
            reverse("exams"),
            {
                "title": "Midterm",
                "subject": "Mathematics",
                "grade_level": "Grade 7",
                "term": "Term 2",
                "academic_year": "2026",
                "pdf_file": pdf,
            },
        )
        self.assertRedirects(response, reverse("exams"))
        self.assertEqual(Exam.objects.count(), 1)