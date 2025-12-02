from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Job, JobApplication
from .forms import JobCreateForm, JobApplicationForm
from accounts.models import EmployerProfile, JobSeekerProfile


@login_required
def create_job(request):
    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "You must be an employer to create a job.")
        return redirect('home')

    if request.method == 'POST':
        form = JobCreateForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = employer_profile
            job.created_at = timezone.now()
            job.save()
            messages.success(request, "Job created successfully.")
            return redirect('employer_jobs')
    else:
        form = JobCreateForm()

    return render(request, 'jobs/create_job.html', {'form': form})


@login_required
def employer_jobs(request):
    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "You must be an employer.")
        return redirect('home')

    jobs = Job.objects.filter(employer=employer_profile).order_by('-created_at')
    return render(request, 'jobs/employer_jobs.html', {'jobs': jobs})


def job_list(request):
    jobs = Job.objects.all().order_by('-created_at')
    return render(request, 'jobs/job_list.html', {'jobs': jobs})


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/job_detail.html', {'job': job})


@login_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "Only job seekers can apply.")
        return redirect('job_detail', job_id=job_id)

    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.job = job
            app.jobseeker = seeker_profile
            app.save()
            messages.success(request, "Application submitted.")
            return redirect('job_list')
    else:
        form = JobApplicationForm()

    return render(request, 'jobs/apply_job.html', {'form': form, 'job': job})


@login_required
def view_applications(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect('home')

    if job.employer != employer_profile:
        messages.error(request, "Not your job.")
        return redirect('home')

    applications = JobApplication.objects.filter(job=job).order_by('-submitted_at')
    return render(request, 'jobs/view_applications.html', {'applications': applications, 'job': job})


@login_required
def schedule_interview(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)

    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        return redirect('home')

    if application.job.employer != employer_profile:
        return redirect('home')

    if request.method == 'POST':
        date = request.POST.get('interview_date')
        application.interview_date = date
        application.status = 'interview'
        application.save()
        messages.success(request, "Interview scheduled.")
        return redirect('view_applications', job_id=application.job.id)

    return render(request, 'jobs/schedule_interview.html', {'application': application})


@login_required
def reject_application(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)

    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        return redirect('home')

    if application.job.employer != employer_profile:
        return redirect('home')

    application.status = 'rejected'
    application.save()
    messages.success(request, "Application rejected.")
    return redirect('view_applications', job_id=application.job.id)
