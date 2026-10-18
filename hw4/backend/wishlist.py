"""Wishlist: products a logged-in shopper saved for later (separate from the bag).

Items live in a `wishlist_items` table (created on startup if missing).
"""

from fastapi import APIRouter, Cookie, HTTPException

from auth import connect, current_user_id

MAX_ITEMS = 100

router = APIRouter(prefix="/api/wishlist")


def ensure_wishlist_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wishlist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                added_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES catalogue(product_id),
                UNIQUE (user_id, product_id)
            )
            """
        )


def require_user(token: str | None) -> int:
    user_id = current_user_id(token)
    if user_id is None:
        raise HTTPException(401, "Please log in to use your wishlist.")
    return user_id


def wishlist_ids(user_id: int) -> list[str]:
    """Saved product ids, newest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT product_id FROM wishlist_items WHERE user_id = ? ORDER BY added_at DESC, id DESC", (user_id,)
        ).fetchall()
    return [r["product_id"] for r in rows]


@router.get("")
def get_wishlist(cc_session: str | None = Cookie(default=None)) -> dict:
    return {"product_ids": wishlist_ids(require_user(cc_session))}


@router.post("/{product_id}")
def add_to_wishlist(product_id: str, cc_session: str | None = Cookie(default=None)) -> dict:
    user_id = require_user(cc_session)
    with connect() as conn:
        if conn.execute("SELECT 1 FROM catalogue WHERE product_id = ?", (product_id,)).fetchone() is None:
            raise HTTPException(404, "We don't carry that item.")
        count = conn.execute("SELECT COUNT(*) FROM wishlist_items WHERE user_id = ?", (user_id,)).fetchone()[0]
        if count >= MAX_ITEMS:
            raise HTTPException(409, f"Your wishlist is full ({MAX_ITEMS} items).")
        conn.execute(
            "INSERT OR IGNORE INTO wishlist_items (user_id, product_id) VALUES (?, ?)", (user_id, product_id)
        )
    return {"product_ids": wishlist_ids(user_id)}


@router.delete("/{product_id}")
def remove_from_wishlist(product_id: str, cc_session: str | None = Cookie(default=None)) -> dict:
    user_id = require_user(cc_session)
    with connect() as conn:
        conn.execute("DELETE FROM wishlist_items WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    return {"product_ids": wishlist_ids(user_id)}
