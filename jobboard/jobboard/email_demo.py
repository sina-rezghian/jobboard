from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import re

from django.conf import settings
from django.core.mail import send_mail


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def send_email_demo(
    *,
    to_emails: Iterable[str] | None = None,
    to_email: str | None = None,
    from_email: str | None = None,
    subject: str,
    message: str,
    tag: str = "EMAIL",
    meta: dict[str, Any] | None = None,
    **_ignored: Any,
) -> None:

    
    if to_emails is None:
        to_emails = []
    if to_email:
        to_emails = list(to_emails) + [to_email]

    to_emails = [e for e in (to_emails or []) if e]
    if not to_emails:
        return

    meta = dict(meta or {})
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "ts": now,
        "tag": tag,
        "to": to_emails,
        "subject": subject,
        "message": message,
        "meta": meta,
    }

    log_path = getattr(settings, "EMAIL_DEMO_LOG", None)
    if not log_path:
        log_dir = Path(getattr(settings, "LOG_DIR", "."))
        log_path = log_dir / "jobboard_email.log"
    log_path = Path(str(log_path))

    _append_jsonl(log_path, payload)

    base_dir = log_path.parent
    (base_dir / "email").mkdir(parents=True, exist_ok=True)


    link = meta.get("activation_link") if isinstance(meta, dict) else None
    if not link:
        m = re.search(r"https?://\S+", message or "")
        link = m.group(0) if m else ""


    outbox_txt = base_dir / "email_outbox.txt"
    with outbox_txt.open("a", encoding="utf-8") as f:
        f.write("=" * 72 + "\n")
        f.write(f"Time: {now}\n")
        f.write(f"To: {', '.join(to_emails)}\n")
        f.write(f"Tag: {tag}\n")
        f.write(f"Subject: {subject}\n")
        if link:
            f.write(f"Link: {link}\n")
        f.write("\n")
        f.write((message or "").strip() + "\n\n")


    def _safe_name(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)

    for email in to_emails:
        rec_path = base_dir / "email" / f"to_{_safe_name(email)}.txt"
        with rec_path.open("a", encoding="utf-8") as f:
            f.write(f"[{now}] {tag} subject={subject}\n")
            if link:
                f.write(f"Link: {link}\n")
            f.write("---\n")


    employer_id = meta.get("employer_user_id") or meta.get("employer_id") if isinstance(meta, dict) else None
    if employer_id:
        _append_jsonl(base_dir / "email" / f"employer_{employer_id}.jsonl", payload)
    user_id = meta.get("user_id") if isinstance(meta, dict) else None
    if user_id:
        _append_jsonl(base_dir / "email" / f"user_{user_id}.jsonl", payload)


    send_mail(
        subject=subject,
        message=message,
        from_email=(from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@jobboard.local")),
        recipient_list=list(to_emails),
        fail_silently=False,
    )
