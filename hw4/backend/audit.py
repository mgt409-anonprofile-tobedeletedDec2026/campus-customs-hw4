"""Append-only audit trail of Handsome Dan's agent loop: output/audit_trail.json.

Format: a valid JSON array, one record per line. Each answer appends exactly one record just
before the closing "]" (the file is never rewritten, reordered or emptied), so the history
survives restarts and runs and the file always opens in any JSON viewer.

Privacy: this file is public. It records what Dan DID (tools, short inputs/results, limits, stop
reason), never who asked: no names, emails, user or account ids, and no chat message text (only
its length). Short tool inputs are scrubbed of anything that looks like an email or long number.
"""

import hashlib
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_lock = threading.Lock()

EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
LONG_NUMBER = re.compile(r"\d[\d\s-]{6,}\d")


def scrub(value, limit: int = 40) -> str:
    """Short, privacy-safe text for the log."""
    text = str(value)
    text = EMAIL.sub("[email removed]", text)
    text = LONG_NUMBER.sub("[number removed]", text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def conversation_tag(conversation_id: str | None) -> str | None:
    """A one-way fingerprint so runs from the same chat can be grouped without identifying anyone."""
    if not conversation_id:
        return None
    return hashlib.sha256(conversation_id.encode()).hexdigest()[:8]


def summarize_args(args: dict) -> dict:
    return {k: scrub(v) for k, v in args.items() if v not in (None, "", [])}


def summarize_result(tool: str, result) -> str:
    """One short line describing what a tool returned (counts and statuses, not personal data)."""
    if isinstance(result, str):
        return scrub(result, 60)
    if isinstance(result, list):
        return f"{len(result)} item(s)"
    if isinstance(result, BaseModel):
        d = result.model_dump()
        if tool == "search_products":
            return f"{d['total_matches']} match(es), returned {len(d['products'])}"
        if tool == "get_product_details":
            out = [s["size"] for s in d["sizes"] if s["quantity"] == 0]
            return f"{d['name']}: ${d['price']:.0f}, sold out in {', '.join(out) or 'no sizes'}"
        if tool == "check_stock":
            return f"{d['name']} {d['size']}: {d['status']} ({d['quantity']})"
        if tool == "find_alternatives":
            return (
                f"{d['requested_size']} {d['requested_status']}; "
                f"{len(d['adjacent_sizes_in_stock'])} adjacent size(s), {len(d['similar_in_size'])} similar item(s)"
            )
    return scrub(result, 60)


def append(record: dict) -> None:
    """Append one record to the audit trail. Never raises: logging must not break a shopper's chat."""
    record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    line = json.dumps(record, ensure_ascii=False).encode("utf-8")
    try:
        with _lock:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
                AUDIT_PATH.write_bytes(b"[\n" + line + b"\n]\n")
                return
            with AUDIT_PATH.open("r+b") as f:
                # Step back over the closing "]" (and trailing whitespace), then add ",<record>\n]".
                f.seek(0, 2)
                pos = f.tell()
                while pos > 0:
                    pos -= 1
                    f.seek(pos)
                    if f.read(1) == b"]":
                        break
                f.seek(pos)
                f.truncate()
                f.write(b",\n" + line + b"\n]\n")
    except OSError:
        pass
