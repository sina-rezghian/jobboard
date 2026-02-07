import logging
from datetime import date as date_cls
from pathlib import Path
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme

from django.conf import settings
from accounts.models import EmployerProfile, JobSeekerProfile
from resumes.models import Resume
from accounts.decorators import employer_required, jobseeker_required
from .constants import ENGLAND_CITIES
from .forms import JobForm, JobApplicationForm, JobAlertForm
from .models import Job, JobApplication
from .utils import send_application_status_notification, process_job_alerts_for_job, record_application_event, create_in_app_notification

logger = logging.getLogger(__name__)

def _paginate(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)
    return page_obj


def _safe_int(v):
    try:
        if v is None or v == "":
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


# -----------------------------
# Employer: Create/Edit Jobs
# -----------------------------
@employer_required
def create_job(request):
    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "You must be an employer to create a job.")
        return redirect("home")

    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = employer_profile
            job.save()
            # Trigger job alerts (demo)
            process_job_alerts_for_job(job)
            messages.success(request, "Job posted.")
            logger.info("Job created: job_id=%s employer=%s", job.id, request.user.username)
            return redirect("employer_jobs")
    else:
        form = JobForm()

    return render(request, "jobs/create_job.html", {"form": form, "cities": ENGLAND_CITIES})


@employer_required
def employer_jobs(request):
    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "You must be an employer.")
        return redirect("home")

    jobs = Job.objects.for_employer(employer_profile).recent()
    return render(request, "jobs/employer_jobs.html", {"jobs": jobs})


@employer_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect("home")

    if job.employer != employer_profile:
        messages.error(request, "This is not your job posting.")
        return redirect("employer_jobs")

    if request.method == "POST":
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated.")
            logger.info("Job updated: job_id=%s employer=%s", job.id, request.user.username)
            return redirect("employer_jobs")
    else:
        form = JobForm(instance=job)

    return render(request, "jobs/edit_job.html", {"form": form, "job": job, "cities": ENGLAND_CITIES})


# -----------------------------
# Public: Job browsing + search
# -----------------------------
def job_list(request):
    q = (request.GET.get("q") or "").strip()
    min_salary = _safe_int(request.GET.get("min_salary"))
    max_salary = _safe_int(request.GET.get("max_salary"))
    skills = (request.GET.get("skills") or "").strip()
    city = (request.GET.get("city") or "").strip()

    qs = Job.objects.search(q=q, min_salary=min_salary, max_salary=max_salary, skills=skills).recent()

    # Salary filter semantics (matches the UI labels):
    # - "Min salary" means the job's advertised MIN must be >= this value.
    # - "Max salary" means the job's advertised MAX must be <= this value.
    if min_salary is not None:
        qs = qs.filter(min_salary__gte=min_salary)
    if max_salary is not None:
        qs = qs.filter(max_salary__lte=max_salary)

    # Location (city) filter
    # - empty/"all" should not filter
    # - users may type partial city names, so we use icontains
    if city and city.strip().lower() not in {"all", "all cities", "any"}:
        qs = qs.filter(location__icontains=city.strip())

    # City dropdown: fixed list (England), alphabetically.
    # This also enables quick-jump on keypress (e.g. typing "f" jumps to first city starting with f).
    cities = ENGLAND_CITIES
    page_obj = _paginate(request, qs, per_page=10)

    ctx = {
        "page_obj": page_obj,
        "jobs": page_obj.object_list,
        "q": q,
        "min_salary": "" if min_salary is None else min_salary,
        "max_salary": "" if max_salary is None else max_salary,
        "skills": skills,
        "city": city,
        "cities": cities,
    }
    return render(request, "jobs/job_list.html", ctx)



def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, "jobs/job_detail.html", {"job": job})


