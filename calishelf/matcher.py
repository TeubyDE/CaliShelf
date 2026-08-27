"""Matching logic: is a book already present in Audiobookshelf?

Priority order:
1. ASIN match (preferred, unambiguous).
2. Normalized title + author fallback -- tried whenever ASIN matching
   doesn't resolve it, not just when ASIN is absent on both sides. In
   practice, items we upload ourselves never get an ASIN in Audiobookshelf
   (ABS only fills it in via its own metadata-match feature) even when the
   Calibre side has one, so skipping the fallback whenever the Calibre book
   has an ASIN would mean re-uploading (never matching) almost everything
   we ourselves synced.
"""

from __future__ import annotations

import re
import unicodedata

from .models import ABSLibraryItem, BookToSync

_PUNCT_WHITESPACE_RE = re.compile(r"[^\w]+")


def normalize(text: str) -> str:
    """Lowercase, strip accents, punctuation and collapse whitespace."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _PUNCT_WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _normalize_asin(asin: str) -> str:
    return asin.strip().upper()


def _normalized_authors(authors: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(normalize(a) for a in authors))


def find_existing(
    book: BookToSync, existing_items: list[ABSLibraryItem]
) -> ABSLibraryItem | None:
    book_asin = _normalize_asin(book.asin) if book.asin else None
    if book_asin:
        for item in existing_items:
            if item.asin and _normalize_asin(item.asin) == book_asin:
                return item

    book_title = normalize(book.title)
    book_authors = _normalized_authors(book.authors)
    for item in existing_items:
        item_asin = _normalize_asin(item.asin) if item.asin else None
        if book_asin and item_asin and item_asin != book_asin:
            # Both sides have a confirmed ASIN and they disagree -- this is
            # a different release (e.g. a different edition/narration),
            # don't let a coincidental title/author match merge it with our
            # book. If either side's ASIN is simply unknown (e.g. removed
            # from Calibre, or ABS hasn't been metadata-matched), that's not
            # a conflict -- fall through to the title/author comparison.
            continue
        if normalize(item.title) == book_title and _normalized_authors(item.authors) == book_authors:
            return item
    return None
