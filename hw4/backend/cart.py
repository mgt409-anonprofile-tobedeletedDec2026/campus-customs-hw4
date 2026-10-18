"""Shopping bag for logged-in customers.

Items live in a `cart_items` table (created on startup if missing). Adding to
the bag never changes inventory; checkout is not built yet.
"""

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

from auth import connect, current_user_id
from naming import display_name

MAX_PER_LINE = 10

router = APIRouter(prefix="/api/cart")


def ensure_cart_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                size TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                added_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES catalogue(product_id),
                UNIQUE (user_id, product_id, size)
            )
            """
        )


def require_user(token: str | None) -> int:
    user_id = current_user_id(token)
    if user_id is None:
        raise HTTPException(401, "Please log in to use your bag.")
    return user_id


def stock_for(conn, product_id: str, size: str) -> int | None:
    row = conn.execute(
        "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (product_id, size)
    ).fetchone()
    return None if row is None else row["quantity"]


def bag_contents(conn, user_id: int) -> dict:
    rows = conn.execute(
        """
        SELECT c.id, c.product_id, c.size, c.quantity, k.name, k.price, k.image_file_path,
               COALESCE(i.quantity, 0) AS in_stock
        FROM cart_items c
        JOIN catalogue k ON k.product_id = c.product_id
        LEFT JOIN inventory i ON i.product_id = c.product_id AND i.size = c.size
        WHERE c.user_id = ?
        ORDER BY c.added_at, c.id
        """,
        (user_id,),
    ).fetchall()
    items = [
        {
            "id": r["id"],
            "product_id": r["product_id"],
            "name": display_name(r["name"]),
            "size": r["size"],
            "quantity": r["quantity"],
            "price": r["price"],
            "line_total": round(r["price"] * r["quantity"], 2),
            "in_stock": r["in_stock"],
            "image_url": "/images/" + r["image_file_path"].split("/")[-1],
        }
        for r in rows
    ]
    return {
        "items": items,
        "count": sum(i["quantity"] for i in items),
        "subtotal": round(sum(i["line_total"] for i in items), 2),
    }


class AddRequest(BaseModel):
    product_id: str
    size: str
    quantity: int = 1


class UpdateRequest(BaseModel):
    quantity: int


@router.get("")
def get_bag(cc_session: str | None = Cookie(default=None)) -> dict:
    user_id = require_user(cc_session)
    with connect() as conn:
        return bag_contents(conn, user_id)


@router.post("")
def add_to_bag(body: AddRequest, cc_session: str | None = Cookie(default=None)) -> dict:
    user_id = require_user(cc_session)
    if body.quantity < 1:
        raise HTTPException(400, "Quantity must be at least 1.")
    with connect() as conn:
        stock = stock_for(conn, body.product_id, body.size)
        if stock is None:
            raise HTTPException(404, "We don't carry that item in that size.")
        existing = conn.execute(
            "SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ? AND size = ?",
            (user_id, body.product_id, body.size),
        ).fetchone()
        new_qty = body.quantity + (existing["quantity"] if existing else 0)
        limit = min(stock, MAX_PER_LINE)
        if stock == 0:
            raise HTTPException(409, f"Size {body.size} is sold out.")
        if new_qty > limit:
            raise HTTPException(409, f"Only {limit} available in size {body.size}.")
        if existing:
            conn.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))
        else:
            conn.execute(
                "INSERT INTO cart_items (user_id, product_id, size, quantity) VALUES (?, ?, ?, ?)",
                (user_id, body.product_id, body.size, new_qty),
            )
        return bag_contents(conn, user_id)


@router.put("/{item_id}")
def update_item(item_id: int, body: UpdateRequest, cc_session: str | None = Cookie(default=None)) -> dict:
    user_id = require_user(cc_session)
    with connect() as conn:
        item = conn.execute(
            "SELECT product_id, size FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user_id)
        ).fetchone()
        if item is None:
            raise HTTPException(404, "That item isn't in your bag.")
        if body.quantity < 1:
            conn.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
        else:
            limit = min(stock_for(conn, item["product_id"], item["size"]) or 0, MAX_PER_LINE)
            if body.quantity > limit:
                raise HTTPException(409, f"Only {limit} available in size {item['size']}.")
            conn.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (body.quantity, item_id))
        return bag_contents(conn, user_id)


@router.delete("/{item_id}")
def remove_item(item_id: int, cc_session: str | None = Cookie(default=None)) -> dict:
    user_id = require_user(cc_session)
    with connect() as conn:
        conn.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        return bag_contents(conn, user_id)
