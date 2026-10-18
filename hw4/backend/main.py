"""Campus Customs backend.

Serves the product catalogue, inventory and photos (read-only) and customer
accounts and shopping bags (auth.py and cart.py, the only code that writes to
the database), plus the /api/chat route to Handsome Dan, the PydanticAI agent
(agent.py, tools.py, models.py, prompts/prompt.md).

Run from the backend folder (with the hw4 virtual environment active):
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import sqlite3
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import audit
import history
import ratelimit
from privacy import remove_card_numbers
from agent import ask_dan, claim_conversation, forget_user_conversations, get_conversation, is_flagged
from auth import current_user_id, ensure_sessions_table, router as auth_router
from cart import ensure_cart_table, router as cart_router
from wishlist import ensure_wishlist_table, router as wishlist_router
from naming import display_name
from models import ChatRequest, ChatResponse, PagePicks, PickProduct, ProductCard, ShopDeps
from tools import valid_product_ids

logger = logging.getLogger("campus_customs")

CHAT_ENDED_MESSAGE = (
    "This chat has ended because of repeated attempts to break the shop's rules. "
    "If you're logged in, your account has been flagged for administrator review."
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
IMAGES_DIR = DATA_DIR / "products"
COPY_PATH = Path(__file__).resolve().parent / "peterman_copy.json"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(cart_router)
app.include_router(wishlist_router)
ensure_sessions_table()
ensure_cart_table()
ensure_wishlist_table()

# Only the product photo folder is public, never the data folder (it holds the database).
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def read_only_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_copy() -> dict:
    """Catalogue-voice display copy written for the site (not used for facts)."""
    if COPY_PATH.exists():
        return json.loads(COPY_PATH.read_text(encoding="utf-8"))
    return {}


def image_url(image_file_path: str) -> str:
    return "/images/" + Path(image_file_path).name


def product_summary(row: sqlite3.Row, copy: dict, stock: dict) -> dict:
    sizes = stock.get(row["product_id"], {})
    return {
        "product_id": row["product_id"],
        "name": display_name(row["name"]),
        "garment_type": row["garment_type"],
        "price": row["price"],
        "colors": json.loads(row["colors"] or "[]"),
        "description": row["description"],
        "tagline": copy.get(row["product_id"], {}).get("tagline", ""),
        "image_url": image_url(row["image_file_path"]),
        "total_in_stock": sum(sizes.values()),
        "sizes_sold_out": [s for s, q in sizes.items() if q == 0],
    }


def stock_by_product(conn: sqlite3.Connection) -> dict:
    stock: dict = {}
    for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    return stock


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[dict]:
    copy = load_copy()
    with read_only_connection() as conn:
        stock = stock_by_product(conn)
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    return [product_summary(r, copy, stock) for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    copy = load_copy()
    with read_only_connection() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = stock_by_product(conn)
    product = product_summary(row, copy, stock)
    sizes = stock.get(product_id, {})
    product["story"] = copy.get(product_id, {}).get("story", "")
    product["sizes"] = [
        {"size": s, "quantity": sizes[s]}
        for s in sorted(sizes, key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else 99)
    ]
    return product


def build_deps(user_id: int | None, viewing_product_id: str | None, is_first_message: bool) -> ShopDeps:
    """Everything Dan should know about who is chatting and which page they're on."""
    deps = ShopDeps(user_id=user_id, is_first_message=is_first_message)
    with read_only_connection() as conn:
        if user_id is not None:
            row = conn.execute(
                "SELECT first_name, last_name, name, email FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row:
                deps.first_name = row["first_name"] or row["name"].split(" ")[0]
                deps.last_name = row["last_name"]
                deps.email = row["email"]
        if viewing_product_id:
            row = conn.execute(
                "SELECT product_id, name, garment_type, colors FROM catalogue WHERE product_id = ?",
                (viewing_product_id,),
            ).fetchone()
            if row:
                deps.viewing_product = {
                    "product_id": row["product_id"],
                    "name": display_name(row["name"]),
                    "garment_type": row["garment_type"],
                    "colors": json.loads(row["colors"] or "[]"),
                }
    return deps


def full_products(product_ids: list[str]) -> list[dict]:
    """Catalogue cards for validated ids, in order, built from the database."""
    ids = valid_product_ids(product_ids)
    if not ids:
        return []
    copy = load_copy()
    with read_only_connection() as conn:
        stock = stock_by_product(conn)
        rows = {r["product_id"]: r for r in conn.execute("SELECT * FROM catalogue")}
    return [product_summary(rows[pid], copy, stock) for pid in ids if pid in rows]


def require_login(cc_session: str | None) -> int:
    user_id = current_user_id(cc_session)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Please log in to see saved chats.")
    return user_id


@app.get("/api/chat/history")
def chat_history(cc_session: str | None = Cookie(default=None)) -> dict:
    """The logged-in shopper's saved conversation, with product cards rebuilt from today's catalogue."""
    user_id = require_login(cc_session)
    messages = []
    for m in history.load_messages(user_id):
        cards = [ProductCard(**{k: p[k] for k in ProductCard.model_fields}) for p in full_products(m["product_ids"])[:6]]
        messages.append({"role": m["role"], "content": m["content"], "products": cards})
    return {"messages": messages}


@app.delete("/api/chat/history")
def clear_chat_history(cc_session: str | None = Cookie(default=None)) -> dict:
    """"Clear my chat history": delete the shopper's saved messages and Dan's memory of them."""
    user_id = require_login(cc_session)
    deleted = history.clear_messages(user_id)
    forget_user_conversations(user_id)
    return {"deleted": deleted}


class ClaimRequest(BaseModel):
    conversation_id: str = Field(max_length=64)


@app.post("/api/chat/claim")
def claim_chat(body: ClaimRequest, cc_session: str | None = Cookie(default=None)) -> dict:
    """A guest just created an account or logged in: save the chat they already had."""
    user_id = require_login(cc_session)
    return {"saved": claim_conversation(body.conversation_id, user_id)}


LOCAL_PROXIES = {"127.0.0.1", "::1"}


def shopper_address(http_request: Request) -> str:
    """The shopper's own network address, for per-shopper spam limits.

    In development every request arrives through the local Vite proxy (127.0.0.1), so the real
    address comes from the X-Forwarded-For header it adds. That header is trusted only when the
    request really came from the local proxy, so a shopper can't fake it to dodge limits.
    """
    direct = http_request.client.host if http_request.client else "unknown"
    forwarded = http_request.headers.get("x-forwarded-for", "")
    if direct in LOCAL_PROXIES and forwarded:
        return forwarded.split(",")[0].strip() or direct
    return direct


def audit_gate(conversation_id: str, user_id: int | None, message: str, stop_reason: str) -> None:
    """Audit a message that was stopped before reaching the AI (spam, bots, ended chats)."""
    audit.append(
        {
            "conversation": audit.conversation_tag(conversation_id),
            "shopper": "logged in" if user_id is not None else "guest",
            "message_chars": len(message),
            "tool_calls": [],
            "tool_call_count": 0,
            "model_requests": 0,
            "stop_reason": stop_reason,
        }
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, http_request: Request, cc_session: str | None = Cookie(default=None)
) -> ChatResponse:
    """Send a shopper's message to Handsome Dan and return his reply plus product cards."""
    user_id = current_user_id(cc_session)
    conversation_id, conv = get_conversation(request.conversation_id, user_id)
    message = remove_card_numbers(request.message.strip())

    if conv.ended or is_flagged(user_id):
        conv.ended = True
        audit_gate(conversation_id, user_id, message, "chat_already_ended")
        return ChatResponse(reply=CHAT_ENDED_MESSAGE, conversation_id=conversation_id, ended=True)

    if not message:
        raise HTTPException(status_code=400, detail="Please type a message.")

    # Spam / bot protection runs before any AI call, so floods cost nothing.
    blocked = ratelimit.check(shopper_address(http_request), conversation_id, message)
    if blocked:
        audit_gate(conversation_id, user_id, message, blocked)
        return ChatResponse(reply=ratelimit.MESSAGES[blocked], conversation_id=conversation_id)

    deps = build_deps(user_id, request.viewing_product_id, is_first_message=not conv.history)
    try:
        reply = await ask_dan(conv, message, deps, conversation_id)
    except Exception:
        logger.exception("Handsome Dan failed to answer")
        return ChatResponse(
            reply="Ruff. My brain hit a snag just now. Please try that again in a moment.",
            conversation_id=conversation_id,
        )

    if conv.ended:
        return ChatResponse(reply=CHAT_ENDED_MESSAGE, conversation_id=conversation_id, ended=True)

    # Cards are built here from the database (never from the AI's text), using only validated product ids.
    full = full_products(reply.product_ids)
    chat_cards = [ProductCard(**{k: p[k] for k in ProductCard.model_fields}) for p in full[:6]]
    picks = None
    if reply.show_on_page and full:
        picks = PagePicks(
            label=(reply.search_label or "Your search").strip()[:60],
            products=[PickProduct(**{k: p[k] for k in PickProduct.model_fields}) for p in full],
        )
    return ChatResponse(
        reply=reply.reply,
        products=chat_cards,
        picks=picks,
        signup_invite=user_id is None and deps.is_first_message and not reply.rule_violation,
        facts_checked=deps.facts_checked,
        corrected=deps.corrections > 0 and deps.facts_checked > 0,
        conversation_id=conversation_id,
    )
