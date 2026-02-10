from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail

from accounts.models import User, EmployerProfile, JobSeekerProfile, Notification
from resumes.models import Resume
from .models import Job, JobApplication, JobAlert, JobAlertMatch, SavedJob
from .utils import process_job_alerts_for_job


class JobSearchTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username="emp", password="pass", role="employer", email="emp@example.com", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user, company_name="ACME", phone="000", company_description="addr"
        )

        Job.objects.create(
            employer=self.employer_profile,
            title="Backend Developer",
            description="Work with Django and PostgreSQL",
            location="Remote",
            job_type="full_time",
            experience_level="mid",
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
            job_type="contract",
            experience_level="entry",
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

    def test_filter_by_job_type(self):
        resp = self.client.get(reverse("job_list"), {"job_type": "contract"})
        self.assertContains(resp, "UI Designer")
        self.assertNotContains(resp, "Backend Developer")

    def test_short_keyword_search_does_not_match_description_only(self):
        Job.objects.create(
            employer=self.employer_profile,
            title="Operations Analyst",
            description="Strong QA processes and documentation",
            location="Leeds",
            required_skills="excel, reporting",
        )
        Job.objects.create(
            employer=self.employer_profile,
            title="QA Engineer",
            description="Testing and automation",
            location="Manchester",
            required_skills="qa, automation",
        )
        resp = self.client.get(reverse("job_list"), {"q": "qa"})
        self.assertContains(resp, "QA Engineer")
        self.assertNotContains(resp, "Operations Analyst")

    def test_job_list_provides_skill_suggestions(self):
        resp = self.client.get(reverse("job_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("skill_suggestions", resp.context)
        self.assertTrue(resp.context["skill_suggestions"])

    def test_skill_suggestions_api_prefix(self):
        resp = self.client.get(reverse("skill_suggestions_api"), {"q": "dj"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertTrue(any(item.startswith("dj") for item in data["items"]))


class RecommendationTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username="emp", password="pass", role="employer", email="emp@example.com", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user, company_name="ACME", phone="000", company_description="addr"
        )

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

    def test_recommendations_use_latest_resume_when_profile_missing(self):
        self.seeker_profile.skills = ""
        self.seeker_profile.education = ""
        self.seeker_profile.save(update_fields=["skills", "education"])
        Resume.objects.create(
            jobseeker=self.seeker_profile,
            file="resumes/js_resume.txt",
            education="Computer Science",
            skills="python, django",
        )

        self.client.login(username="js", password="pass")
        resp = self.client.get(reverse("recommended_jobs"))
        self.assertContains(resp, "Django Developer")

    def test_recommendations_fallback_to_recent_jobs_when_no_match(self):
        self.seeker_profile.skills = "golang, rust"
        self.seeker_profile.education = "Mechanical Engineering"
        self.seeker_profile.save(update_fields=["skills", "education"])

        self.client.login(username="js", password="pass")
        resp = self.client.get(reverse("recommended_jobs"))
        self.assertContains(resp, "Django Developer")
        self.assertContains(resp, "C++ Engineer")
        self.assertContains(resp, "latest jobs for you to explore")

    def test_apply_page_contains_skill_suggestions(self):
        Resume.objects.create(
            jobseeker=self.seeker_profile,
            file="resumes/js_resume.txt",
            education="Computer Science",
            skills="python, django",
        )
        self.client.login(username="js", password="pass")
        resp = self.client.get(reverse("apply_job", args=[self.job1.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Recommended skills to mention")
        self.assertIn("python", resp.context["skill_suggestions"])


class SavedJobsTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username="emp_saved", password="pass", role="employer", email="emp_saved@example.com", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user, company_name="ACME Saved", phone="000", company_description="addr"
        )
        self.job = Job.objects.create(
            employer=self.employer_profile,
            title="Saved Job Target",
            description="Django role",
            location="London",
            required_skills="python, django",
        )
        self.seeker_user = User.objects.create_user(username="js_saved", password="pass", role="jobseeker", email="js_saved@example.com", is_active=True)
        self.seeker_profile = JobSeekerProfile.objects.create(user=self.seeker_user, full_name="Saved Seeker", education="CS", skills="python")

    def test_toggle_saved_job_updates_saved_state(self):
        self.client.login(username="js_saved", password="pass")

        resp = self.client.get(reverse("toggle_saved_job", args=[self.job.id]), {"next": reverse("job_list")})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SavedJob.objects.filter(job=self.job, jobseeker=self.seeker_profile).exists())

        list_resp = self.client.get(reverse("job_list"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertIn(self.job.id, list_resp.context["saved_job_ids"])

        resp = self.client.get(reverse("toggle_saved_job", args=[self.job.id]), {"next": reverse("job_list")})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SavedJob.objects.filter(job=self.job, jobseeker=self.seeker_profile).exists())


class AlertFlowTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(
            username="emp_alert", password="pass", role="employer", email="emp_alert@example.com", is_active=True
        )
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user, company_name="ACME Alerts", phone="000", company_description="addr"
        )
        self.seeker_user = User.objects.create_user(
            username="js_alert", password="pass", role="jobseeker", email="js_alert@example.com", is_active=True
        )
        self.seeker_profile = JobSeekerProfile.objects.create(
            user=self.seeker_user, full_name="Alert Seeker", education="CS", skills="python, django"
        )

    def test_job_alerts_page_renders(self):
        self.client.login(username="js_alert", password="pass")
        resp = self.client.get(reverse("job_alerts"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Create Alert")

    def test_alert_match_creates_in_app_notification(self):
        alert = JobAlert.objects.create(
            jobseeker=self.seeker_profile,
            keywords="backend, django",
            skills="python, django",
            location="Remote",
            is_enabled=True,
        )
        job = Job.objects.create(
            employer=self.employer_profile,
            title="Backend Django Engineer",
            description="Build APIs in Django and Python",
            location="Remote",
            required_skills="python, django, postgresql",
        )

        process_job_alerts_for_job(job)

        self.assertTrue(JobAlertMatch.objects.filter(alert=alert, job=job).exists())
        self.assertTrue(Notification.objects.filter(user=self.seeker_user, title__icontains="New job match").exists())

    def test_alert_create_backfills_existing_jobs_and_notification(self):
        Job.objects.create(
            employer=self.employer_profile,
            title="Backend Django Engineer",
            description="Build APIs in Django and Python",
            location="London",
            required_skills="python, django, postgresql",
        )
        self.client.login(username="js_alert", password="pass")
        resp = self.client.post(
            reverse("job_alerts"),
            {
                "keywords": "backend, engineer",
                "skills": "django, python",
                "location": "London",
                "min_salary": "",
                "max_salary": "",
                "is_enabled": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(JobAlertMatch.objects.filter(alert__jobseeker=self.seeker_profile).exists())
        self.assertTrue(
            Notification.objects.filter(
                user=self.seeker_user,
                title__icontains="existing jobs matched your new alert",
            ).exists()
        )


class ApplicationDetailTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(
            username="emp_app", password="pass", role="employer", email="emp_app@example.com", is_active=True
        )
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user, company_name="ACME", phone="000", company_description="addr"
        )
        self.seeker_user = User.objects.create_user(
            username="js_app", password="pass", role="jobseeker", email="js_app@example.com", is_active=True
        )
        self.seeker_profile = JobSeekerProfile.objects.create(user=self.seeker_user, full_name="Job Seeker", education="CS", skills="python")
        self.job = Job.objects.create(employer=self.employer_profile, title="Backend", description="Django", location="Remote")
        self.app = JobApplication.objects.create(job=self.job, jobseeker=self.seeker_profile, resume="resumes/test.pdf")

    def test_employer_can_open_application_detail(self):
        self.client.login(username="emp_app", password="pass")
        resp = self.client.get(reverse("application_detail", args=[self.app.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Application")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="no-reply@test.local")
class NotificationTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username="emp", password="pass", role="employer", email="emp@example.com", is_active=True)
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user, company_name="ACME", phone="000", company_description="addr"
        )

        self.seeker_user = User.objects.create_user(username="js", password="pass", role="jobseeker", email="js@example.com", is_active=True)
        self.seeker_profile = JobSeekerProfile.objects.create(user=self.seeker_user, full_name="Job Seeker", education="CS", skills="python")

        self.job = Job.objects.create(employer=self.employer_profile, title="Backend", description="Django", location="Remote")
        self.app = JobApplication.objects.create(job=self.job, jobseeker=self.seeker_profile, resume="resumes/test.pdf")

    def test_schedule_interview_sends_email(self):
        self.client.login(username="emp", password="pass")
        resp = self.client.post(
            reverse("schedule_interview", args=[self.app.id]),
            {"interview_date": "2026-02-01", "interview_time": "10:30"},
        )
        self.assertEqual(resp.status_code, 302)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "interview")
        self.assertEqual(str(self.app.interview_time), "10:30:00")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Interview scheduled", mail.outbox[0].subject)
        self.assertTrue(Notification.objects.filter(user=self.seeker_user, title__icontains="Interview scheduled").exists())

    def test_reject_sends_email(self):
        self.client.login(username="emp", password="pass")
        resp = self.client.get(reverse("reject_application", args=[self.app.id]))
        self.assertEqual(resp.status_code, 302)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, "rejected")
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(Notification.objects.filter(user=self.seeker_user, title__icontains="Application update").exists())
