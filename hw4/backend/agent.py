"""Handsome Dan: agent entry and wiring.

Loads the system prompt from prompts/prompt.md, builds the Portkey-routed
OpenAI model named by OPENAI_MODEL, registers the tools, and keeps each
conversation's memory and rule-violation strikes.
"""

import asyncio
import functools
import inspect
import json
import logging
import os
import secrets
import time
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import audit
import factcheck
import history
import tools
from auth import connect
from models import DanReply, ShopDeps

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
load_dotenv(HERE.parent / ".env")

logger = logging.getLogger("campus_customs")

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_NAME = os.getenv("OPENAI_MODEL") or "gpt-5.6-luna"
PROMPT_PATH = HERE / "prompts" / "prompt.md"

# ---------- Loop protection (specs) ----------
MAX_MODEL_REQUESTS = 8  # AI calls per shopper message
MAX_TOOL_CALLS = 10  # tool calls per shopper message
MAX_IDENTICAL_CALLS = 2  # same tool + same inputs; a third identical call stops the run
RUN_TIMEOUT_SECONDS = 60  # one minute per answer, then a polite "please try again"
FACT_CHECK_RETRIES = 2  # chances Dan gets to fix a reply the fact-checker rejects

MAX_STRIKES = 3
MAX_HISTORY_MESSAGES = 40
CONVERSATION_TTL_SECONDS = 6 * 60 * 60


