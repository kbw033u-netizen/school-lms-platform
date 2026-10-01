from django.test import TestCase
from django.urls import reverse

from .models import ResourceMaterial, SupportTicket, User


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
        for page in ("index", "library", "classes", "support", "contact"):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(reverse(page)).status_code, 200)

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