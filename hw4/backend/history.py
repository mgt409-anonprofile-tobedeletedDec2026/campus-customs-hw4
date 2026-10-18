"""Saved chat history for logged-in shoppers, stored in the seed `chat_messages` table.

Each exchange is two rows: the shopper's message (role "user") and Handsome Dan's reply
(role "assistant", with the product ids he showed in `products_json`). Guests' chats are
never written here unless they create an account or log in during the conversation.
"""

import json

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from auth import connect
from privacy import remove_card_numbers

MAX_RELOADED_MESSAGES = 60  # shown in the chat window
MAX_MEMORY_MESSAGES = 20  # replayed into Dan's memory


def save_message(user_id: int, role: str, content: str, product_ids: list[str] | None = None) -> None:
    content = remove_card_numbers(content)
    products_json = json.dumps([{"product_id": pid} for pid in product_ids]) if product_ids else None
    with connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content, products_json),
        )


def load_messages(user_id: int, limit: int = MAX_RELOADED_MESSAGES) -> list[dict]:
    """Most recent messages for this shopper, oldest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    messages = []
    for r in reversed(rows):
        try:
            products = json.loads(r["products_json"] or "[]")
        except json.JSONDecodeError:
            products = []
        messages.append(
            {
                "role": r["role"],
                "content": r["content"],
                "product_ids": [p["product_id"] for p in products if isinstance(p, dict) and "product_id" in p],
                "created_at": r["created_at"],
            }
        )
    return messages


def to_model_history(messages: list[dict]) -> list[ModelMessage]:
    """Rebuild Dan's memory from saved text (tool calls aren't saved, so he re-checks facts)."""
    recent = messages[-MAX_MEMORY_MESSAGES:]
    while recent and recent[0]["role"] != "user":  # memory must start with a shopper turn
        recent = recent[1:]
    history: list[ModelMessage] = []
    for m in recent:
        if m["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=m["content"])]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=m["content"])]))
    return history


def clear_messages(user_id: int) -> int:
    with connect() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