# -----------------------------
# Job Seeker: Apply + my apps
# -----------------------------
@jobseeker_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "Only job seekers can apply.")
        return redirect("job_detail", job_id=job_id)

    # Prevent duplicate applications
    if JobApplication.objects.filter(job=job, jobseeker=seeker_profile).exists():
        messages.info(request, "You already applied to this job.")
        return redirect("my_applications")

    # Enforce single resume: use latest uploaded resume
    latest_resume = Resume.objects.filter(jobseeker=seeker_profile).order_by("-created_at").first()
    if not latest_resume:
        messages.error(request, "Please upload your resume first (only one resume is used for all applications).")
        return redirect("upload_resume")

    if request.method == "POST":
        form = JobApplicationForm(request.POST, job=job)
        if form.is_valid():
            cover_letter = (form.cleaned_data.get("cover_letter") or "").strip()
            note = (form.cleaned_data.get("note") or "").strip()

            app = JobApplication(
                job=job,
                jobseeker=seeker_profile,
                resume=latest_resume.file,
                cover_letter=cover_letter or None,
                note=note or None,
            )
            app.save()
            record_application_event(app, "submitted", "Application submitted")

            # In-app notification for employer
            employer_user = job.employer.user
            create_in_app_notification(
                employer_user,
                title=f"New application for {job.title}",
                message=f"Candidate: {seeker_profile.user.username}",
                url=f"/jobs/application/{app.id}/",
            )

            # Demo email/SMS notifications (logged to files under logs/)
            notify_failed = False
            notify_failed = False
            try:
                from jobboard.email_demo import send_email_demo
                from jobboard.sms_demo import send_sms_demo

                send_email_demo(
                    subject="New job application (demo)",
                    message=(
                        f"You have a new application for '{job.title}'.\n"
                        f"Candidate: {seeker_profile.user.username}\n"
                        f"Application id: {app.id}"
                    ),
                    to_emails=[employer_user.email] if employer_user.email else ["demo@example.com"],
                    meta={
                        "job_id": job.id,
                        "application_id": app.id,
                        "employer_user_id": employer_user.id,
                    },
                )

                # If employer has no phone, we still log the attempt.
                phone = getattr(job.employer, "phone", None) or "+44-0000-000000"
                send_sms_demo(
                    to_number=phone,
                    message=f"(demo) New application for '{job.title}' (app #{app.id})",
                    meta={
                        "job_id": job.id,
                        "application_id": app.id,
                        "employer_user_id": employer_user.id,
                    },
                )
            except Exception:
                # Never break the UX because of demo services.
                notify_failed = True
                logger.exception("Demo notification failed")

            if notify_failed:
                messages.warning(request, "Application submitted, but demo notifications failed.")
            else:
                messages.success(request, "Application submitted.")
            logger.info(
                "Application submitted: app_id=%s job_id=%s user=%s",
                app.id,
                job.id,
                request.user.username,
            )
            return redirect("my_applications")
    else:
        form = JobApplicationForm(job=job)

    return render(request, "jobs/apply_job.html", {"form": form, "job": job, "latest_resume": latest_resume})


@jobseeker_required
def my_applications(request):
    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "You must be a job seeker.")
        return redirect("home")

    status = (request.GET.get("status") or "all").lower()
    allowed = {"all", "submitted", "interview", "rejected"}
    if status not in allowed:
        status = "all"

    base_qs = JobApplication.objects.for_jobseeker(seeker_profile).select_related("job", "job__employer")
    applications = base_qs
    if status != "all":
        applications = applications.filter(status=status)
    applications = applications.order_by("-submitted_at")

    counts = {
        "all": base_qs.count(),
        "submitted": base_qs.filter(status="submitted").count(),
        "interview": base_qs.filter(status="interview").count(),
        "rejected": base_qs.filter(status="rejected").count(),
    }

    return render(
        request,
        "jobs/my_applications.html",
        {"applications": applications, "status": status, "counts": counts},
    )


# -----------------------------
# Employer: applications dashboards
# -----------------------------
@employer_required
def employer_applications(request):
    """Employer: list all applications across all of their jobs."""
    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "You must be an employer.")
        return redirect("home")

    status = (request.GET.get("status") or "all").lower()
    allowed = {"all", "submitted", "interview", "rejected"}
    if status not in allowed:
        status = "all"

    base_qs = (
        JobApplication.objects.filter(job__employer=employer_profile)
        .select_related("job", "jobseeker", "jobseeker__user")
    )
    applications = base_qs
    if status != "all":
        applications = applications.filter(status=status)
    applications = applications.order_by("-submitted_at")

    counts = {
        "all": base_qs.count(),
        "submitted": base_qs.filter(status="submitted").count(),
        "interview": base_qs.filter(status="interview").count(),
        "rejected": base_qs.filter(status="rejected").count(),
    }

    return render(
        request,
        "jobs/employer_applications.html",
        {"applications": applications, "status": status, "counts": counts, "employer": employer_profile},
    )


