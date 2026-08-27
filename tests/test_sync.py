import pytest

from calishelf.abs_client import ABSClientError
from calishelf.config import CaliShelfConfig
from calishelf.models import ABSLibraryItem, BookToSync
from calishelf.sync import SyncEngine


class FakeABSClient:
    def __init__(self, existing_items, fail_titles=frozenset(), fail_scan=False):
        self.existing_items = existing_items
        self.fail_titles = fail_titles
        self.fail_scan = fail_scan
        self.uploaded = []
        self.scan_triggered_for = []

    def list_library_items(self, library_id):
        return self.existing_items

    def upload_book(self, library_id, folder_id, book):
        if book.title in self.fail_titles:
            raise ABSClientError(f"boom: {book.title}")
        self.uploaded.append(book)

    def trigger_scan(self, library_id):
        if self.fail_scan:
            raise ABSClientError("scan boom")
        self.scan_triggered_for.append(library_id)


def _config():
    return CaliShelfConfig(
        base_url="https://abs.example.com",
        api_key="secret",
        library_id="lib1",
        folder_id="folder1",
    )


def test_uploads_only_books_not_already_present():
    already_present = ABSLibraryItem(id="1", title="Already There", authors=("A",), asin="ASIN1")
    client = FakeABSClient(existing_items=[already_present])
    engine = SyncEngine(_config(), client=client)

    books = [
        BookToSync(title="Already There", authors=("A",), file_path="/a.m4b", asin="ASIN1"),
        BookToSync(title="New Book", authors=("B",), file_path="/b.m4b", asin="ASIN2"),
    ]
    result = engine.run(books)

    assert [b.title for b in result.uploaded] == ["New Book"]
    assert [b.title for b in result.skipped] == ["Already There"]
    assert result.failed == []
    assert [b.title for b in client.uploaded] == ["New Book"]
    assert client.scan_triggered_for == ["lib1"]


def test_failed_upload_is_recorded_not_raised():
    client = FakeABSClient(existing_items=[], fail_titles={"Broken Book"})
    engine = SyncEngine(_config(), client=client)

    books = [BookToSync(title="Broken Book", authors=("A",), file_path="/a.m4b", asin="ASIN1")]
    result = engine.run(books)

    assert result.uploaded == []
    assert result.skipped == []
    assert len(result.failed) == 1
    assert result.failed[0][0].title == "Broken Book"
    assert "boom" in result.failed[0][1]
    assert client.scan_triggered_for == []


def test_no_scan_triggered_when_everything_was_skipped():
    already_present = ABSLibraryItem(id="1", title="Book", authors=("A",), asin="ASIN1")
    client = FakeABSClient(existing_items=[already_present])
    engine = SyncEngine(_config(), client=client)

    books = [BookToSync(title="Book", authors=("A",), file_path="/a.m4b", asin="ASIN1")]
    engine.run(books)

    assert client.scan_triggered_for == []


def test_scan_failure_does_not_affect_upload_result():
    client = FakeABSClient(existing_items=[], fail_scan=True)
    engine = SyncEngine(_config(), client=client)

    books = [BookToSync(title="New Book", authors=("A",), file_path="/a.m4b", asin="ASIN1")]
    result = engine.run(books)

    assert [b.title for b in result.uploaded] == ["New Book"]
    assert result.failed == []


def test_progress_callback_reports_start_and_end():
    client = FakeABSClient(existing_items=[])
    engine = SyncEngine(_config(), client=client)
    messages = []

    engine.run(
        [BookToSync(title="Book", authors=("A",), file_path="/a.m4b", asin="ASIN1")],
        progress_cb=lambda fraction, message: messages.append((fraction, message)),
    )

    assert messages[0][0] == 0.0
    assert messages[-1] == (1.0, "Done.")


def test_empty_book_list_does_not_crash():
    client = FakeABSClient(existing_items=[])
    engine = SyncEngine(_config(), client=client)
    result = engine.run([])
    assert result.uploaded == result.skipped == result.failed == []


def test_mixed_run_keeps_each_book_independent():
    # One already present, one upload fails, one uploads fine -- a failure
    # or a skip for one book must never affect how the others are handled.
    already_present = ABSLibraryItem(id="1", title="Already There", authors=("A",), asin=None)
    client = FakeABSClient(existing_items=[already_present], fail_titles={"Broken Book"})
    engine = SyncEngine(_config(), client=client)

    books = [
        BookToSync(title="Already There", authors=("A",), file_path="/a.m4b", asin=None),
        BookToSync(title="Broken Book", authors=("B",), file_path="/b.m4b", asin=None),
        BookToSync(title="Good Book", authors=("C",), file_path="/c.m4b", asin=None),
    ]
    result = engine.run(books)

    assert [b.title for b in result.skipped] == ["Already There"]
    assert [b.title for b in result.uploaded] == ["Good Book"]
    assert [b.title for b, _ in result.failed] == ["Broken Book"]
    # A failed upload still counts as "something uploaded this run" overall
    # (Good Book succeeded), so a scan still gets triggered.
    assert client.scan_triggered_for == ["lib1"]


def test_duplicate_calibre_records_in_same_run_only_upload_once():
    # Two BookToSync entries that would match each other (same title/author,
    # e.g. an accidental duplicate Calibre record) -- the second must be
    # recognized as "already present" because of what the first one just
    # uploaded, not just against what existed before the run started.
    client = FakeABSClient(existing_items=[])
    engine = SyncEngine(_config(), client=client)

    books = [
        BookToSync(title="Dune", authors=("Frank Herbert",), file_path="/a.m4b", asin=None),
        BookToSync(title="Dune", authors=("Frank Herbert",), file_path="/b.m4b", asin=None),
    ]
    result = engine.run(books)

    assert len(result.uploaded) == 1
    assert len(result.skipped) == 1
    assert len(client.uploaded) == 1


def test_interrupted_run_still_triggers_scan_for_what_was_uploaded():
    # progress_cb raising mid-run (e.g. the user aborted the job) must not
    # skip the scan trigger for books that already made it to Audiobookshelf
    # -- otherwise they're invisible next run and get re-uploaded.
    client = FakeABSClient(existing_items=[])
    engine = SyncEngine(_config(), client=client)

    class Abort(Exception):
        pass

    def progress_cb(fraction, message):
        if message.startswith("Uploading: Second"):
            raise Abort()

    books = [
        BookToSync(title="First", authors=("A",), file_path="/a.m4b", asin=None),
        BookToSync(title="Second", authors=("B",), file_path="/b.m4b", asin=None),
    ]

    with pytest.raises(Abort):
        engine.run(books, progress_cb=progress_cb)

    assert [b.title for b in client.uploaded] == ["First"]
    assert client.scan_triggered_for == ["lib1"]


def test_fetching_existing_items_failure_propagates_before_any_upload():
    # If we can't even ask Audiobookshelf what's already there, we must not
    # guess or upload blind -- fail the whole run cleanly so the user can
    # just retry, rather than silently treating everything as "new".
    class BrokenListClient(FakeABSClient):
        def list_library_items(self, library_id):
            raise ABSClientError("connection reset")

    client = BrokenListClient(existing_items=[])
    engine = SyncEngine(_config(), client=client)

    with pytest.raises(ABSClientError):
        engine.run([BookToSync(title="Book", authors=("A",), file_path="/a.m4b", asin=None)])

    assert client.uploaded == []
