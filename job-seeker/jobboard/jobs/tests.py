from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail

from accounts.models import User, EmployerProfile, JobSeekerProfile
from .models import Job, JobApplication


class JobSearchTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username="emp", password="pass", role="employer", email="emp@example.com", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(user=self.employer_user, company_name="ACME", phone="000", address="addr")

        Job.objects.create(
            employer=self.employer_profile,
            title="Backend Developer",
            description="Work with Django and PostgreSQL",
            location="Remote",
            min_salary=50000,
            max_salary=90000,
            required_skills="python, django, sql",
            benefits="remote, insurance",
        )
        Job.objects.create(
            employer=self.employer_profile,
            title="UI Designer",
            description="Figma and design systems",
            location="London",
            min_salary=30000,
            max_salary=50000,
            required_skills="figma, ui, ux",
        )

    def test_search_by_title(self):
        resp = self.client.get(reverse("job_list"), {"q": "backend"})
        self.assertContains(resp, "Backend Developer")
        self.assertNotContains(resp, "UI Designer")

    def test_filter_by_salary_overlap(self):
        resp = self.client.get(reverse("job_list"), {"min_salary": "80000"})
        self.assertContains(resp, "Backend Developer")
        self.assertNotContains(resp, "UI Designer")

    def test_filter_by_skills(self):
        resp = self.client.get(reverse("job_list"), {"skills": "django"})
        self.assertContains(resp, "Backend Developer")
        self.assertNotContains(resp, "UI Designer")


class RecommendationTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username="emp", password="pass", role="employer", email="emp@example.com", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(user=self.employer_user, company_name="ACME", phone="000", address="addr")

        self.job1 = Job.objects.create(
            employer=self.employer_profile,
            title="Django Developer",
            description="Python Django REST",
            location="Remote",
            required_skills="python, django, rest",
        )
        self.job2 = Job.objects.create(
            employer=self.employer_profile,
            title="C++ Engineer",
            description="Low level systems",
            location="Berlin",
            required_skills="c++, linux",
        )

        self.seeker_user = User.objects.create_user(username="js", password="pass", role="jobseeker", email="js@example.com", is_active=True)
        self.seeker_profile = JobSeekerProfile.objects.create(user=self.seeker_user, full_name="Job Seeker", education="Computer Science", skills="python, django")

    def test_recommended_jobs(self):
        self.client.login(username="js", password="pass")
        resp = self.client.get(reverse("recommended_jobs"))
        self.assertContains(resp, "Django Developer")
        self.assertNotContains(resp, "C++ Engineer")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="no-reply@test.local")
class NotificationTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username="emp", password="pass", role="employer", email="emp@example.com", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(user=self.employer_user, company_name="ACME", phone="000", address="addr")

        self.seeker_user = User.objects.create_user(username="js", password="pass", role="jobseeker", email="js@example.com", is_active=True)
        self.seeker_profile = JobSeekerProfile.objects.create(user=self.seeker_user, full_name="Job Seeker", education="CS", skills="python")

        self.job = Job.objects.create(employer=self.employer_profile, title="Backend", description="Django", location="Remote")
        self.app = JobApplication.objects.create(job=self.job, jobseeker=self.seeker_profile, resume="resumes/test.pdf")

    def test_schedule_interview_sends_email(self):
        self.client.login(username="emp", password="pass")
        resp = self.client.post(reverse("schedule_interview", args=[self.app.id]), {"interview_date": "2026-02-01"})
        self.assertEqual(resp.status_code, 302)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "interview")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Interview scheduled", mail.outbox[0].subject)

    def test_reject_sends_email(self):
        self.client.login(username="emp", password="pass")
        resp = self.client.get(reverse("reject_application", args=[self.app.id]))
        self.assertEqual(resp.status_code, 302)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "rejected")
        self.assertEqual(len(mail.outbox), 1)
