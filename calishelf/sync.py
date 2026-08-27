"""Orchestrates a sync run: fetch existing ABS items once, diff, upload."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .abs_client import ABSClient, ABSClientError
from .config import CaliShelfConfig
from .matcher import find_existing
from .models import ABSLibraryItem, BookToSync, SyncResult

ProgressCallback = Callable[[float, str], None]


def _noop_progress(_fraction: float, _message: str) -> None:
    pass


class SyncEngine:
    def __init__(self, config: CaliShelfConfig, client: ABSClient | None = None):
        self.config = config
        self.client = client or ABSClient(config.base_url, config.api_key)

    def run(
        self,
        books: Iterable[BookToSync],
        progress_cb: ProgressCallback = _noop_progress,
    ) -> SyncResult:
        books = list(books)
        result = SyncResult()

        progress_cb(0.0, "Fetching existing library items from Audiobookshelf...")
        existing_items = self.client.list_library_items(self.config.library_id)

        total = len(books)
        try:
            for index, book in enumerate(books, start=1):
                fraction = index / total
                if find_existing(book, existing_items):
                    result.skipped.append(book)
                    progress_cb(fraction, f"Already present, skipping: {book.title}")
                    continue

                progress_cb(fraction, f"Uploading: {book.title}")
                try:
                    self.client.upload_book(
                        self.config.library_id, self.config.folder_id, book
                    )
                    result.uploaded.append(book)
                    # So a duplicate/leftover book later in the same batch
                    # matches against what we just uploaded, not just
                    # against what existed at the start of this run.
                    existing_items.append(
                        ABSLibraryItem(
                            id="", title=book.title, authors=book.authors, asin=book.asin
                        )
                    )
                except ABSClientError as exc:
                    result.failed.append((book, str(exc)))
        finally:
            # Uploaded files don't show up as library items until Audiobookshelf
            # scans for them. This must run even if the loop above was
            # interrupted (e.g. progress_cb raising because the user aborted
            # the job) -- otherwise already-uploaded files never get scanned
            # and look "new" again on the next run, causing a duplicate
            # upload. Not routed through progress_cb: calling it again here
            # would immediately re-raise on an aborted run.
            if result.uploaded:
                try:
                    self.client.trigger_scan(self.config.library_id)
                except ABSClientError:
                    pass

        progress_cb(1.0, "Done.")
        return result
