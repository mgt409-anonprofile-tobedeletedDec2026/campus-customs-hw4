"""Remove payment card numbers that shoppers sometimes paste into chats.

Applied before a message reaches Handsome Dan or the saved chat history, so card numbers
are never sent to the AI provider or stored.
"""

import re

# 13-19 digits, optionally separated by spaces or dashes (the shape of a payment card number).
CARD_NUMBER = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def remove_card_numbers(text: str) -> str:
    return CARD_NUMBER.sub("[card number removed]", text)
