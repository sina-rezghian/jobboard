from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User, EmployerProfile, JobSeekerProfile
from resumes.models import Resume
from .models import Job, JobApplication, JobAlertMatch


class JobBoardFlowTests(TestCase):
    def setUp(self):
        self.emp_user = User.objects.create_user(username="emp", password="pass", role="employer", email="emp@example.com", is_active=True)
        self.emp = EmployerProfile.objects.create(user=self.emp_user, company_name="ACME", phone="+440001")

        self.js_user = User.objects.create_user(username="js", password="pass", role="jobseeker", email="js@example.com", is_active=True)
        self.js = JobSeekerProfile.objects.create(user=self.js_user, full_name="Ali", education="Computer Science", skills="python,django")

        self.job1 = Job.objects.create(employer=self.emp, title="Backend Developer", description="Django", location="London", min_salary=50000, max_salary=90000, required_skills="python,django")
        self.job2 = Job.objects.create(employer=self.emp, title="UI Designer", description="Figma", location="Manchester", min_salary=30000, max_salary=50000, required_skills="figma,ux")

    def test_search_filters(self):
        resp = self.client.get(reverse("job_list"), {"q": "Backend", "skills": "django", "city": "London"})
        self.assertContains(resp, "Backend Developer")
        self.assertNotContains(resp, "UI Designer")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_apply_and_reject_flow(self):
        Resume.objects.create(
            jobseeker=self.js,
            file=SimpleUploadedFile("cv.pdf", b"pdf-bytes", content_type="application/pdf"),
            title="CV",
        )
        self.client.login(username="js", password="pass")
        resp = self.client.post(reverse("apply_job", args=[self.job1.id]), {"cover_letter": "hello", "note": "note"})
        self.assertEqual(resp.status_code, 302)
        app = JobApplication.objects.get(job=self.job1, jobseeker=self.js)

        self.client.logout()
        self.client.login(username="emp", password="pass")
        resp = self.client.get(reverse("reject_application", args=[app.id]))
        self.assertEqual(resp.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, "rejected")

    def test_recommendations(self):
        self.client.login(username="js", password="pass")
        resp = self.client.get(reverse("recommended_jobs"))
        self.assertContains(resp, "Backend Developer")

    def test_alert_match_created(self):
        self.client.login(username="js", password="pass")
        self.client.post(reverse("job_alerts"), {"keywords": "backend", "skills": "django", "location": "London", "is_enabled": True})
        self.client.logout()

        self.client.login(username="emp", password="pass")
        self.client.post(reverse("create_job"), {
            "title": "Python Engineer",
            "description": "backend django",
            "location": "London",
            "job_type": "full_time",
            "experience_level": "entry",
            "cover_letter_required": False,
            "min_salary": 60000,
            "max_salary": 80000,
            "required_skills": "python,django",
            "benefits": "",
        })
        self.assertTrue(JobAlertMatch.objects.exists())
