from __future__ import annotations

from django.db import models
from django.db.models import Q

from accounts.models import EmployerProfile, JobSeekerProfile


def _tokenize_csv(text: str | None) -> list[str]:
    if not text:
        return []
    # split by comma / whitespace
    raw = []
    for part in text.replace("\n", " ").replace(";", ",").split(","):
        raw.extend(part.split())
    tokens = [t.strip().lower() for t in raw if t.strip()]
    # unique preserving order
    seen=set()
    out=[]
    for t in tokens:
        if t not in seen:
            out.append(t); seen.add(t)
    return out


class JobQuerySet(models.QuerySet):
    def recent(self):
        return self.order_by("-created_at")

    def for_employer(self, employer: EmployerProfile):
        return self.filter(employer=employer)

    def search(self, q: str | None = None, min_salary: int | None = None, max_salary: int | None = None, skills: str | None = None):
        qs = self
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))
        # salary overlap logic
        if min_salary is not None:
            qs = qs.filter(Q(max_salary__isnull=True) | Q(max_salary__gte=min_salary))
        if max_salary is not None:
            qs = qs.filter(Q(min_salary__isnull=True) | Q(min_salary__lte=max_salary))
        if skills:
            tokens = _tokenize_csv(skills)
            if tokens:
                cond = Q()
                for t in tokens:
                    cond |= Q(required_skills__icontains=t) | Q(title__icontains=t) | Q(description__icontains=t)
                qs = qs.filter(cond)
        return qs


class JobManager(models.Manager):
    def get_queryset(self):
        return JobQuerySet(self.model, using=self._db)

    def recent(self):
        return self.get_queryset().recent()

    def for_employer(self, employer: EmployerProfile):
        return self.get_queryset().for_employer(employer)

    def search(self, q: str | None = None, min_salary: int | None = None, max_salary: int | None = None, skills: str | None = None):
        return self.get_queryset().search(q=q, min_salary=min_salary, max_salary=max_salary, skills=skills)


class JobType(models.TextChoices):
    FULL_TIME = "full_time", "Full-time"
    PART_TIME = "part_time", "Part-time"
    CONTRACT = "contract", "Contract"
    INTERN = "intern", "Internship"
    REMOTE = "remote", "Remote"

class ExperienceLevel(models.TextChoices):
    ENTRY = "entry", "Entry"
    MID = "mid", "Mid"
    SENIOR = "senior", "Senior"
    LEAD = "lead", "Lead"


class Job(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)

    # Indeed-style fields
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.FULL_TIME,
    )
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.ENTRY,
    )
    cover_letter_required = models.BooleanField(
        default=False,
        help_text="If true, applicants must provide a cover letter.",
    )

    # Phase 4: extra job fields
    min_salary = models.PositiveIntegerField(blank=True, null=True)
    max_salary = models.PositiveIntegerField(blank=True, null=True)
    benefits = models.TextField(blank=True, null=True, help_text="Benefits/perks (optional).")
    required_skills = models.TextField(
        blank=True,
        null=True,
        help_text="Comma separated skills (e.g. Python, Django, SQL).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    objects = JobManager()

    def __str__(self):
        return self.title

    def skills_list(self) -> list[str]:
        return _tokenize_csv(self.required_skills)


class JobApplicationQuerySet(models.QuerySet):
    def submitted(self):
        return self.filter(status="submitted")

    def interviews(self):
        return self.filter(status="interview")

    def rejected(self):
        return self.filter(status="rejected")

    def for_job(self, job: Job):
        return self.filter(job=job)

    def for_jobseeker(self, jobseeker: JobSeekerProfile):
        return self.filter(jobseeker=jobseeker)


class JobApplicationManager(models.Manager):
    def get_queryset(self):
        return JobApplicationQuerySet(self.model, using=self._db)

    def submitted(self):
        return self.get_queryset().submitted()

    def interviews(self):
        return self.get_queryset().interviews()

    def rejected(self):
        return self.get_queryset().rejected()

    def for_job(self, job: Job):
        return self.get_queryset().for_job(job)

    def for_jobseeker(self, jobseeker: JobSeekerProfile):
        return self.get_queryset().for_jobseeker(jobseeker)


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("interview", "Interview"),
        ("rejected", "Rejected"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    jobseeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name="applications")
    resume = models.FileField(upload_to="resumes/")
    cover_letter = models.TextField(blank=True, null=True)
    # Optional note from the job seeker (visible to the employer).
    note = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    interview_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")

    objects = JobApplicationManager()

    def __str__(self):
        return f"{self.jobseeker.user.username} → {self.job.title}"


class JobApplicationEvent(models.Model):
    """Status timeline event for an application (Phase 4+ / UI improvement)."""
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20, choices=JobApplication.STATUS_CHOICES)
    note = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.application_id}: {self.status}"


class SavedJob(models.Model):
    """Job bookmarks for job seekers."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by")
    jobseeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name="saved_jobs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("job", "jobseeker")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.jobseeker.user.username} saved {self.job.title}"


class JobAlert(models.Model):
    """Saved search / alert preferences for job seekers."""
    jobseeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name="job_alerts")
    keywords = models.CharField(max_length=255, blank=True, null=True, help_text="Keywords (title/skills).")
    min_salary = models.PositiveIntegerField(blank=True, null=True)
    max_salary = models.PositiveIntegerField(blank=True, null=True)
    skills = models.CharField(max_length=255, blank=True, null=True, help_text="Comma separated skills.")
    location = models.CharField(max_length=255, blank=True, null=True)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Alert({self.jobseeker.user.username})"


class JobAlertMatch(models.Model):
    """A matched job for an alert (in-app notification)."""
    alert = models.ForeignKey(JobAlert, on_delete=models.CASCADE, related_name="matches")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="alert_matches")
    created_at = models.DateTimeField(auto_now_add=True)
    is_seen = models.BooleanField(default=False)

    class Meta:
        unique_together = [("alert", "job")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Match({self.alert_id} -> {self.job_id})"


class ApplicationNote(models.Model):
    """Internal notes by employer about an application."""
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="notes")
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="application_notes")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note({self.employer_id} -> {self.application_id})"
