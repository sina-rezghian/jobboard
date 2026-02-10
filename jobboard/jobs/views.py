import logging
from datetime import date as date_cls, timedelta, time as time_cls
from pathlib import Path
import json
import re
from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone

from django.conf import settings
from accounts.models import EmployerProfile, JobSeekerProfile
from resumes.models import Resume
from accounts.decorators import employer_required, jobseeker_required
from .constants import ENGLAND_CITIES
from .forms import JobForm, JobApplicationForm, JobAlertForm
from .models import Job, JobApplication, ApplicationNote, SavedJob, JobType, ExperienceLevel, JobAlertMatch
from .utils import (
    send_application_status_notification,
    process_job_alerts_for_job,
    process_alert_matches_for_alert,
    record_application_event,
    create_in_app_notification,
)

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


def _normalize_space(v: str | None) -> str:
    return re.sub(r"\s+", " ", (v or "")).strip()


def _tokenize_query(v: str | None) -> list[str]:
    return [part for part in re.split(r"\s+", _normalize_space(v).lower()) if part]


def _tokenize_reco_text(*values):
    """Tokenize profile/resume text into lowercase terms for recommendations."""
    tokens = set()
    for value in values:
        if not value:
            continue
        for token in re.findall(r"[a-z0-9+#\.]+", str(value).lower()):
            token = token.strip(".")
            if token and len(token) >= 2:
                tokens.add(token)
    return tokens


_SKILL_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "this",
    "that",
    "your",
    "have",
    "will",
    "you",
    "our",
    "role",
    "team",
}


def _extract_skill_tokens(*values):
    """Extract ordered skill-like tokens from free text."""
    out = []
    seen = set()
    for value in values:
        if not value:
            continue
        for token in re.findall(r"[a-z0-9+#\.]+", str(value).lower()):
            token = token.strip(".")
            if not token or len(token) < 2:
                continue
            if token in _SKILL_STOPWORDS or token.isdigit():
                continue
            if token not in seen:
                out.append(token)
                seen.add(token)
    return out


def _ensure_jobseeker_profile(user):
    profile = JobSeekerProfile.objects.filter(user=user).first()
    if profile:
        return profile
    if getattr(user, "role", "") != "jobseeker":
        return None
    return JobSeekerProfile.objects.create(
        user=user,
        full_name=(user.get_full_name() or user.username),
    )


def _popular_skill_suggestions(limit=12):
    counter = Counter()
    required_skills_values = (
        Job.objects.exclude(required_skills__isnull=True)
        .exclude(required_skills__exact="")
        .values_list("required_skills", flat=True)[:500]
    )
    for raw in required_skills_values:
        for token in _extract_skill_tokens(raw):
            counter[token] += 1
    seeker_skills_values = (
        JobSeekerProfile.objects.exclude(skills__isnull=True)
        .exclude(skills__exact="")
        .values_list("skills", flat=True)[:500]
    )
    for raw in seeker_skills_values:
        for token in _extract_skill_tokens(raw):
            counter[token] += 1
    return [token for token, _ in counter.most_common(limit)]


def _skill_suggestions_by_prefix(prefix: str, *, limit: int = 12) -> list[str]:
    prefix_norm = (prefix or "").strip().lower()
    pool = _popular_skill_suggestions(limit=120)
    if not prefix_norm:
        return pool[:limit]
    starts = [s for s in pool if s.startswith(prefix_norm)]
    contains = [s for s in pool if prefix_norm in s and not s.startswith(prefix_norm)]
    return (starts + contains)[:limit]


def _search_skill_suggestions(request, limit=12):
    suggestions = []
    seen = set()

    def _push(tokens):
        for token in tokens:
            if token in seen:
                continue
            suggestions.append(token)
            seen.add(token)
            if len(suggestions) >= limit:
                return True
        return False

    if request.user.is_authenticated and getattr(request.user, "role", "") == "jobseeker":
        seeker_profile = JobSeekerProfile.objects.filter(user=request.user).first()
        if seeker_profile:
            latest_resume = Resume.objects.filter(jobseeker=seeker_profile).order_by("-created_at").first()
            if _push(_extract_skill_tokens(seeker_profile.skills, getattr(latest_resume, "skills", None))):
                return suggestions[:limit]

    _push(_popular_skill_suggestions(limit=limit * 2))
    return suggestions[:limit]