def build_model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing. Add it to hw4/.env.")
    client = AsyncOpenAI(
        api_key=api_key, base_url=PORTKEY_BASE_URL, default_headers={"x-portkey-provider": "openai"}
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


class LoopStop(Exception):
    """Raised by the loop guard to stop a run that's going in circles."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def guarded(fn):
    """Wrap a tool so every call is logged for the audit trail and loop limits are enforced."""
    name = fn.__name__
    signature = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(ctx: RunContext[ShopDeps], *args, **kwargs):
        bound = signature.bind(ctx, *args, **kwargs)
        bound.apply_defaults()
        call_args = {k: v for k, v in bound.arguments.items() if k != "ctx"}
        entry = {"tool": name, "args": audit.summarize_args(call_args)}
        ctx.deps.tool_log.append(entry)

        key = name + json.dumps(call_args, sort_keys=True, default=str)
        ctx.deps.call_counts[key] = ctx.deps.call_counts.get(key, 0) + 1
        if ctx.deps.call_counts[key] > MAX_IDENTICAL_CALLS:
            entry["result"] = "STOPPED: same call repeated"
            raise LoopStop("repeated_tool_call")
        if len(ctx.deps.tool_log) > MAX_TOOL_CALLS:
            entry["result"] = "STOPPED: tool-call cap reached"
            raise LoopStop("tool_call_limit")
        try:
            result = fn(ctx, *args, **kwargs)
        except ModelRetry as retry:
            entry["result"] = "retry: " + audit.scrub(retry.message, 60)
            raise
        entry["result"] = audit.summarize_result(name, result)
        return result

    return wrapper


dan = Agent(
    build_model(),
    output_type=DanReply,
    deps_type=ShopDeps,
    instructions=PROMPT_PATH.read_text(encoding="utf-8"),
    tools=[guarded(t) for t in tools.ALL_TOOLS],
    retries=FACT_CHECK_RETRIES,
)


@dan.instructions
def shopper_context(ctx: RunContext[ShopDeps]) -> str:
    """Who is chatting and which page they're on, rebuilt fresh for every message."""
    d = ctx.deps
    lines = ["## Current shopper (from the server, not from the chat)"]
    if d.user_id is None:
        lines.append("- Status: guest (not logged in). Their chat will not be saved.")
        if d.is_first_message:
            lines.append(
                "- This is the guest's FIRST message. After answering it, add one short, friendly sentence "
                "inviting them to create a free account so their chat history is saved for next time, using the "
                "'Create a free account' button that appears right below your message (don't mention page "
                "positions like top or right). Make it optional and don't repeat the invitation later."
            )
    else:
        lines += [
            "- Status: logged in. Their chat history is saved and earlier conversation may appear above.",
            f"- Name: {d.first_name} {d.last_name or ''}".rstrip(),
            f"- Email: {d.email}",
            "- Greet them by first name when natural. Only mention their email if they ask what email is on "
            "their account. Never reveal or discuss any other customer.",
        ]
    lines.append("")
    lines.append("## Current page")
    if d.viewing_product:
        p = d.viewing_product
        lines += [
            f"- Product page open: '{p['name']}' (product_id '{p['product_id']}'), a {p['garment_type']}.",
            f"- Design colors on this item: {', '.join(p['colors']) or 'not listed'}.",
            '- If they say "this", "it" or "this one" without naming a product, they mean this item. '
            "Use your tools for its price, stock and description.",
        ]
    else:
        lines.append("- Not on a product page.")
    return "\n".join(lines)


# ---------- Fact-checker ----------

@dan.output_validator
def fact_check(ctx: RunContext[ShopDeps], output: DanReply) -> DanReply:
    """Check every price, stock count, size claim and color against the database before sending.
    A mistake sends the reply back to Dan with the exact problem so he can fix it."""
    # Tool results from this turn only (everything after the shopper's latest message).
    turn_start = max(
        (i for i, m in enumerate(ctx.messages)
         if isinstance(m, ModelRequest) and any(isinstance(p, UserPromptPart) for p in m.parts)),
        default=0,
    )
    tool_results = [
        part.content
        for m in ctx.messages[turn_start:]
        if isinstance(m, ModelRequest)
        for part in m.parts
        if isinstance(part, ToolReturnPart)
    ]
    user_message = ctx.prompt if isinstance(ctx.prompt, str) else ""
    viewing = ctx.deps.viewing_product["product_id"] if ctx.deps.viewing_product else None
    problems, claims = factcheck.check_reply(
        output.reply,
        user_message=user_message,
        tool_results=tool_results,
        product_ids=tools.valid_product_ids(output.product_ids),
        viewing_product_id=viewing,
    )
    ctx.deps.facts_checked = claims
    if problems:
        ctx.deps.corrections += 1
        logger.warning("Fact-check caught: %s", " | ".join(problems))
        raise ModelRetry(
            "Fact-check failed. Fix these before replying, using your tools for exact data:\n- "
            + "\n- ".join(problems)
        )
    return output


# ---------- Conversations ----------

class Conversation:
    def __init__(self, user_id: int | None):
        self.user_id = user_id
        self.history: list[ModelMessage] = []
        self.transcript: list[dict] = []  # guest messages, saved if they sign up or log in mid-chat
        self.strikes = 0
        self.ended = False
        self.last_used = time.time()


_conversations: dict[str, Conversation] = {}


def get_conversation(conversation_id: str | None, user_id: int | None) -> tuple[str, Conversation]:
    """Reuse the shopper's conversation, or start a new one (also when the logged-in user changed)."""
    now = time.time()
    for cid in [c for c, conv in _conversations.items() if now - conv.last_used > CONVERSATION_TTL_SECONDS]:
        del _conversations[cid]
    conv = _conversations.get(conversation_id or "")
    if conv is None or conv.user_id != user_id:
        conversation_id = secrets.token_urlsafe(16)
        conv = _conversations[conversation_id] = Conversation(user_id)
        if user_id is not None:
            # A returning shopper: give Dan their saved conversation as memory.
            conv.history = history.to_model_history(history.load_messages(user_id))
    conv.last_used = now
    return conversation_id, conv


def claim_conversation(conversation_id: str, user_id: int) -> bool:
    """A guest just signed up or logged in: save their chat so far to their account and keep going."""
    conv = _conversations.get(conversation_id)
    if conv is None or conv.user_id is not None or conv.ended:
        return False
    for m in conv.transcript:
        history.save_message(user_id, m["role"], m["content"], m.get("product_ids"))
    conv.transcript = []
    conv.user_id = user_id
    return True


def forget_user_conversations(user_id: int) -> None:
    """Used by "Clear my chat history": drop Dan's in-memory copy too."""
    for cid in [c for c, conv in _conversations.items() if conv.user_id == user_id]:
        del _conversations[cid]


def record_exchange(conv: Conversation, user_id: int | None, message: str, reply: DanReply) -> None:
    turn = [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply.reply, "product_ids": reply.product_ids[:6]},
    ]
    if user_id is None:
        conv.transcript.extend(turn)
    else:
        for m in turn:
            history.save_message(user_id, m["role"], m["content"], m.get("product_ids"))


def trim_history(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep recent memory, cutting only at the start of a shopper's turn so tool calls stay paired."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    for i in range(len(messages) - MAX_HISTORY_MESSAGES, len(messages)):
        msg = messages[i]
        if isinstance(msg, ModelRequest) and any(isinstance(p, UserPromptPart) for p in msg.parts):
            return messages[i:]
    return messages[-MAX_HISTORY_MESSAGES:]


def flag_account(user_id: int, reason: str, excerpt: str) -> None:
    """Record repeated rule-breaking for an administrator to review."""
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS abuse_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                excerpt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                reviewed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            "INSERT INTO abuse_flags (user_id, reason, excerpt) VALUES (?, ?, ?)",
            (user_id, reason[:300], excerpt[:500]),
        )


def is_flagged(user_id: int | None) -> bool:
    if user_id is None:
        return False
    with connect() as conn:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'abuse_flags'"
        ).fetchone()
        if not table:
            return False
        return conn.execute(
            "SELECT 1 FROM abuse_flags WHERE user_id = ? AND reviewed = 0", (user_id,)
        ).fetchone() is not None


UNVERIFIED_REPLY = (
    "Woof, I want to be sure I give you exact numbers, and I couldn't double-check that one. "
    "The product page always shows the current price and stock by size."
)

