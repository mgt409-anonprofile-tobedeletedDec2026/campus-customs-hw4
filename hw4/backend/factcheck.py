"""Fact-checker for Handsome Dan's replies.

Before a reply reaches the shopper, every price, stock count, sold-out / in-stock claim and color
Dan mentions is checked against the database. Problems are returned as plain sentences; agent.py
sends them back to Dan (ModelRetry) so he corrects the reply before it goes out.
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from naming import display_name

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"

SIZE_WORDS = [  # longest first so "extra large" wins over "large"
    ("extra extra large", "XXL"), ("extra small", "XS"), ("extra large", "XL"), ("x-large", "XL"),
    ("xx-large", "XXL"), ("2xl", "XXL"), ("xxl", "XXL"), ("xl", "XL"), ("xs", "XS"),
    ("smalls", "S"), ("small", "S"), ("mediums", "M"), ("medium", "M"), ("larges", "L"), ("large", "L"),
]
LETTER_SIZES = {"S", "M", "L"}  # only counted when written as a capital letter on its own
COLOR_WORDS = [
    "navy", "gray", "grey", "white", "black", "red", "green", "yellow", "gold", "blue", "cream", "ivory",
    "coral", "pink", "charcoal", "orange", "purple", "brown", "maroon", "beige", "tan", "crimson", "silver",
]
SPIRIT_PHRASES = ["yale blue", "bulldog blue", "boola"]  # not claims about a garment


@dataclass
class Catalogue:
    names: dict[str, str] = field(default_factory=dict)  # lowercased name -> product_id
    price: dict[str, float] = field(default_factory=dict)
    colors: dict[str, list[str]] = field(default_factory=dict)
    stock: dict[str, dict[str, int]] = field(default_factory=dict)


def load_catalogue() -> Catalogue:
    cat = Catalogue()
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        for pid, name, price, colors in conn.execute("SELECT product_id, name, price, colors FROM catalogue"):
            cat.names[name.lower()] = pid
            cat.names[display_name(name).lower()] = pid  # "1/4 Zip" as shown to shoppers
            cat.price[pid] = price
            cat.colors[pid] = [c.lower() for c in json.loads(colors or "[]")]
        for pid, size, qty in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            cat.stock.setdefault(pid, {})[size] = qty
    finally:
        conn.close()
    return cat


def _walk_numbers(obj, prices: set[float], quantities: set[int]) -> None:
    """Collect every price and stock count that the tools actually returned."""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"price", "subtotal", "line_total"} and isinstance(value, (int, float)):
                prices.add(round(float(value), 2))
            elif key in {"quantity", "quantity_in_size", "requested_quantity", "total_in_stock", "total_matches"} and isinstance(value, int):
                quantities.add(value)
            else:
                _walk_numbers(value, prices, quantities)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _walk_numbers(item, prices, quantities)


def _clauses(text: str) -> list[str]:
    """Split into small pieces so 'M is sold out, but 15 larges are left' is checked part by part."""
    return [c.strip() for c in re.split(r"[.!?;:\n]|,|\bbut\b|\bwhile\b|\bthough\b|—|–", text) if c.strip()]


def _sizes_in(clause: str) -> set[str]:
    found, lowered = set(), clause.lower()
    for word, size in SIZE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            found.add(size)
            lowered = re.sub(rf"\b{re.escape(word)}\b", " ", lowered)
    for letter in LETTER_SIZES:
        if re.search(rf"(?<![\w$']){letter}(?![\w'])", clause):
            found.add(letter)
    return found


def _products_in(clause: str, cat: Catalogue) -> list[str]:
    lowered = clause.lower()
    return [pid for name, pid in cat.names.items() if name in lowered]


def check_reply(
    reply: str,
    *,
    user_message: str,
    tool_results: list,
    product_ids: list[str],
    viewing_product_id: str | None = None,
    cat: Catalogue | None = None,
) -> tuple[list[str], int]:
    """Return (problems, number_of_claims_checked)."""
    cat = cat or load_catalogue()
    problems: list[str] = []
    claims = 0

    tool_prices: set[float] = set()
    tool_quantities: set[int] = set()
    _walk_numbers(tool_results, tool_prices, tool_quantities)

    mentioned = set(product_ids) | set(_products_in(reply, cat))
    if viewing_product_id:
        mentioned.add(viewing_product_id)
    allowed_prices = tool_prices | {cat.price[p] for p in mentioned if p in cat.price}
    allowed_prices |= {round(float(n), 2) for n in re.findall(r"\$?\s?(\d+(?:\.\d{1,2})?)", user_message)}
    allowed_quantities = tool_quantities | {q for p in mentioned for q in cat.stock.get(p, {}).values()}

    # 1. Prices
    for amount in re.findall(r"\$\s?(\d+(?:\.\d{1,2})?)", reply):
        claims += 1
        value = round(float(amount), 2)
        if not any(abs(value - p) < 0.01 for p in allowed_prices):
            real = sorted({f"${cat.price[p]:.0f}" for p in mentioned if p in cat.price})
            problems.append(
                f"You said ${amount}, but no product you discussed costs that"
                + (f" (their real prices: {', '.join(real)})" if real else "")
                + ". Quote prices exactly as your tools return them."
            )

    # 2. Stock counts ("15 left", "only 3", "12 in stock")
    for match in re.finditer(r"\b(?:only\s+)?(\d+)\s+(?:\w+\s+){0,2}?(?:left|in stock|available|remaining)\b|\bonly\s+(\d+)\b", reply, re.I):
        number = int(match.group(1) or match.group(2))
        claims += 1
        if number not in allowed_quantities:
            problems.append(
                f"You said '{match.group(0)}', but no tool returned a stock count of {number}. "
                "Use check_stock or get_product_details and quote the exact quantity."
            )

    # 3. Sold-out / in-stock claims for a specific size of a specific product
    for clause in _clauses(reply):
        lowered = clause.lower()
        says_out = "sold out" in lowered or "out of stock" in lowered
        says_in = bool(re.search(r"\b(in stock|available|we have|there are|we've got)\b", lowered)) and not says_out
        if not (says_out or says_in):
            continue
        sizes = _sizes_in(clause)
        if not sizes:
            continue
        named = _products_in(clause, cat)
        if len(named) == 1:
            pid = named[0]
        elif not named and viewing_product_id:
            pid = viewing_product_id
        elif not named and len(product_ids) == 1:
            pid = product_ids[0]
        else:
            continue  # can't tell which product the clause is about
        for size in sizes:
            qty = cat.stock.get(pid, {}).get(size)
            if qty is None:
                continue
            claims += 1
            if says_out and qty > 0:
                problems.append(f"You said size {size} is sold out, but the database shows {qty} in stock.")
            if says_in and qty == 0:
                problems.append(f"You implied size {size} is available, but it is sold out (0 in stock).")

    # 4. Colors attributed to a named product
    asked = user_message.lower()
    for clause in _clauses(reply):
        named = _products_in(clause, cat)
        if len(named) != 1:
            continue
        lowered = clause.lower()
        for phrase in SPIRIT_PHRASES:
            lowered = lowered.replace(phrase, " ")
        for name in cat.names:  # colors inside a product's own name aren't claims
            lowered = lowered.replace(name, " ")
        product_colors = " ".join(cat.colors.get(named[0], [])).replace("grey", "gray")
        if not product_colors:
            continue
        for color in COLOR_WORDS:
            if not re.search(rf"\b{color}\b", lowered):
                continue
            claims += 1
            check = "gray" if color == "grey" else color
            if check in product_colors or check in asked:
                continue
            problems.append(
                f"You described a product as {color}, but its catalogue colors are: {product_colors}. "
                "Use the exact colors from your tools."
            )

    return problems, claims