def _apply_skill_suggestions(job, seeker_profile, latest_resume, limit=10):
    """Recommend skills to mention in the application cover letter."""
    ordered = []
    seen = set()

    seeker_tokens = set(
        _extract_skill_tokens(
            seeker_profile.skills,
            getattr(latest_resume, "skills", None),
            getattr(latest_resume, "education", None),
        )
    )

    for token in job.skills_list():
        if token in seeker_tokens and token not in seen:
            ordered.append(token)
            seen.add(token)
        if len(ordered) >= limit:
            return ordered

    for token in job.skills_list():
        if token not in seen:
            ordered.append(token)
            seen.add(token)
        if len(ordered) >= limit:
            return ordered

    for token in _extract_skill_tokens(job.title, job.description):
        if token not in seen:
            ordered.append(token)
            seen.add(token)
        if len(ordered) >= limit:
            return ordered

    for token in _popular_skill_suggestions(limit=limit * 2):
        if token not in seen:
            ordered.append(token)
            seen.add(token)
        if len(ordered) >= limit:
            return ordered

    return ordered[:limit]


def _last_7_days_application_series(apps_qs):
    """Return labels/values for last 7 days including today."""
    today = timezone.localdate()
    start = today - timedelta(days=6)
    days = [start + timedelta(days=i) for i in range(7)]

    counts = {d: 0 for d in days}
    rows = (
        apps_qs.filter(submitted_at__date__gte=start, submitted_at__date__lte=today)
        .annotate(day=TruncDate("submitted_at"))
        .values("day")
        .annotate(c=Count("id"))
    )
    for row in rows:
        day = row.get("day")
        if day in counts:
            counts[day] = row.get("c", 0)

    labels = [d.strftime("%a") for d in days]
    values = [counts[d] for d in days]
    return {
        "labels": labels,
        "values": values,
        "from": start.isoformat(),
        "to": today.isoformat(),
    }


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

    skill_suggestions = _popular_skill_suggestions(limit=30)
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

    return render(
        request,
        "jobs/create_job.html",
        {
            "form": form,
            "cities": ENGLAND_CITIES,
            "skill_suggestions": skill_suggestions,
        },
    )


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

    skill_suggestions = _popular_skill_suggestions(limit=30)
    if request.method == "POST":
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated.")
            logger.info("Job updated: job_id=%s employer=%s", job.id, request.user.username)
            return redirect("employer_jobs")
    else:
        form = JobForm(instance=job)

    return render(
        request,
        "jobs/edit_job.html",
        {
            "form": form,
            "job": job,
            "cities": ENGLAND_CITIES,
            "skill_suggestions": skill_suggestions,
        },
    )


