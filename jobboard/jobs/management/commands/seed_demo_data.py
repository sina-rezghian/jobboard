import random
from datetime import timedelta, time

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import EmployerProfile, JobSeekerProfile, Notification
from jobs.constants import UK_CITIES
from jobs.models import ExperienceLevel, Job, JobAlert, JobApplication, JobType, SavedJob
from jobs.utils import record_application_event, process_alert_matches_for_alert, create_in_app_notification
from resumes.models import Resume

User = get_user_model()


class Command(BaseCommand):
    help = "Seed realistic demo/test data (employers, seekers, jobs, resumes, alerts, applications)."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", type=str, default="demo")
        parser.add_argument("--employers", type=int, default=6)
        parser.add_argument("--jobseekers", type=int, default=12)
        parser.add_argument("--jobs-per-employer", type=int, default=5)
        parser.add_argument("--applications-per-seeker", type=int, default=3)
        parser.add_argument("--password", type=str, default="DemoPass123!")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--wipe", action="store_true", help="Delete existing users starting with prefix before seeding.")

    def _skills(self, rnd, minimum=3, maximum=5):
        pool = [
            "python",
            "django",
            "postgresql",
            "react",
            "javascript",
            "docker",
            "aws",
            "linux",
            "sql",
            "figma",
            "ui/ux",
            "java",
            "spring",
            "typescript",
            "node.js",
            "git",
            "rest",
            "ci/cd",
        ]
        return ", ".join(sorted(rnd.sample(pool, rnd.randint(minimum, maximum))))

    def _make_user(self, username, email, role, password):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "role": role,
                "is_active": True,
                "is_email_verified": True,
            },
        )
        # Keep demo credentials predictable.
        user.email = email
        user.role = role
        user.is_active = True
        user.is_email_verified = True
        user.set_password(password)
        user.save()
        return user

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(opts["seed"])
        prefix = (opts["prefix"] or "demo").strip().lower()
        employers_n = max(1, int(opts["employers"]))
        seekers_n = max(1, int(opts["jobseekers"]))
        jobs_per_employer = max(1, int(opts["jobs_per_employer"]))
        apps_per_seeker = max(0, int(opts["applications_per_seeker"]))
        password = opts["password"]

        if opts["wipe"]:
            User.objects.filter(username__startswith=f"{prefix}_").delete()

        company_names = [
            "NorthBridge Labs",
            "Harbor Metrics",
            "BluePeak Systems",
            "CedarStone Digital",
            "OrbitGrid Tech",
            "Crownline Health",
            "Skyforge Data",
            "Granite Works",
        ]
        educations = [
            "BSc Computer Science",
            "BEng Software Engineering",
            "MSc Data Science",
            "Information Systems",
            "Bootcamp Graduate",
        ]
        job_templates = [
            ("Backend Developer", "Build and maintain APIs, background jobs, and PostgreSQL schemas."),
            ("Frontend Engineer", "Develop responsive interfaces with modern JavaScript and API integrations."),
            ("Full Stack Developer", "Own features end-to-end across Django, REST APIs, and frontend modules."),
            ("Data Analyst", "Transform product and hiring data into dashboards and actionable insights."),
            ("DevOps Engineer", "Automate CI/CD pipelines, deployments, and runtime monitoring."),
            ("QA Engineer", "Write test cases, automate regression suites, and improve release quality."),
            ("Product Designer", "Prototype user journeys and design system components with Figma."),
            ("Technical Recruiter", "Source candidates and coordinate interview pipelines with hiring managers."),
        ]
        location_pool = [c for c in UK_CITIES if c in {"London", "Manchester", "Leeds", "Bristol", "Liverpool", "Birmingham", "Remote", "Cambridge"}]
        if not location_pool:
            location_pool = ["London", "Manchester", "Remote"]

        created_jobs = []
        employer_creds = []
        seeker_creds = []

        for i in range(1, employers_n + 1):
            username = f"{prefix}_emp_{i}"
            email = f"{username}@example.com"
            user = self._make_user(username, email, User.Role.EMPLOYER, password)

            company_name = company_names[(i - 1) % len(company_names)]
            profile, _ = EmployerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": f"{company_name} {i}",
                    "company_description": "Hiring across engineering, product, and data teams.",
                    "phone": f"+44-20-7000-{1000 + i}",
                    "website": "https://example.com",
                },
            )
            if not profile.company_name:
                profile.company_name = f"{company_name} {i}"
                profile.save(update_fields=["company_name"])

            for j in range(1, jobs_per_employer + 1):
                title_base, description_base = job_templates[(j + i - 2) % len(job_templates)]
                title = f"{title_base} - Team {i}.{j}"
                location = location_pool[(i + j) % len(location_pool)]
                min_salary = rnd.randint(35_000, 95_000)
                max_salary = min_salary + rnd.randint(8_000, 35_000)
                required_skills = self._skills(rnd)

                job, _ = Job.objects.get_or_create(
                    employer=profile,
                    title=title,
                    location=location,
                    defaults={
                        "description": description_base,
                        "job_type": rnd.choice([choice for choice, _ in JobType.choices]),
                        "experience_level": rnd.choice([choice for choice, _ in ExperienceLevel.choices]),
                        "cover_letter_required": rnd.random() < 0.35,
                        "min_salary": min_salary,
                        "max_salary": max_salary,
                        "required_skills": required_skills,
                        "benefits": "Health insurance, flexible hours, learning budget",
                    },
                )
                created_jobs.append(job)

            employer_creds.append((username, password))

        seeker_profiles = []
        for i in range(1, seekers_n + 1):
            username = f"{prefix}_seeker_{i}"
            email = f"{username}@example.com"
            user = self._make_user(username, email, User.Role.JOBSEEKER, password)

            skills = self._skills(rnd)
            education = educations[(i - 1) % len(educations)]
            profile, _ = JobSeekerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": f"Demo Seeker {i}",
                    "education": education,
                    "skills": skills,
                    "phone": f"+44-77-9000-{2000 + i}",
                },
            )
            profile.education = profile.education or education
            profile.skills = profile.skills or skills
            profile.save(update_fields=["education", "skills"])
            seeker_profiles.append(profile)
            seeker_creds.append((username, password))

        
            resume = Resume.objects.filter(jobseeker=profile).order_by("-created_at").first()
            if not resume:
                resume = Resume(
                    jobseeker=profile,
                    title="Primary Resume",
                    education=profile.education,
                    skills=profile.skills,
                )
                resume.file.save(
                    f"{username}_resume.txt",
                    ContentFile(
                        f"Resume for {profile.full_name}\nEducation: {profile.education}\nSkills: {profile.skills}\n"
                    ),
                    save=True,
                )


            JobAlert.objects.get_or_create(
                jobseeker=profile,
                keywords="developer, engineer",
                skills="python, django",
                location=rnd.choice(["London", "Remote", "Manchester"]),
                min_salary=40_000,
                max_salary=130_000,
                defaults={"is_enabled": True},
            )

       
            for job in rnd.sample(created_jobs, k=min(2, len(created_jobs))):
                SavedJob.objects.get_or_create(job=job, jobseeker=profile)


        for profile in seeker_profiles:
            resume = Resume.objects.filter(jobseeker=profile).order_by("-created_at").first()
            resume_name = resume.file.name if resume and resume.file else f"resumes/{profile.user.username}_resume.txt"
            for job in rnd.sample(created_jobs, k=min(apps_per_seeker, len(created_jobs))):
                status = rnd.choices(["submitted", "interview", "rejected"], weights=[60, 25, 15], k=1)[0]
                application, created = JobApplication.objects.get_or_create(
                    job=job,
                    jobseeker=profile,
                    defaults={
                        "resume": resume_name,
                        "cover_letter": "I am interested in this role and believe my background is a strong fit.",
                        "note": "Seeded demo application",
                        "status": status,
                    },
                )
                if created and status == "interview":
                    interview_date = timezone.localdate() + timedelta(days=rnd.randint(1, 7))
                    interview_time = time(hour=rnd.randint(9, 17), minute=rnd.choice([0, 15, 30, 45]))
                    application.interview_date = interview_date
                    application.interview_time = interview_time
                    application.save(update_fields=["interview_date", "interview_time"])
                if created:
                    record_application_event(application, "submitted", "Application submitted (seed)")
                    if status in {"interview", "rejected"}:
                        if status == "interview":
                            when = f"{application.interview_date} {application.interview_time.strftime('%H:%M') if application.interview_time else ''}".strip()
                            record_application_event(application, status, f"Interview scheduled: {when} (seed)")
                        else:
                            record_application_event(application, status, f"Application moved to {status} (seed)")
                    create_in_app_notification(
                        job.employer.user,
                        title=f"New application for {job.title}",
                        message=f"Candidate: {profile.user.username}",
                        url=f"/jobs/application/{application.id}/",
                    )

   
        for profile in seeker_profiles:
            for alert in JobAlert.objects.filter(jobseeker=profile, is_enabled=True):
                created_matches = process_alert_matches_for_alert(alert, limit=500)
                if created_matches > 0:
                    create_in_app_notification(
                        profile.user,
                        title=f"{created_matches} jobs matched your alert",
                        message="Open your alert inbox to review matches.",
                        url="/jobs/alerts/inbox/",
                    )

        for username, _pwd in employer_creds:
            user = User.objects.filter(username=username).first()
            if user:
                Notification.objects.create(
                    user=user,
                    title="Employer account ready",
                    message="Your seeded dashboard includes jobs and applications.",
                    url="/jobs/dashboard/",
                )
        for username, _pwd in seeker_creds:
            user = User.objects.filter(username=username).first()
            if user:
                Notification.objects.create(
                    user=user,
                    title="Job seeker account ready",
                    message="Check alerts and recommended jobs.",
                    url="/jobs/dashboard/",
                )

        self.stdout.write(self.style.SUCCESS("Seeded demo data successfully."))
        self.stdout.write(f"Created/updated employers: {employers_n}")
        self.stdout.write(f"Created/updated job seekers: {seekers_n}")
        self.stdout.write(f"Created/updated jobs target: {employers_n * jobs_per_employer}")
        self.stdout.write("")
        self.stdout.write("Sample credentials:")
        for username, pwd in employer_creds[:3]:
            self.stdout.write(f"  {username} / {pwd}")
        for username, pwd in seeker_creds[:3]:
            self.stdout.write(f"  {username} / {pwd}")
