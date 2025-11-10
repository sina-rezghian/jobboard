from django.db import models
from accounts.models import JobSeekerProfile
from jobs.models import Job


class Resume(models.Model):
    job_seeker = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    related_job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_resumes')
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.job_seeker.full_name} - {self.file.name}"