# -----------------------------
# Public: Job browsing + search
# -----------------------------
def job_list(request):
    q = _normalize_space(request.GET.get("q"))
    company = _normalize_space(request.GET.get("company"))
    min_salary = _safe_int(request.GET.get("min_salary"))
    max_salary = _safe_int(request.GET.get("max_salary"))
    skills = _normalize_space(request.GET.get("skills"))
    city = _normalize_space(request.GET.get("city"))
    sort = (request.GET.get("sort") or "newest").strip().lower()
    job_type = (request.GET.get("job_type") or "").strip()
    experience_level = (request.GET.get("experience_level") or "").strip()
    cover_letter = (request.GET.get("cover_letter") or "any").strip().lower()
    cover_letter_required = None
    if cover_letter == "required":
        cover_letter_required = True
    elif cover_letter == "not_required":
        cover_letter_required = False

    valid_job_types = {choice[0] for choice in JobType.choices}
    valid_experience_levels = {choice[0] for choice in ExperienceLevel.choices}
    if job_type and job_type not in valid_job_types:
        job_type = ""
    if experience_level and experience_level not in valid_experience_levels:
        experience_level = ""

    qs = Job.objects.select_related("employer").search(
        q=q,
        min_salary=min_salary,
        max_salary=max_salary,
        skills=skills,
        company=company,
        job_type=job_type or None,
        experience_level=experience_level or None,
        cover_letter_required=cover_letter_required,
    )

    # Salary filtering is handled in JobQuerySet.search() with overlap semantics:
    # - requested min salary => keep jobs whose max can reach that value
    # - requested max salary => keep jobs whose min is not above that value

    # Location (city) filter
    # - empty/"all" should not filter
    # - users may type partial city names, so we use icontains
    if city and city.strip().lower() not in {"all", "all cities", "any"}:
        qs = qs.filter(location__icontains=city.strip())

    if sort == "salary_high":
        qs = qs.order_by("-max_salary", "-created_at")
    elif sort == "salary_low":
        qs = qs.order_by("min_salary", "-created_at")
    else:
        sort = "newest"
        qs = qs.order_by("-created_at")

    # City dropdown: fixed list (England), alphabetically.
    # This also enables quick-jump on keypress (e.g. typing "f" jumps to first city starting with f).
    cities = ENGLAND_CITIES
    page_obj = _paginate(request, qs, per_page=10)
    page_jobs = list(page_obj.object_list)

    saved_job_ids = set()
    if request.user.is_authenticated and getattr(request.user, "role", "") == "jobseeker":
        seeker_profile = JobSeekerProfile.objects.filter(user=request.user).first()
        if seeker_profile:
            page_job_ids = [job.id for job in page_jobs]
            if page_job_ids:
                saved_job_ids = set(
                    SavedJob.objects.filter(jobseeker=seeker_profile, job_id__in=page_job_ids).values_list("job_id", flat=True)
                )

    skills_fragment = _normalize_space((skills.split(",")[-1] if skills else ""))
    skill_suggestions = _skill_suggestions_by_prefix(skills_fragment, limit=14)

    ctx = {
        "page_obj": page_obj,
        "jobs": page_jobs,
        "q": q,
        "company": company,
        "min_salary": "" if min_salary is None else min_salary,
        "max_salary": "" if max_salary is None else max_salary,
        "skills": skills,
        "city": city,
        "job_type": job_type,
        "experience_level": experience_level,
        "cover_letter": cover_letter,
        "sort": sort,
        "cities": cities,
        "saved_job_ids": saved_job_ids,
        "skill_suggestions": skill_suggestions,
        "job_type_choices": JobType.choices,
        "experience_choices": ExperienceLevel.choices,
    }
    return render(request, "jobs/job_list.html", ctx)


def skill_suggestions_api(request):
    prefix = _normalize_space(request.GET.get("q"))
    items = _skill_suggestions_by_prefix(prefix, limit=12)
    return JsonResponse({"items": items})



def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    is_saved = False
    if request.user.is_authenticated and getattr(request.user, "role", "") == "jobseeker":
        seeker_profile = JobSeekerProfile.objects.filter(user=request.user).first()
        if seeker_profile:
            is_saved = SavedJob.objects.filter(job=job, jobseeker=seeker_profile).exists()
    return render(request, "jobs/job_detail.html", {"job": job, "is_saved": is_saved})


