"""Mock merchant catalog. Swap this for a real DB/API in a production build --
kept as a static list here since the catalog isn't the part being tested."""

import re

CATALOG = [
    {"name": "Running Shoes - Blue, Size 9", "price": 2499.0, "category": "footwear", "stock": 12,
     "keywords": ["running", "jogging", "sport", "athletic", "exercise", "shoe", "shoes"]},
    {"name": "Running Shoes - Black, Size 9", "price": 2699.0, "category": "footwear", "stock": 5,
     "keywords": ["running", "jogging", "sport", "athletic", "exercise", "shoe", "shoes"]},
    {"name": "Wireless Earbuds", "price": 1999.0, "category": "electronics", "stock": 20,
     "keywords": ["earphones", "audio", "music", "headphones", "earbuds"]},
    {"name": "Yoga Mat", "price": 899.0, "category": "fitness", "stock": 30,
     "keywords": ["exercise", "workout", "stretching", "yoga"]},
    {"name": "Cotton Hoodie - Blue, Size M", "price": 1299.0, "category": "apparel", "stock": 8,
     "keywords": ["sweater", "warm", "winter", "hoodie", "jacket"]},
    {"name": "Cotton Hoodie - Blue, Size L", "price": 1299.0, "category": "apparel", "stock": 3,
     "keywords": ["sweater", "warm", "winter", "hoodie", "jacket"]},
    {"name": "Smart Water Bottle", "price": 1499.0, "category": "fitness", "stock": 15,
     "keywords": ["hydration", "bottle", "water"]},
    {"name": "Bluetooth Speaker", "price": 3499.0, "category": "electronics", "stock": 0,
     "keywords": ["audio", "music", "sound", "speaker"]},  # out of stock, for testing
]


def search_catalog(query: str, category: str | None = None):
    """Keyword-overlap search over BOTH the product name and each item's
    explicit synonym list. Deliberately does NOT fall back to matching
    every item in a broad LLM-guessed category (e.g. 'electronics') --
    that approach caused false positives, matching 'laptop' to Wireless
    Earbuds just because both are tagged electronics. Explicit synonyms
    per item are more precise: 'jogging' correctly finds Running Shoes,
    but 'laptop' correctly finds nothing, since no item claims that
    synonym. The category param is accepted for API compatibility /
    future use but is not used for matching here.
    """
    STOPWORDS = {"i", "want", "a", "an", "the", "for", "to", "buy", "please", "looking"}
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS]

    results = []
    for item in CATALOG:
        name_lower = item["name"].lower()
        searchable = name_lower + " " + " ".join(item.get("keywords", []))
        if any(w in searchable for w in words):
            results.append(item)
    return results


def get_item(name: str):
    for item in CATALOG:
        if item["name"] == name:
            return item
    return None