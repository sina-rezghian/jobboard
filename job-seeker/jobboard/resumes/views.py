import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import ResumeUploadForm
from .models import Resume
from accounts.models import JobSeekerProfile

logger = logging.getLogger(__name__)


@login_required
def upload_resume(request):
    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "You must be a job seeker to upload a resume.")
        logger.warning("Upload resume denied (not jobseeker): user=%s", request.user.username)
        return redirect("home")

    if request.method == "POST":
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Only one resume is kept per job seeker (latest replaces older ones)
            Resume.objects.filter(jobseeker=seeker_profile).delete()
            resume = form.save(commit=False)
            resume.jobseeker = seeker_profile
            resume.save()
            logger.info("Resume uploaded: resume_id=%s user=%s", resume.id, request.user.username)
            messages.success(request, "Resume uploaded successfully.")
            return redirect("resume_list")
        logger.warning("Resume upload failed: user=%s errors=%s", request.user.username, form.errors)
    else:
        form = ResumeUploadForm()

    return render(request, "resumes/upload.html", {"form": form})


@login_required
def resume_list(request):
    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "You must be a job seeker to view your resumes.")
        logger.warning("Resume list denied (not jobseeker): user=%s", request.user.username)
        return redirect("home")

    resumes = Resume.objects.filter(jobseeker=seeker_profile).order_by("-created_at")
    return render(request, "resumes/list.html", {"resumes": resumes})
