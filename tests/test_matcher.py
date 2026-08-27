from calishelf.matcher import find_existing, normalize
from calishelf.models import ABSLibraryItem, BookToSync


def test_normalize_strips_case_punctuation_and_whitespace():
    assert normalize("  The Book:  A Story!  ") == "the book a story"
    assert normalize("Über den Wolken") == normalize("uber den wolken")


def test_asin_match_is_preferred_and_unambiguous():
    book = BookToSync(
        title="Some Other Title",
        authors=("Some Other Author",),
        file_path="/x.m4b",
        asin="B000ASIN1",
    )
    existing = [
        ABSLibraryItem(id="1", title="Different Title", authors=(), asin="B000ASIN1"),
        ABSLibraryItem(id="2", title="Some Other Title", authors=("Some Other Author",), asin="B000OTHER"),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"


def test_asin_match_is_case_and_whitespace_insensitive():
    book = BookToSync(
        title="Some Other Title",
        authors=("Some Other Author",),
        file_path="/x.m4b",
        asin=" b000asin1 ",
    )
    existing = [
        ABSLibraryItem(id="1", title="Different Title", authors=(), asin="B000ASIN1"),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"


def test_asin_present_but_no_asin_match_falls_back_to_title_author():
    # This is the common case for books we uploaded ourselves: Audiobookshelf
    # never gets an ASIN from our upload, even though Calibre has one.
    book = BookToSync(
        title="Dune",
        authors=("Frank Herbert",),
        file_path="/x.m4b",
        asin="B000ASIN1",
    )
    existing = [
        ABSLibraryItem(id="1", title="Dune", authors=("Frank Herbert",), asin=None),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"


def test_asin_present_conflicting_asin_on_item_blocks_title_fallback():
    # Same title/author, but the item has a *different* confirmed ASIN --
    # treat it as a different release, don't merge.
    book = BookToSync(
        title="Dune",
        authors=("Frank Herbert",),
        file_path="/x.m4b",
        asin="B000ASIN1",
    )
    existing = [
        ABSLibraryItem(id="1", title="Dune", authors=("Frank Herbert",), asin="B000OTHERASIN"),
    ]
    assert find_existing(book, existing) is None


def test_title_author_fallback_when_no_asin_on_either_side():
    book = BookToSync(
        title="The Hobbit",
        authors=("J.R.R. Tolkien",),
        file_path="/x.m4b",
        asin=None,
    )
    existing = [
        ABSLibraryItem(id="1", title="the hobbit", authors=("j.r.r. tolkien",), asin=None),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"


def test_title_author_fallback_matches_item_with_asin_when_book_has_none():
    # Covers "ASIN removed from Calibre": the book itself carries no ASIN
    # (unknown), so an item having *some* ASIN isn't a confirmed conflict --
    # title/author still decide it. Only a *disagreeing* ASIN on both sides
    # blocks the fallback (see test_asin_present_conflicting_asin_on_item_blocks_title_fallback).
    book = BookToSync(
        title="The Hobbit",
        authors=("J.R.R. Tolkien",),
        file_path="/x.m4b",
        asin=None,
    )
    existing = [
        ABSLibraryItem(id="1", title="The Hobbit", authors=("J.R.R. Tolkien",), asin="B000SOMEASIN"),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"


def test_no_match_returns_none():
    book = BookToSync(title="Unmatched Book", authors=("Nobody",), file_path="/x.m4b")
    existing = [
        ABSLibraryItem(id="1", title="Another Book", authors=("Someone Else",), asin=None),
    ]
    assert find_existing(book, existing) is None


def test_metadata_edited_in_calibre_still_matches_via_asin():
    # Title/author changed in Calibre after the book was already ASIN-matched
    # in Audiobookshelf (e.g. via ABS's own metadata match). ASIN doesn't
    # change with a title edit, so this must still match -- title/author are
    # irrelevant once ASIN agrees.
    book = BookToSync(
        title="Dune: Deluxe Edition",  # renamed in Calibre
        authors=("Frank Herbert",),
        file_path="/x.m4b",
        asin="B000ASIN1",
    )
    existing = [
        ABSLibraryItem(id="1", title="Dune", authors=("Frank Herbert",), asin="B000ASIN1"),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"


def test_metadata_edited_in_calibre_without_abs_asin_causes_reupload():
    # Known, documented limitation: if the ABS item has no ASIN yet (the
    # common case for anything only we've ever uploaded) and the title is
    # edited in Calibre afterwards, there's nothing stable left to match on
    # -- this book will look "new" and get re-uploaded under the new title.
    # Running Audiobookshelf's own metadata match after the first sync
    # avoids this by giving the ABS item a real ASIN (see the test above).
    book = BookToSync(
        title="Dune: Deluxe Edition",
        authors=("Frank Herbert",),
        file_path="/x.m4b",
        asin="B000ASIN1",
    )
    existing = [
        ABSLibraryItem(id="1", title="Dune", authors=("Frank Herbert",), asin=None),
    ]
    assert find_existing(book, existing) is None


def test_asin_removed_from_calibre_still_matches_previously_synced_item():
    # The book had an ASIN, got synced (ABS item has no ASIN, per how upload
    # works), and the ASIN identifier was later deleted in Calibre. Title and
    # author are unchanged, so this must still match.
    book = BookToSync(
        title="Dune",
        authors=("Frank Herbert",),
        file_path="/x.m4b",
        asin=None,
    )
    existing = [
        ABSLibraryItem(id="1", title="Dune", authors=("Frank Herbert",), asin=None),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"


def test_multiple_authors_order_independent():
    book = BookToSync(
        title="Good Omens",
        authors=("Neil Gaiman", "Terry Pratchett"),
        file_path="/x.m4b",
        asin=None,
    )
    existing = [
        ABSLibraryItem(
            id="1",
            title="Good Omens",
            authors=("Terry Pratchett", "Neil Gaiman"),
            asin=None,
        ),
    ]
    match = find_existing(book, existing)
    assert match is not None
    assert match.id == "1"
