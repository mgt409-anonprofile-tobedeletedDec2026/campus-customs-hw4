"""Spam and bot protection for the chat, checked BEFORE any AI call (so attacks cost nothing).

In-memory and per backend process, which is enough for a single-server shop. Limits:
- per network address: 10 messages a minute and 100 an hour (stops floods and scripted bots)
- per conversation: at least 1 second between messages (humans can't type that fast)
- per conversation: the same message repeated within 30 seconds is answered once, not re-run
"""

import time
from collections import deque

PER_MINUTE = 10
PER_HOUR = 100
MIN_GAP_SECONDS = 1.0
DUPLICATE_WINDOW_SECONDS = 30

_by_address: dict[str, deque] = {}
_last_by_conversation: dict[str, tuple[float, str]] = {}


def check(address: str, conversation_id: str, message: str) -> str | None:
    """Return a stop reason ("rate_limited", "too_fast", "duplicate_message") or None if allowed."""
    now = time.monotonic()
    stamps = _by_address.setdefault(address, deque())
    while stamps and now - stamps[0] > 3600:
        stamps.popleft()
    if len(stamps) >= PER_HOUR or sum(1 for t in stamps if now - t <= 60) >= PER_MINUTE:
        return "rate_limited"

    last = _last_by_conversation.get(conversation_id)
    normalized = " ".join(message.lower().split())
    if last:
        last_time, last_text = last
        if now - last_time < MIN_GAP_SECONDS:
            return "too_fast"
        if normalized == last_text and now - last_time < DUPLICATE_WINDOW_SECONDS:
            return "duplicate_message"

    stamps.append(now)
    _last_by_conversation[conversation_id] = (now, normalized)
    if len(_last_by_conversation) > 5000:  # keep memory bounded
        for key in list(_last_by_conversation)[:1000]:
            del _last_by_conversation[key]
    return None


MESSAGES = {
    "rate_limited": "Woof, that's a lot of messages in a short time. Let's take a breather; please try again in a minute.",
    "too_fast": "One sniff at a time, please! Give me a second between messages.",
    "duplicate_message": "Looks like that came through twice. My answer above still stands.",
}