@login_required

@employer_required
def employer_sms_log(request):
    """Employer: view demo SMS messages sent for their job applications.

    We filter SMS JSON lines by meta.employer_user_id == request.user.id.
    """
    try:
        EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect("home")

    log_path = getattr(settings, "SMS_DEMO_LOG", None)
    entries = []

    # Prefer per-employer demo log if available (LOG_DIR/sms/employer_<id>.jsonl)
    base_dir = None
    if log_path:
        base_dir = Path(str(log_path)).parent
    else:
        base_dir = Path(getattr(settings, "LOG_DIR", "."))

    employer_file = base_dir / "sms" / f"employer_{request.user.id}.jsonl"
    if employer_file.exists():
        for raw in employer_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    obj = json.loads(line)
                    entries.append(obj)
                except Exception:
                    continue
        # Already employer-scoped; no need to parse the global file
        return render(request, "jobs/employer_sms_log.html", {"entries": entries})

    if log_path:
        p = Path(str(log_path))
        if p.exists():
            for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line:
                    continue
                # Preferred: JSON lines
                if line.startswith("{"):
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    meta = obj.get("meta") or {}
                    if meta.get("employer_user_id") == request.user.id:
                        entries.append(obj)
                else:
                    # Legacy line format (no employer info) -> skip for safety
                    continue

    # Optional filtering by kind (interview/rejected)
    kind = request.GET.get("kind")
    if kind in {"interview", "rejected"}:
        entries = [e for e in entries if (e.get("meta") or {}).get("kind") == kind]

    # Newest first
    entries = list(reversed(entries))

    return render(
        request,
        "jobs/employer_sms_log.html",
        {"entries": entries, "kind": kind},
    )

def application_detail(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)

    # can view: owner employer (job.employer.user) OR the job seeker user
    can_manage = False
    employer_profile = None
    if request.user.is_authenticated:
        if getattr(request.user, "role", "") == "employer":
            try:
                employer_profile = EmployerProfile.objects.get(user=request.user)
                can_manage = (application.job.employer == employer_profile)
            except EmployerProfile.DoesNotExist:
                can_manage = False
        elif getattr(request.user, "role", "") == "jobseeker":
            can_manage = False

    if not can_manage and application.jobseeker.user != request.user:
        messages.error(request, "Access denied.")
        return redirect("home")

    next_url = request.GET.get("next")
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = None

    # Employer notes (internal)
    if request.method == "POST" and can_manage:
        note_content = (request.POST.get("note_content") or "").strip()
        if note_content:
            ApplicationNote.objects.create(application=application, employer=employer_profile, content=note_content)
            record_application_event(application, "note", "Employer added a note")
            messages.success(request, "Note saved.")
            return redirect(f"/jobs/application/{application.id}/?next={next_url}" if next_url else f"/jobs/application/{application.id}/")

    notes = ApplicationNote.objects.filter(application=application) if can_manage else []

    return render(
        request,
        "jobs/application_detail.html",
        {"application": application, "can_manage": can_manage, "next": next_url, "notes": notes},
    )


