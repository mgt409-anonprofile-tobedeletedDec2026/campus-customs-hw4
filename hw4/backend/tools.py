"""Tools Handsome Dan can call. All read-only; none can see other customers' data."""

import json
import re
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic_ai import ModelRetry, RunContext

from naming import display_name

from models import (
    Alternative,
    Alternatives,
    BagLine,
    ProductDetails,
    ProductSummary,
    SearchResults,
    ShopDeps,
    SizeStock,
    StockCheck,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK = 5
SIZE_WORDS = {
    "EXTRA SMALL": "XS", "X SMALL": "XS", "SMALL": "S", "MEDIUM": "M", "MED": "M", "LARGE": "L",
    "EXTRA LARGE": "XL", "X LARGE": "XL", "XX LARGE": "XXL", "2XL": "XXL", "2X": "XXL",
    "EXTRA EXTRA LARGE": "XXL",
}
STOPWORDS = {"a", "an", "and", "the", "for", "with", "in", "of", "to", "me", "some", "any", "do", "you", "have", "yale"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _sizes(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    rows = sorted(rows, key=lambda r: SIZE_ORDER.index(r["size"]) if r["size"] in SIZE_ORDER else 99)
    return [SizeStock(size=r["size"], quantity=r["quantity"]) for r in rows]


def _summary(conn: sqlite3.Connection, row: sqlite3.Row) -> ProductSummary:
    sizes = _sizes(conn, row["product_id"])
    return ProductSummary(
        product_id=row["product_id"],
        name=display_name(row["name"]),
        garment_type=row["garment_type"],
        price=row["price"],
        colors=json.loads(row["colors"] or "[]"),
        total_in_stock=sum(s.quantity for s in sizes),
        sizes_sold_out=[s.size for s in sizes if s.quantity == 0],
    )


def _get_row(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id.strip(),)).fetchone()
    if row is None:
        raise ModelRetry(f"No product with id '{product_id}'. Use search_products to find valid product_id values.")
    return row


# A shopper's word -> catalogue words that mean the same thing.
SYNONYMS = {
    "hoodie": {"hoodie", "hood", "hooded"},
    "sweatshirt": {"sweatshirt", "crewneck", "hoodie", "hooded"},
    "sweater": {"sweater", "sweatshirt", "crewneck", "fleece"},
    "crew": {"crew", "crewneck"},
    "tee": {"tee", "shirt"},
    "tshirt": {"shirt"},
    "jacket": {"jacket", "fleece", "bomber"},
    "zip": {"zip", "quarter"},
    "grey": {"gray"},
    "pink": {"pink", "coral", "rose"},
    "beige": {"cream", "ivory"},
}


def _normalize(word: str) -> str:
    """Lowercase and drop a plural "s" so "hoodies" matches "hoodie"."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _tokens(text: str) -> set[str]:
    return {_normalize(w) for w in re.findall(r"[a-z0-9]+", text.lower())}


def search_products(
    ctx: RunContext[ShopDeps],
    query: str = "",
    max_price: float | None = None,
    sort_by: Literal["relevance", "price_low_to_high", "price_high_to_low"] = "relevance",
    limit: int = 6,
) -> SearchResults:
    """Find products by keywords: garment type, sport, residential college, school, color or family
    member (e.g. "navy hoodie", "Saybrook", "hockey", "dad", "quarter zip"). Whole words only, so
    "dog" does not match "bulldog". Products must match every keyword. Leave query empty to browse.
    Use sort_by="price_low_to_high" for "cheapest" questions and "price_high_to_low" for "most
    expensive" or "nicest". Every match is considered before sorting and limiting."""
    terms = [_normalize(w) for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS]
    limit = max(1, min(limit, 15))
    with _connect() as conn:
        matches = []
        for row in conn.execute("SELECT * FROM catalogue"):
            if max_price is not None and row["price"] > max_price:
                continue
            name_tokens = _tokens(row["name"])
            all_tokens = name_tokens | _tokens(
                " ".join([row["garment_type"], row["description"], row["colors"], row["search_tags"]])
            )
            score = 0
            for term in terms:
                options = SYNONYMS.get(term, {term})
                if not options & all_tokens:
                    break
                score += 3 if options & name_tokens else 1
            else:
                matches.append((score, row))

        if sort_by == "price_low_to_high":
            matches.sort(key=lambda m: (m[1]["price"], -m[0], m[1]["name"]))
        elif sort_by == "price_high_to_low":
            matches.sort(key=lambda m: (-m[1]["price"], -m[0], m[1]["name"]))
        else:
            matches.sort(key=lambda m: (-m[0], m[1]["name"]))

        return SearchResults(
            query=query,
            sort_by=sort_by,
            total_matches=len(matches),
            products=[_summary(conn, row) for _, row in matches[:limit]],
        )


def get_product_details(ctx: RunContext[ShopDeps], product_id: str) -> ProductDetails:
    """Full facts for ONE product: description, price, design colors and stock for every size.
    Use for description questions, price questions about a named product, and "which sizes are left?"."""
    with _connect() as conn:
        row = _get_row(conn, product_id)
        summary = _summary(conn, row)
        return ProductDetails(**summary.model_dump(), description=row["description"], sizes=_sizes(conn, row["product_id"]))


def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str) -> StockCheck:
    """Exact stock count and status for ONE product in ONE size. Use for "do you have X in medium?"
    Accepts XS, S, M, L, XL, XXL or words like "medium", "extra large", "2XL"."""
    size = SIZE_WORDS.get(re.sub(r"[\s-]+", " ", size.strip().upper()), size.strip().upper())
    with _connect() as conn:
        row = _get_row(conn, product_id)
        stock = conn.execute(
            "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (row["product_id"], size)
        ).fetchone()
    if stock is None:
        raise ModelRetry(f"'{size}' isn't a size we carry. Sizes are {', '.join(SIZE_ORDER)}.")
    qty = stock["quantity"]
    status = "sold out" if qty == 0 else "low stock" if qty <= LOW_STOCK else "in stock"
    return StockCheck(product_id=row["product_id"], name=display_name(row["name"]), size=size, quantity=qty, status=status)


THEME_WORDS = {
    # residential colleges and schools
    "benjamin", "franklin", "berkeley", "branford", "davenport", "grace", "hopper", "jonathan", "edwards",
    "morse", "pierson", "saybrook", "timothy", "dwight", "trumbull", "silliman", "stiles", "murray",
    "law", "medicine", "nursing", "management", "art", "architecture", "music", "divinity", "engineering",
    "forest", "health",
    # sports and themes
    "baseball", "basketball", "crew", "diving", "fencing", "field", "football", "golf", "hockey", "lacrosse",
    "sailing", "soccer", "squash", "swimming", "tennis", "track", "volleyball", "bulldog", "vintage",
    "harvard", "bowl", "boola",
    # family
    "mom", "dad", "aunt", "uncle", "grandma", "grandpa", "brother", "cousin",
}


def _theme_words(name: str) -> set[str]:
    """Exact whole words only, so "Brooks Brothers" doesn't count as the "brother" family theme."""
    return set(re.findall(r"[a-z]+", name.lower())) & THEME_WORDS


def _family(row: sqlite3.Row) -> str:
    """Rough garment family, matching the Products page filter."""
    t = f"{row['garment_type']} {row['name']}".lower()
    if "quarter-zip" in t or "1 4 zip" in t:
        return "quarter-zip"
    if "jacket" in t or "fleece" in t:
        return "outerwear"
    if "hood" in t:
        return "hoodie"
    if "crew" in t or "sweatshirt" in t or "mockneck" in t:
        return "crewneck"
    if "long-sleeve" in t or "performance" in t:
        return "performance"
    return "tee"


def find_alternatives(ctx: RunContext[ShopDeps], product_id: str, size: str) -> Alternatives:
    """Use when a shopper wants a product in a size that is sold out (or low). Returns the item's
    neighboring sizes that are in stock and up to 4 similar products (same kind of garment, same college,
    sport or theme, similar color and price) that ARE in stock in the requested size."""
    size = SIZE_WORDS.get(re.sub(r"[\s-]+", " ", size.strip().upper()), size.strip().upper())
    if size not in SIZE_ORDER:
        raise ModelRetry(f"'{size}' isn't a size we carry. Sizes are {', '.join(SIZE_ORDER)}.")
    with _connect() as conn:
        row = _get_row(conn, product_id)
        sizes = {s.size: s.quantity for s in _sizes(conn, row["product_id"])}
        qty = sizes.get(size, 0)
        i = SIZE_ORDER.index(size)
        adjacent = [
            SizeStock(size=s, quantity=sizes[s])
            for s in SIZE_ORDER[max(0, i - 1): i + 2]
            if s != size and sizes.get(s, 0) > 0
        ]

        family = _family(row)
        themes = _theme_words(row["name"])
        main_color = (json.loads(row["colors"] or "[]") or [""])[0]
        candidates = []
        for other in conn.execute(
            "SELECT k.*, i.quantity AS qty FROM catalogue k JOIN inventory i ON i.product_id = k.product_id "
            "WHERE i.size = ? AND i.quantity > 0 AND k.product_id != ?",
            (size, row["product_id"]),
        ):
            reasons, score = [], 0
            if _family(other) == family:
                score += 5
                reasons.append(f"also a {other['garment_type']}")
            shared = _theme_words(other["name"]) & themes
            if shared:
                score += 8 * len(shared)  # college/sport/family loyalty matters most
                reasons.append("same " + "/".join(sorted(w.title() for w in shared)) + " theme")
            other_color = (json.loads(other["colors"] or "[]") or [""])[0]
            if main_color and other_color == main_color:
                score += 2
                reasons.append(other_color)
            if abs(other["price"] - row["price"]) <= 15:
                score += 1
            if score >= 5:
                candidates.append((score, other, reasons))
        candidates.sort(key=lambda c: (-c[0], abs(c[1]["price"] - row["price"]), c[1]["name"]))

    status = "sold out" if qty == 0 else "low stock" if qty <= LOW_STOCK else "in stock"
    return Alternatives(
        product_id=row["product_id"],
        name=display_name(row["name"]),
        requested_size=size,
        requested_quantity=qty,
        requested_status=status,
        adjacent_sizes_in_stock=adjacent,
        similar_in_size=[
            Alternative(
                product_id=o["product_id"],
                name=display_name(o["name"]),
                garment_type=o["garment_type"],
                price=o["price"],
                colors=json.loads(o["colors"] or "[]"),
                quantity_in_size=o["qty"],
                why_similar=", ".join(reasons),
            )
            for _, o, reasons in candidates[:4]
        ],
    )


def get_my_bag(ctx: RunContext[ShopDeps]) -> list[BagLine] | str:
    """The logged-in shopper's own bag (never anyone else's). Use it to suggest matching items."""
    if ctx.deps.user_id is None:
        return "The shopper is not logged in, so there is no bag to show."
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'cart_items'"
        ).fetchone()
        if not exists:
            return []
        rows = conn.execute(
            """
            SELECT c.product_id, k.name, c.size, c.quantity, k.price
            FROM cart_items c JOIN catalogue k ON k.product_id = c.product_id
            WHERE c.user_id = ?
            ORDER BY c.added_at
            """,
            (ctx.deps.user_id,),
        ).fetchall()
    return [BagLine(**{**dict(r), "name": display_name(r["name"])}) for r in rows] or "The shopper's bag is empty."


