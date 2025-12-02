from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ResumeUploadForm
from .models import Resume
from accounts.models import JobSeekerProfile

@login_required
def upload_resume(request):
    # مطمئن شو user پروفایل jobseeker داره
    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "You must be a job seeker to upload a resume.")
        return redirect('home')

    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.jobseeker = seeker_profile
            resume.save()
            # Optional: also save latest resume into profile.file (if you want)
            # seeker_profile.resume = resume.file
            # seeker_profile.save()
            messages.success(request, "Resume uploaded successfully.")
            return redirect('resume_list')
    else:
        form = ResumeUploadForm()

    return render(request, 'resumes/upload.html', {'form': form})


@login_required
def resume_list(request):
    # if employer: show all resumes? but project says jobseeker should see own resumes
    # We'll show jobseeker their own resumes; employers will view resumes via job applications.
    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "You must be a job seeker to view your resumes.")
        return redirect('home')

    resumes = Resume.objects.filter(jobseeker=seeker_profile).order_by('-created_at')
    return render(request, 'resumes/list.html', {'resumes': resumes})