@employer_required
def view_applications(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect("home")

    if job.employer != employer_profile:
        messages.error(request, "Not your job.")
        return redirect("home")

    applications = JobApplication.objects.for_job(job).select_related("jobseeker__user").order_by("-submitted_at")
    return render(request, "jobs/view_applications.html", {"applications": applications, "job": job})


@employer_required
def schedule_interview(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)

    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect("home")

    if application.job.employer != employer_profile:
        messages.error(request, "Access denied.")
        return redirect("home")

    next_url = request.GET.get("next")
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = None

    if request.method == "POST":
        next_url = request.POST.get("next") or next_url
        if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = None

        raw = (request.POST.get("interview_date") or "").strip()
        if not raw:
            messages.error(request, "Please pick an interview date.")
            return redirect("schedule_interview", application_id=application.id)

        try:
            # raw is YYYY-MM-DD
            y, m, d = [int(x) for x in raw.split("-")]
            parsed = date_cls(y, m, d)
        except Exception:
            messages.error(request, "Invalid date format.")
            return redirect("schedule_interview", application_id=application.id)

        application.interview_date = parsed
        application.status = "interview"
        application.save()
        record_application_event(application, "interview", f"Interview scheduled: {application.interview_date}")

        send_application_status_notification(application, kind="interview")
        messages.success(request, "Interview scheduled.")
        logger.info("Interview scheduled: app_id=%s date=%s", application.id, parsed)

        if next_url:
            return redirect(next_url)
        return redirect("view_applications", job_id=application.job.id)

    return render(request, "jobs/schedule_interview.html", {"application": application})


@employer_required
def reject_application(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)

    next_url = request.GET.get("next")
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = None

    try:
        employer_profile = EmployerProfile.objects.get(user=request.user)
    except EmployerProfile.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect("home")

    if application.job.employer != employer_profile:
        messages.error(request, "Access denied.")
        return redirect("home")

    application.status = "rejected"
    application.save()
    record_application_event(application, "rejected", "Application rejected")

    send_application_status_notification(application, kind="rejected")
    messages.success(request, "Application rejected.")
    logger.info("Application rejected: app_id=%s", application.id)

    if next_url:
        return redirect(next_url)
    return redirect("view_applications", job_id=application.job.id)


# -----------------------------
# Bonus: Recommended jobs
# -----------------------------
@login_required
def recommended_jobs(request):
    """Simple recommendation based on skill overlap and education keywords."""
    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "You must be a job seeker.")
        return redirect("home")

    seeker_skills = set()
    if seeker_profile.skills:
        for token in seeker_profile.skills.replace("\n", " ").replace(";", ",").split(","):
            for s in token.split():
                s = s.strip().lower()
                if s:
                    seeker_skills.add(s)

    edu_tokens = set()
    if seeker_profile.education:
        for w in seeker_profile.education.replace("/", " ").split():
            w = w.strip().lower()
            if w:
                edu_tokens.add(w)

    scored = []
    for job in Job.objects.recent()[:200]:
        job_skills = set(job.skills_list())
        overlap = len(seeker_skills.intersection(job_skills)) if job_skills else 0

        edu_boost = 0
        if edu_tokens:
            hay = f"{job.title} {job.description}".lower()
            if any(t in hay for t in edu_tokens):
                edu_boost = 1

        score = overlap * 10 + edu_boost
        if score > 0:
            scored.append((score, overlap, job))
    scored = sorted(scored, key=lambda x: (-x[0], -x[1], -x[2].created_at.timestamp() if x[2].created_at else 0))

    recommendations = [{"job": j, "score": s, "overlap": o} for (s, o, j) in scored[:30]]

    return render(
        request,
        "jobs/recommended_jobs.html",
        {"recommendations": recommendations, "profile": seeker_profile},
    )


@jobseeker_required
def toggle_saved_job(request, job_id: int):
    seeker = JobSeekerProfile.objects.get(user=request.user)
    job = get_object_or_404(Job, id=job_id)
    from .models import SavedJob
    obj, created = SavedJob.objects.get_or_create(job=job, jobseeker=seeker)
    if not created:
        obj.delete()
        messages.info(request, "Removed from saved jobs.")
    else:
        messages.success(request, "Saved job.")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "job_list"
    return redirect(next_url)

@jobseeker_required
def saved_jobs(request):
    seeker = JobSeekerProfile.objects.get(user=request.user)
    from .models import SavedJob
    qs = SavedJob.objects.filter(jobseeker=seeker).select_related("job", "job__employer", "job__employer__user")
    page_obj = _paginate(request, qs, per_page=10)
    return render(request, "jobs/saved_jobs.html", {"saved_jobs": page_obj.object_list, "page_obj": page_obj})