# -----------------------------
# Job Seeker: Apply + my apps
# -----------------------------
@jobseeker_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    seeker_profile = _ensure_jobseeker_profile(request.user)
    if not seeker_profile:
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

    skill_suggestions = _apply_skill_suggestions(job, seeker_profile, latest_resume)

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
                    phone=phone,
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

    return render(
        request,
        "jobs/apply_job.html",
        {
            "form": form,
            "job": job,
            "latest_resume": latest_resume,
            "skill_suggestions": skill_suggestions,
        },
    )


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
        raw_time = (request.POST.get("interview_time") or "").strip()
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

        parsed_time = None
        if raw_time:
            try:
                hh, mm = [int(x) for x in raw_time.split(":")[:2]]
                parsed_time = time_cls(hh, mm)
            except Exception:
                messages.error(request, "Invalid time format.")
                return redirect("schedule_interview", application_id=application.id)

        application.interview_date = parsed
        application.interview_time = parsed_time
        application.status = "interview"
        application.save(update_fields=["interview_date", "interview_time", "status"])
        when = f"{application.interview_date} {application.interview_time.strftime('%H:%M') if application.interview_time else ''}".strip()
        record_application_event(application, "interview", f"Interview scheduled: {when}")

        send_application_status_notification(application, kind="interview")
        messages.success(request, "Interview scheduled.")
        logger.info("Interview scheduled: app_id=%s when=%s", application.id, when)

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
@jobseeker_required
def recommended_jobs(request):
    """Profile/resume-aware recommendation with sensible fallback."""
    try:
        seeker_profile = JobSeekerProfile.objects.get(user=request.user)
    except JobSeekerProfile.DoesNotExist:
        messages.error(request, "You must be a job seeker.")
        return redirect("home")

    latest_resume = Resume.objects.filter(jobseeker=seeker_profile).order_by("-created_at").first()

    seeker_skills = _tokenize_reco_text(
        seeker_profile.skills,
        getattr(latest_resume, "skills", None),
    )
    edu_tokens = _tokenize_reco_text(
        seeker_profile.education,
        getattr(latest_resume, "education", None),
    )

    scored = []
    for job in Job.objects.select_related("employer").recent()[:300]:
        job_skills = set(job.skills_list())
        hay = f"{job.title} {job.description or ''} {job.required_skills or ''} {job.location or ''}".lower()

        exact_overlap = sorted(seeker_skills.intersection(job_skills)) if job_skills else []
        text_overlap = sorted(
            {
                token
                for token in seeker_skills
                if len(token) >= 3 and token not in exact_overlap and token in hay
            }
        )
        edu_hits = sorted({token for token in edu_tokens if len(token) >= 4 and token in hay})

        score = (len(exact_overlap) * 12) + (len(text_overlap) * 4) + (len(edu_hits) * 2)
        if score > 0:
            scored.append(
                {
                    "job": job,
                    "score": score,
                    "overlap": len(exact_overlap),
                    "overlap_terms": exact_overlap + text_overlap,
                }
            )

    scored.sort(
        key=lambda item: (
            -item["score"],
            -item["overlap"],
            -(item["job"].created_at.timestamp() if item["job"].created_at else 0),
        )
    )
    recommendations = scored[:30]

    used_fallback = False
    if not recommendations:
        used_fallback = True
        recommendations = [
            {"job": job, "score": 0, "overlap": 0, "overlap_terms": []}
            for job in Job.objects.select_related("employer").recent()[:12]
        ]

    return render(
        request,
        "jobs/recommended_jobs.html",
        {
            "recommendations": recommendations,
            "profile": seeker_profile,
            "used_fallback": used_fallback,
        },
    )


@jobseeker_required
def toggle_saved_job(request, job_id: int):
    seeker = _ensure_jobseeker_profile(request.user)
    if not seeker:
        messages.error(request, "Only job seekers can save jobs.")
        return redirect("home")

    job = get_object_or_404(Job, id=job_id)
    obj, created = SavedJob.objects.get_or_create(job=job, jobseeker=seeker)
    if not created:
        obj.delete()
        messages.info(request, "Removed from saved jobs.")
    else:
        messages.success(request, "Saved job.")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = None
    return redirect(next_url or "saved_jobs")

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
            created_matches = process_alert_matches_for_alert(alert, limit=300)
            if created_matches > 0:
                create_in_app_notification(
                    seeker.user,
                    title=f"{created_matches} existing jobs matched your new alert",
                    message="Open Alert Inbox to review them.",
                    url="/jobs/alerts/inbox/",
                )
                messages.success(request, f"Alert saved. Found {created_matches} existing matches.")
            else:
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
    qs = JobAlertMatch.objects.filter(alert__jobseeker=seeker).select_related("job", "job__employer", "job__employer__user", "alert")
    page_obj = _paginate(request, qs, per_page=10)
    page_ids = [m.id for m in page_obj.object_list]
    if page_ids:
        JobAlertMatch.objects.filter(id__in=page_ids, is_seen=False).update(is_seen=True)
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
        weekly_series = _last_7_days_application_series(apps_qs)
        ctx = {
            "role": "employer",
            "jobs_count": jobs_qs.count(),
            "apps_count": apps_qs.count(),
            "submitted_count": apps_qs.filter(status="submitted").count(),
            "interview_count": apps_qs.filter(status="interview").count(),
            "rejected_count": apps_qs.filter(status="rejected").count(),
            "recent_apps": apps_qs.select_related("job", "jobseeker", "jobseeker__user").order_by("-submitted_at")[:10],
            "weekly_chart_labels": weekly_series["labels"],
            "weekly_chart_values": weekly_series["values"],
            "weekly_chart_from": weekly_series["from"],
            "weekly_chart_to": weekly_series["to"],
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
        {
            "recent_jobs": recent_jobs,
            "featured_companies": featured_companies,
            "stats": stats,
            "hero_skill_suggestions": _popular_skill_suggestions(limit=20),
        },
    )
