import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings


def send_sms_demo(to_number, message, tag="SMS", meta=None, phone=None):
    target = to_number or phone or "unknown"
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "to": target,
        "message": message,
        "meta": meta or {},
    }
    log_path = Path(getattr(settings, "SMS_DEMO_LOG", settings.LOG_DIR / "sms_demo.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")

    employer_id = (meta or {}).get("employer_user_id")
    if employer_id:
        per = log_path.parent / "sms" / f"employer_{employer_id}.jsonl"
        per.parent.mkdir(parents=True, exist_ok=True)
        per.open("a", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False) + "\n")
