"""Demo SMS helper.

Instead of sending real SMS (which needs a paid provider/API),
we store outgoing SMS messages in a local log file so you can
show it to the instructor as the 'SMS' output.

Extra: we store each SMS as a JSON line so we can filter and show
messages per employer (or per user) inside the UI.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def send_sms_demo(
    phone: str,
    message: str,
    *,
    tag: str = "SMS DEMO",
    meta: dict[str, Any] | None = None,
) -> Path | None:
    try:
        log_path = getattr(settings, "SMS_DEMO_LOG", None)
        if not log_path:
            return None

        log_path = Path(str(log_path))
        log_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tag": tag,
            "phone": phone,
            "message": message,
            "meta": meta or {},
        }
        # Global SMS log
        _append_jsonl(log_path, payload)

        # Also write per-employer/per-user logs (requested for demo/testing)
        base_dir = log_path.parent
        meta_ = payload.get("meta", {}) or {}

        employer_id = meta_.get("employer_user_id") or meta_.get("employer_id") or meta_.get("employer")
        if employer_id is not None:
            _append_jsonl(base_dir / "sms" / f"employer_{employer_id}.jsonl", payload)

        user_id = (
            meta_.get("user_id")
            or meta_.get("jobseeker_user_id")
            or meta_.get("job_seeker_user_id")
        )
        if user_id is not None:
            _append_jsonl(base_dir / "sms" / f"user_{user_id}.jsonl", payload)

        # Mirror the SMS content to terminal logs for easy copy/paste in demos.
        logger.info("SMS_DEMO phone=%s message=%s", phone, message)
        return log_path
    except Exception:
        # Don't break the request flow for a demo feature.
        return None
