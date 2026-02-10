from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone

from .models import User


class SmsActivationTests(TestCase):
    def test_sms_activate_success(self):
        u = User.objects.create_user(username="u1", password="pass", role="jobseeker", email="u1@example.com", is_active=False, is_email_verified=False)
        cache.set(f"sms_activation:{u.pk}", "123456", timeout=600)

        resp = self.client.post(reverse("sms_activate"), {"username": "u1", "code": "123456"})
        self.assertEqual(resp.status_code, 302)

        u.refresh_from_db()
        self.assertTrue(u.is_active)
        self.assertTrue(u.is_email_verified)

    def test_jobseeker_signup_does_not_auto_create_sms_code(self):
        resp = self.client.post(
            reverse("register_jobseeker"),
            {
                "username": "u2",
                "email": "u2@example.com",
                "password": "pass12345",
                "full_name": "User Two",
                "education": "CS",
                "skills": "python, django",
                "phone": "",
            },
        )
        self.assertEqual(resp.status_code, 302)

        user = User.objects.get(username="u2")
        self.assertFalse(user.is_active)
        self.assertIsNone(cache.get(f"sms_activation:{user.pk}"))
        self.assertFalse(user.sms_activation_code)

    def test_sms_send_code_generates_unique_codes(self):
        user = User.objects.create_user(
            username="u_send",
            password="pass",
            role="jobseeker",
            email="u_send@example.com",
            is_active=False,
            is_email_verified=False,
        )

        first = self.client.post(reverse("sms_send_code"), {"username": "u_send"})
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["ok"])
        user.refresh_from_db()
        first_code = user.sms_activation_code
        self.assertTrue(first_code)
        self.assertEqual(first_code, cache.get(f"sms_activation:{user.pk}"))

        second = self.client.post(reverse("sms_send_code"), {"username": "u_send"})
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["ok"])
        user.refresh_from_db()
        second_code = user.sms_activation_code
        self.assertTrue(second_code)
        self.assertNotEqual(first_code, second_code)

    def test_sms_activate_logs_user_in_and_uses_persisted_code(self):
        u = User.objects.create_user(
            username="u3",
            password="pass",
            role="jobseeker",
            email="u3@example.com",
            is_active=False,
            is_email_verified=False,
            sms_activation_code="654321",
            sms_activation_sent_at=timezone.now(),
        )
        # Simulate cache miss
        cache.delete(f"sms_activation:{u.pk}")

        resp = self.client.post(reverse("sms_activate"), {"username": "u3", "code": "654321"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("home"))

        u.refresh_from_db()
        self.assertTrue(u.is_active)
        self.assertTrue(u.is_email_verified)
        self.assertIsNone(u.sms_activation_code)
        self.assertIn("_auth_user_id", self.client.session)
