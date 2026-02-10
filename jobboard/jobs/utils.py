import logging
from jobboard.email_demo import send_email_demo
from jobboard.sms_demo import send_sms_demo

logger = logging.getLogger(__name__)


def _alert_label(alert) -> str:
   
    parts = []
    if getattr(alert, "keywords", None):
        parts.append(f"keywords: {alert.keywords}")
    if getattr(alert, "skills", None):
        parts.append(f"skills: {alert.skills}")
    if getattr(alert, "location", None):
        parts.append(f"location: {alert.location}")
    return " | ".join(parts) if parts else f"Alert #{alert.id}"


def send_application_status_notification(application, *, kind: str):
    user = application.jobseeker.user
    to_email = getattr(user, "email", None)
    job_title = application.job.title

    subject = ""
    body = ""
    interview_when = (
        f"{application.interview_date or 'TBD'} "
        f"{application.interview_time.strftime('%H:%M') if application.interview_time else ''}"
    ).strip()

    if kind == "interview":
        subject = f"JobBoard: Interview scheduled for {job_title}"
        body = (
            f"Hello {user.username},\n\n"
            f"Your application for '{job_title}' has been moved to INTERVIEW.\n"
            f"Interview date/time: {interview_when}\n\n"
            "Good luck!\n"
            "JobBoard"
        )
    elif kind == "rejected":
        subject = f"JobBoard: Update on your application for {job_title}"
        body = (
            f"Hello {user.username},\n\n"
            f"Unfortunately, your application for '{job_title}' was marked as REJECTED.\n\n"
            "Thanks for applying, and good luck with your job search.\n"
            "JobBoard"
        )
    else:
        return

    try:
        title = (
            f"Interview scheduled for {job_title}"
            if kind == "interview"
            else f"Application update for {job_title}"
        )
        message = (
            f"Interview date/time: {interview_when}"
            if kind == "interview"
            else "Your application status changed to rejected."
        )
        create_in_app_notification(
            user,
            title=title,
            message=message,
            url=f"/jobs/application/{application.id}/",
        )
    except Exception:
        logger.exception("In-app notification failed: kind=%s app_id=%s", kind, application.id)

    if to_email:
        meta = {
            "kind": kind,
            "application_id": application.id,
            "job_id": getattr(application.job, "id", None),
            "employer_user_id": getattr(getattr(getattr(application.job, "employer", None), "user", None), "id", None)
            or getattr(getattr(application.job, "employer", None), "user_id", None),
            "jobseeker_user_id": getattr(getattr(application, "jobseeker", None), "user_id", None)
            or getattr(getattr(getattr(application, "jobseeker", None), "user", None), "id", None),
        }
        try:
            send_email_demo(
                to_emails=[to_email],
                subject=subject,
                message=body,
                meta=meta,
            )
            logger.info("Email notification sent: kind=%s to=%s app_id=%s", kind, to_email, application.id)
        except Exception:
            logger.exception("Email notification failed: kind=%s to=%s app_id=%s", kind, to_email, application.id)


    phone = getattr(application.jobseeker, "phone", None)
    if phone:
        send_sms_demo(
            phone,
            f"[{kind.upper()}] {subject}",
            tag="APPLICATION",
            meta={
                "employer_user_id": application.job.employer.user_id,
                "employer_company": application.job.employer.company_name,
                "job_id": application.job_id,
                "job_title": job_title,
                "application_id": application.id,
                "jobseeker_user_id": user.id,
                "jobseeker_username": user.username,
                "kind": kind,
            },
        )


def record_application_event(application, status: str, note: str | None = None):
    """Create a timeline event for an application."""
    from .models import JobApplicationEvent
    try:
        JobApplicationEvent.objects.create(application=application, status=status, note=note)
    except Exception:
        logger.exception("Failed to record application event")


def process_job_alerts_for_job(job):
    """When a new job is created, match it against enabled job alerts and store in-app notifications."""
    from .models import JobAlert, JobAlertMatch
    from .models import _tokenize_csv  # reuse

    title_desc = f"{job.title} {job.description or ''} {job.required_skills or ''}".lower()
    job_skills = set(_tokenize_csv(job.required_skills))

    alerts = JobAlert.objects.filter(is_enabled=True).select_related("jobseeker", "jobseeker__user")
    for alert in alerts:
        if not _job_matches_alert(alert, job, title_desc, job_skills):
            continue
        _create_alert_match_and_notify(alert, job, JobAlertMatch)


def process_alert_matches_for_alert(alert, *, limit: int = 250) -> int:
    """Backfill matches for an alert against existing jobs.

    Returns count of newly created matches.
    """
    from .models import Job, JobAlertMatch
    from .models import _tokenize_csv

    if not getattr(alert, "is_enabled", False):
        return 0

    created_count = 0
    qs = Job.objects.select_related("employer", "employer__user").recent()[:limit]
    for job in qs:
        title_desc = f"{job.title} {job.description or ''} {job.required_skills or ''}".lower()
        job_skills = set(_tokenize_csv(job.required_skills))
        if not _job_matches_alert(alert, job, title_desc, job_skills):
            continue
        if _create_alert_match_and_notify(alert, job, JobAlertMatch):
            created_count += 1
    return created_count


def _job_matches_alert(alert, job, title_desc: str, job_skills: set[str]) -> bool:
    if alert.location and (alert.location.lower() not in (job.location or "").lower()):
        return False
    if alert.min_salary is not None:
        if job.max_salary is not None and job.max_salary < alert.min_salary:
            return False
    if alert.max_salary is not None:
        if job.min_salary is not None and job.min_salary > alert.max_salary:
            return False

    from .models import _tokenize_csv

    if alert.keywords:
        kws = [k.strip().lower() for k in alert.keywords.replace(";", ",").split(",") if k.strip()]
        if kws and not any(k in title_desc for k in kws):
            return False

    if alert.skills:
        need = set(_tokenize_csv(alert.skills))
        if need and job_skills:
            if not (need & job_skills):
                return False
        elif need:
            # no skills on job -> fallback to text contains
            if not any(s in title_desc for s in need):
                return False

    return True


def _create_alert_match_and_notify(alert, job, job_alert_match_model) -> bool:

    try:
        _match, created = job_alert_match_model.objects.get_or_create(alert=alert, job=job)
        if not created:
            return False

        label = _alert_label(alert)
        create_in_app_notification(
            alert.jobseeker.user,
            title=f"New job match: {job.title}",
            message=f"Matched your alert: {label}",
            url=f"/jobs/{job.id}/",
        )
        # Demo email/SMS notifications (logged under logs/)
        try:
            user = alert.jobseeker.user
            to_email = user.email or "demo@example.com"
            send_email_demo(
                subject="New job match (demo)",
                message=f"A new job matched your alert '{label}': {job.title} ({job.location})",
                to_emails=[to_email],
                meta={"user_id": user.id, "alert_id": alert.id, "job_id": job.id},
            )
            phone = getattr(alert.jobseeker, "phone", None) or "+440000000000"
            send_sms_demo(
                phone=phone,
                message=f"New job match: {job.title} in {job.location} (demo)",
                meta={"user_id": user.id, "alert_id": alert.id, "job_id": job.id},
            )
        except Exception:
            logger.exception("Failed to send demo alert notifications")
        return True
    except Exception:
        logger.exception("Failed to create JobAlertMatch")
        return False


def create_in_app_notification(user, title: str, message: str = "", url: str = ""):
    try:
        from accounts.models import Notification
        Notification.objects.create(user=user, title=title, message=message or None, url=url or None)
    except Exception:
        logger.exception("Failed to create in-app notification")
