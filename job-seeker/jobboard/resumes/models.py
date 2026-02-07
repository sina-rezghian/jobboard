from django.db import models
from accounts.models import JobSeekerProfile


class Resume(models.Model):
    jobseeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to="resumes/")
    title = models.CharField(max_length=200, blank=True)  # optional title for the resume
    education = models.CharField(max_length=255, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = getattr(self.jobseeker, "full_name", None) or self.jobseeker.user.username
        return f"{name} - {self.title or 'Resume'}"
