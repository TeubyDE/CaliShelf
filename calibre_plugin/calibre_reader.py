"""Reads books flagged for sync out of the current Calibre library.

Uses db.new_api (calibre.db.cache.Cache) exclusively -- no calibredb, no
direct metadata.db access. Calibre is read-only from this module's
perspective; nothing here ever writes back to the library.
"""

def get_books_to_sync(db, audiobook_column, asin_identifier_key, audio_extensions):
    """db is gui.current_db (a LibraryDatabase).

    Returns (books, errors) -- errors is a list of (book_id, message) for
    records that couldn't be read. One broken/inconsistent book record
    (e.g. a missing metadata field) must not prevent every other flagged
    book from being synced.
    """
    from calibre_plugins.calishelf.calishelf.models import BookToSync

    api = db.new_api
    books = []
    errors = []
    for book_id in api.all_book_ids():
        try:
            if api.field_for(audiobook_column, book_id) is not True:
                continue

            file_path = _find_audio_file_path(api, book_id, audio_extensions)
            if file_path is None:
                continue

            metadata = api.get_metadata(book_id)
            identifiers = api.field_for("identifiers", book_id) or {}

            books.append(
                BookToSync(
                    title=metadata.title,
                    authors=tuple(metadata.authors),
                    file_path=file_path,
                    asin=identifiers.get(asin_identifier_key) or None,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append((book_id, str(exc)))
    return books, errors


def _find_audio_file_path(api, book_id, audio_extensions):
    formats = api.formats(book_id)
    for extension in audio_extensions:
        if extension.upper() in formats or extension in formats:
            return api.format_abspath(book_id, extension)
    return None
