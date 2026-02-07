from django.db.models import Q

from accounts.models import Notification
from jobboard.email_demo import send_email_demo
from jobboard.sms_demo import send_sms_demo
from .models import JobAlert, JobAlertMatch, JobApplicationEvent, Job


def create_in_app_notification(user, title, message="", url=""):
    return Notification.objects.create(user=user, title=title, message=message, url=url)


def send_application_status_notification(application, kind="interview"):
    seeker_user = application.jobseeker.user
    title = "Interview scheduled" if kind == "interview" else "Application update"
    body = f"Your application for '{application.job.title}' is now: {application.get_status_display()}."
    if application.interview_date:
        body += f" Interview date: {application.interview_date}."

    create_in_app_notification(seeker_user, title=title, message=body, url=f"/jobs/application/{application.id}/")
    send_email_demo(
        subject=title,
        message=body,
        to_emails=[seeker_user.email] if seeker_user.email else ["demo@example.com"],
        tag="APPLICATION_STATUS",
        meta={"application_id": application.id, "kind": kind, "job_id": application.job_id},
    )
    send_sms_demo(
        to_number=application.jobseeker.phone or "+44-0000-000000",
        message=body,
        tag="APPLICATION_STATUS",
        meta={"application_id": application.id, "kind": kind, "job_id": application.job_id},
    )


def record_application_event(application, status, note=""):
    valid = {c[0] for c in application.STATUS_CHOICES}
    if status not in valid:
        status = application.status
    return JobApplicationEvent.objects.create(application=application, status=status, note=note or None)


def process_job_alerts_for_job(job: Job):
    q = Q(is_enabled=True)
    candidates = JobAlert.objects.filter(q).select_related("jobseeker", "jobseeker__user")
    hay = f"{job.title} {job.description} {job.required_skills or ''} {job.location}".lower()
    for alert in candidates:
        if alert.location and alert.location.lower() not in (job.location or "").lower():
            continue
        if alert.min_salary and (job.max_salary or 0) < alert.min_salary:
            continue
        if alert.max_salary and (job.min_salary or 10**9) > alert.max_salary:
            continue
        terms = [t.strip().lower() for t in (alert.keywords or "").replace(";", ",").split(",") if t.strip()]
        skills = [t.strip().lower() for t in (alert.skills or "").replace(";", ",").split(",") if t.strip()]
        if terms and not any(t in hay for t in terms):
            continue
        if skills and not any(s in hay for s in skills):
            continue
        match, created = JobAlertMatch.objects.get_or_create(alert=alert, job=job)
        if created:
            create_in_app_notification(
                alert.jobseeker.user,
                title="New job match",
                message=f"{job.title} in {job.location}",
                url=f"/jobs/{job.id}/",
            )
