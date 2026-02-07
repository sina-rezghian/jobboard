from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

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
