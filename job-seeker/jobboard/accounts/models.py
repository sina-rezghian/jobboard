from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model (Phase 3).

    We keep it minimal and compatible with Django auth, while adding:
    - unique email
    - role (employer / jobseeker)
    - email verification flag
    """
    class Role(models.TextChoices):
        EMPLOYER = "employer", "Employer"
        JOBSEEKER = "jobseeker", "Job Seeker"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, blank=True)
    is_email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class EmployerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=100)
    company_description = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.company_name


class JobSeekerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    education = models.CharField(max_length=100, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)

    def __str__(self):
        return self.full_name


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, null=True)
    url = models.CharField(max_length=300, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification({self.user_id}): {self.title}"