@jobseeker_required
def job_alerts(request):
    seeker = JobSeekerProfile.objects.get(user=request.user)
    from .models import JobAlert
    if request.method == "POST":
        form = JobAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.jobseeker = seeker
            alert.save()
            messages.success(request, "Alert saved.")
            return redirect("job_alerts")
    else:
        form = JobAlertForm()
    alerts = JobAlert.objects.filter(jobseeker=seeker)
    return render(request, "jobs/job_alerts.html", {"alerts": alerts, "form": form})

@jobseeker_required
def delete_job_alert(request, alert_id: int):
    seeker = JobSeekerProfile.objects.get(user=request.user)
    from .models import JobAlert
    alert = get_object_or_404(JobAlert, id=alert_id, jobseeker=seeker)
    alert.delete()
    messages.info(request, "Alert deleted.")
    return redirect("job_alerts")

@jobseeker_required
def alert_inbox(request):
    seeker = JobSeekerProfile.objects.get(user=request.user)
    from .models import JobAlertMatch
    qs = JobAlertMatch.objects.filter(alert__jobseeker=seeker).select_related("job", "job__employer", "job__employer__user", "alert")
    page_obj = _paginate(request, qs, per_page=10)
    return render(request, "jobs/alert_inbox.html", {"matches": page_obj.object_list, "page_obj": page_obj})

@login_required
def dashboard(request):
    """Simple dashboard: shows different stats based on role."""
    user = request.user
    role = getattr(user, "role", "")
    if role == "employer":
        employer = EmployerProfile.objects.get(user=user)
        jobs_qs = Job.objects.for_employer(employer)
        apps_qs = JobApplication.objects.filter(job__employer=employer)
        ctx = {
            "role": "employer",
            "jobs_count": jobs_qs.count(),
            "apps_count": apps_qs.count(),
            "submitted_count": apps_qs.filter(status="submitted").count(),
            "interview_count": apps_qs.filter(status="interview").count(),
            "rejected_count": apps_qs.filter(status="rejected").count(),
            "recent_apps": apps_qs.select_related("job", "jobseeker", "jobseeker__user").order_by("-submitted_at")[:10],
        }
        return render(request, "jobs/dashboard_employer.html", ctx)
    elif role == "jobseeker":
        seeker = JobSeekerProfile.objects.get(user=user)
        apps_qs = JobApplication.objects.filter(jobseeker=seeker)
        from .models import SavedJob, JobAlertMatch
        ctx = {
            "role": "jobseeker",
            "apps_count": apps_qs.count(),
            "submitted_count": apps_qs.filter(status="submitted").count(),
            "interview_count": apps_qs.filter(status="interview").count(),
            "rejected_count": apps_qs.filter(status="rejected").count(),
            "saved_count": SavedJob.objects.filter(jobseeker=seeker).count(),
            "alerts_unseen": JobAlertMatch.objects.filter(alert__jobseeker=seeker, is_seen=False).count(),
            "recent_apps": apps_qs.select_related("job", "job__employer", "job__employer__user").order_by("-submitted_at")[:10],
        }
        return render(request, "jobs/dashboard_jobseeker.html", ctx)
    messages.info(request, "Dashboard is not available.")
    return redirect("home")

# -----------------------------
# Public landing page
# -----------------------------
def home_public(request):
    recent_jobs = Job.objects.select_related("employer").order_by("-created_at")[:12]
    featured_companies = (
        EmployerProfile.objects.annotate(jobs_count=Count("jobs"))
        .order_by("-jobs_count", "company_name")[:8]
    )
    # Stats shown in the hero area. We intentionally DO NOT show global "applications"
    # counts to job seekers (requested), and for employers we show only their own.
    show_applications_stat = False
    applications_count = None
    if request.user.is_authenticated:
        role = getattr(request.user, "role", None)
        if role == "employer":
            try:
                employer = EmployerProfile.objects.get(user=request.user)
                applications_count = JobApplication.objects.filter(job__employer=employer).count()
                show_applications_stat = True
            except EmployerProfile.DoesNotExist:
                pass
        # jobseeker: do not show

    stats = {
        "jobs": Job.objects.count(),
        "companies": EmployerProfile.objects.count(),
        "applications": applications_count,
        "show_applications": show_applications_stat,
    }
    return render(
        request,
        "jobs/home_public.html",
        {"recent_jobs": recent_jobs, "featured_companies": featured_companies, "stats": stats},
    )
