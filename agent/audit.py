"""Append-only structured audit log. Every mandate transition and tool
call goes through here -- this file IS the audit trail deliverable."""

import json
import time
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "audit_trail.jsonl")


def log_event(stage: str, event: str, detail: dict, reasoning: str = "", session_id: str = None):
    entry = {
        "timestamp": time.time(),
        "session_id": session_id,  # correlates all events for one checkout -- used by evidence.py
        "stage": stage,       # intent | cart | payment | razorpay | rejection
        "event": event,       # e.g. "cart_created", "payment_rejected"
        "detail": detail,
        "reasoning": reasoning,
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_session(session_id: str):
    """Returns only the events belonging to one checkout session, in
    order -- this is the input to evidence.py's dispute evidence report."""
    return [e for e in read_log() if e.get("session_id") == session_id]


def clear_log():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)