def get_my_wishlist(ctx: RunContext[ShopDeps]) -> list[ProductSummary] | str:
    """Products the logged-in shopper saved to their own wishlist (never anyone else's), newest first.
    Use it to personalize suggestions, e.g. find items similar to a saved hoodie."""
    if ctx.deps.user_id is None:
        return "The shopper is not logged in, so there is no wishlist."
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'wishlist_items'"
        ).fetchone()
        if not exists:
            return "The shopper's wishlist is empty."
        rows = conn.execute(
            """
            SELECT k.* FROM wishlist_items w JOIN catalogue k ON k.product_id = w.product_id
            WHERE w.user_id = ? ORDER BY w.added_at DESC, w.id DESC LIMIT 20
            """,
            (ctx.deps.user_id,),
        ).fetchall()
        return [_summary(conn, r) for r in rows] or "The shopper's wishlist is empty."


ALL_TOOLS = [search_products, get_product_details, check_stock, find_alternatives, get_my_bag, get_my_wishlist]


def valid_product_ids(ids: list[str]) -> list[str]:
    """Keep only ids that exist in the catalogue, in order, without duplicates."""
    if not ids:
        return []
    with _connect() as conn:
        known = {r["product_id"] for r in conn.execute("SELECT product_id FROM catalogue")}
    seen, result = set(), []
    for pid in ids:
        if pid in known and pid not in seen:
            seen.add(pid)
            result.append(pid)
    return result
