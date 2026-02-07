import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail


def send_email_demo(*, subject, message, to_email=None, to_emails=None, tag="EMAIL", meta=None, from_email=None):
    recipients = to_emails or ([] if to_email is None else [to_email])
    recipients = [r for r in recipients if r]
    if not recipients:
        recipients = ["demo@example.com"]

    send_mail(subject, message, from_email or settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)

    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "subject": subject,
        "to": recipients,
        "meta": meta or {},
        "message": message,
    }
    log_path = Path(getattr(settings, "EMAIL_DEMO_LOG", settings.LOG_DIR / "email_demo.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")

    employer_id = (meta or {}).get("employer_user_id")
    if employer_id:
        per = log_path.parent / "email" / f"employer_{employer_id}.jsonl"
        per.parent.mkdir(parents=True, exist_ok=True)
        per.open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")