BLOCKED_REPLY = (
    "Woof. I can only help with Campus Customs shopping and a little Yale lore, "
    "and I can't follow requests to change or get around my rules."
)


def is_content_filter_block(error: Exception) -> bool:
    """The AI provider's own safety filter rejected the message (e.g. a jailbreak attempt)."""
    return isinstance(error, ModelHTTPError) and error.status_code == 400 and "content_filter" in str(error)


TRY_AGAIN_REPLY = (
    "Ruff, that one is taking me longer than it should. Please try asking again, "
    "maybe in a slightly different way."
)


def _find(error: BaseException | None, kind: type, _depth: int = 0) -> BaseException | None:
    """Find an exception of `kind`, even inside an exception group or as a cause."""
    if error is None or _depth > 6:
        return None
    if isinstance(error, kind):
        return error
    for inner in getattr(error, "exceptions", ()):
        found = _find(inner, kind, _depth + 1)
        if found:
            return found
    return _find(error.__cause__ or error.__context__, kind, _depth + 1)


def audit_run(
    conv: "Conversation",
    conversation_id: str | None,
    deps: ShopDeps,
    message: str,
    stop_reason: str,
    started: float,
    reply: DanReply | None = None,
    model_requests: int | None = None,
) -> None:
    """One audit-trail line per answer: what Dan did and why he stopped (no personal data)."""
    viewing = deps.viewing_product["product_id"] if deps.viewing_product else None
    audit.append(
        {
            "conversation": audit.conversation_tag(conversation_id),
            "shopper": "logged in" if deps.user_id is not None else "guest",
            "page": f"product page: {viewing}" if viewing else "other page",
            "message_chars": len(message),
            "tool_calls": deps.tool_log,
            "tool_call_count": len(deps.tool_log),
            "model_requests": model_requests,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stop_reason": stop_reason,
            "reply": None
            if reply is None
            else {
                "chars": len(reply.reply),
                "product_cards": len(reply.product_ids),
                "page_picks": reply.show_on_page,
                "off_topic": reply.off_topic,
                "rule_violation": reply.rule_violation,
            },
            "fact_check": {"claims_checked": deps.facts_checked, "corrections": deps.corrections},
            "strikes": conv.strikes,
            "chat_ended": conv.ended,
        }
    )


async def ask_dan(conv: Conversation, message: str, deps: ShopDeps, conversation_id: str | None = None) -> DanReply:
    started = time.monotonic()
    model_requests = None
    try:
        result = await asyncio.wait_for(
            dan.run(
                message,
                deps=deps,
                message_history=conv.history,
                usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS, tool_calls_limit=MAX_TOOL_CALLS + 2),
            ),
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except Exception as error:  # noqa: BLE001 - every outcome is classified and audited below
        loop_stop = _find(error, LoopStop)
        limit = _find(error, UsageLimitExceeded)
        http_error = _find(error, ModelHTTPError)
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            stop, reply = "timeout_1_minute", DanReply(reply=TRY_AGAIN_REPLY)
        elif loop_stop:
            stop, reply = loop_stop.reason, DanReply(reply=TRY_AGAIN_REPLY)
        elif limit:
            stop = "tool_call_limit" if "tool" in str(limit).lower() else "model_request_limit"
            reply = DanReply(reply=TRY_AGAIN_REPLY)
        elif _find(error, UnexpectedModelBehavior):
            # Still failing the fact-check after retries: send nothing unverified.
            logger.warning("Fact-check: reply withheld after repeated corrections")
            stop, reply = "fact_check_withheld", DanReply(reply=UNVERIFIED_REPLY)
        elif http_error and is_content_filter_block(http_error):
            # Count it as a strike; the blocked message is left out of Dan's memory.
            stop = "blocked_by_safety_filter"
            reply = DanReply(
                reply=BLOCKED_REPLY,
                rule_violation=True,
                violation_reason="Message blocked by the AI provider's safety filter",
            )
        else:
            audit_run(conv, conversation_id, deps, message, f"error: {type(error).__name__}", started)
            raise
    else:
        conv.history = trim_history(result.all_messages())
        reply = result.output
        reply.product_ids = tools.valid_product_ids(reply.product_ids)
        usage = result.usage() if callable(result.usage) else result.usage
        model_requests = usage.requests
        stop = "finished_after_fact_check_correction" if deps.corrections else "finished"

    if reply.rule_violation:
        conv.strikes += 1
        if conv.strikes >= MAX_STRIKES:
            conv.ended = True
            stop = f"{stop}; chat_ended_after_{MAX_STRIKES}_strikes"
            if deps.user_id is not None:
                flag_account(deps.user_id, reply.violation_reason or "Repeated rule violations", message)

    audit_run(conv, conversation_id, deps, message, stop, started, reply, model_requests)

    if not conv.ended and reply.reply not in (BLOCKED_REPLY, TRY_AGAIN_REPLY):
        record_exchange(conv, deps.user_id, message, reply)
    return reply
