"""Shopper-facing product names.

The seed catalogue's names were generated from file names, so a few have lost punctuation or
capitalization ("1 4 Zip", "Ua", "Creqneck", "Hoodie 1"). Names are tidied here on their way out
of the database (the database itself is unchanged), so the site, the bag, Handsome Dan and the
fact-checker all agree.
"""

import re

FIXES = [
    (r"\b1 4 Zip\b", "1/4 Zip"),  # quarter-zips
    (r"\bL S 2 0\b", "L/S 2.0"),  # Under Armour long-sleeve 2.0
    (r"\bUa\b", "UA"),  # Under Armour
    (r"\bMens\b", "Men's"),
    (r"\bVit\b", "VIT"),  # District's VIT line
    (r"\bCreqneck\b", "Crewneck"),  # typo
    (r"\s+1$", ""),  # stray "1" suffix ("Champion Reverse Weave Hoodie 1")
]


def display_name(name: str) -> str:
    for pattern, replacement in FIXES:
        name = re.sub(pattern, replacement, name)
    return name
