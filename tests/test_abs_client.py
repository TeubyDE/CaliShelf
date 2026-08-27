import json
from unittest.mock import MagicMock, patch

import pytest

from calishelf.abs_client import ABSClient, ABSClientError, _build_multipart_body
from calishelf.models import BookToSync


def _fake_response(payload: bytes):
    response = MagicMock()
    response.read.return_value = payload
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_build_multipart_body_contains_fields_and_file(tmp_path):
    audio_file = tmp_path / "book.m4b"
    audio_file.write_bytes(b"fake-audio-bytes")

    body = _build_multipart_body(
        "BOUNDARY123",
        {"library": "lib1", "folder": "folder1", "title": "My Book", "author": "Jane Doe"},
        str(audio_file),
    )

    assert b"--BOUNDARY123" in body
    assert b'name="library"' in body
    assert b"lib1" in body
    assert b'name="0"; filename="book.m4b"' in body
    assert b"fake-audio-bytes" in body
    assert body.endswith(b"--BOUNDARY123--\r\n")


def test_build_multipart_body_sanitizes_crlf_and_quotes_in_filename(tmp_path):
    # CR/LF and '"' are legal in Unix filenames; a filename containing them
    # must not be able to inject an extra header line or break out of the
    # filename="..." attribute.
    audio_file = tmp_path / 'evil"\r\nX-Injected: yes.m4b'
    audio_file.write_bytes(b"fake-audio-bytes")

    body = _build_multipart_body(
        "BOUNDARY123",
        {"library": "lib1", "folder": "folder1", "title": "Book", "author": "Author"},
        str(audio_file),
    )

    # The malicious text may still appear as literal filename content, but
    # it must not land on its own header line (no injected CRLF before it).
    assert b"\r\nX-Injected" not in body
    assert b'filename="evil\'X-Injected: yes.m4b"' in body


def test_sanitize_header_value_strips_crlf_and_quotes():
    from calishelf.abs_client import _sanitize_header_value

    assert _sanitize_header_value('evil"\r\nX-Injected: yes') == "evil'X-Injected: yes"


def test_build_multipart_body_strips_crlf_from_field_values(tmp_path):
    # title/author/library/folder come from Calibre metadata (or config) and
    # go straight into the multipart body -- an embedded CR/LF must not be
    # able to inject an extra part/header, same as for the filename.
    audio_file = tmp_path / "book.m4b"
    audio_file.write_bytes(b"fake-audio-bytes")

    body = _build_multipart_body(
        "BOUNDARY123",
        {
            "library": "lib1",
            "folder": "folder1",
            "title": "Evil Title\r\nX-Injected: yes",
            "author": "Author",
        },
        str(audio_file),
    )

    assert b"\r\nX-Injected" not in body
    assert b"Evil TitleX-Injected: yes" in body


@patch("calishelf.abs_client.urlopen")
def test_list_libraries_sends_bearer_auth_header(mock_urlopen):
    mock_urlopen.return_value = _fake_response(json.dumps({"libraries": [{"id": "lib1"}]}).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    libraries = client.list_libraries()

    assert libraries == [{"id": "lib1"}]
    sent_request = mock_urlopen.call_args[0][0]
    assert sent_request.headers.get("Authorization") == "Bearer secret-key"
    assert sent_request.full_url == "https://abs.example.com/api/libraries"


@patch("calishelf.abs_client.urlopen")
def test_list_library_items_parses_metadata(mock_urlopen):
    payload = {
        "results": [
            {
                "id": "item1",
                "media": {
                    "metadata": {
                        "title": "Dune",
                        "authorName": "Frank Herbert",
                        "asin": "B000ASIN1",
                    }
                },
            }
        ]
    }
    mock_urlopen.return_value = _fake_response(json.dumps(payload).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    items = client.list_library_items("lib1")

    assert len(items) == 1
    assert items[0].id == "item1"
    assert items[0].title == "Dune"
    assert items[0].authors == ("Frank Herbert",)
    assert items[0].asin == "B000ASIN1"


@patch("calishelf.abs_client.urlopen")
def test_list_library_items_splits_multiple_authors(mock_urlopen):
    payload = {
        "results": [
            {
                "id": "item1",
                "media": {"metadata": {"title": "Good Omens", "authorName": "Neil Gaiman, Terry Pratchett"}},
            }
        ]
    }
    mock_urlopen.return_value = _fake_response(json.dumps(payload).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    items = client.list_library_items("lib1")

    assert items[0].authors == ("Neil Gaiman", "Terry Pratchett")


@patch("calishelf.abs_client.urlopen")
def test_list_library_items_handles_explicit_null_title(mock_urlopen):
    # An item with unscanned/missing metadata can have "title": null (not
    # just a missing key) -- .get(key, default) doesn't catch that, only
    # .get(key) or default does. Must not crash the whole sync run over it.
    payload = {"results": [{"id": "item1", "media": {"metadata": {"title": None}}}]}
    mock_urlopen.return_value = _fake_response(json.dumps(payload).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    items = client.list_library_items("lib1")

    assert items[0].title == ""


@patch("calishelf.abs_client.urlopen")
def test_list_library_items_handles_explicit_null_results(mock_urlopen):
    payload = {"results": None}
    mock_urlopen.return_value = _fake_response(json.dumps(payload).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    assert client.list_library_items("lib1") == []


@patch("calishelf.abs_client.urlopen")
def test_list_library_items_url_encodes_library_id(mock_urlopen):
    mock_urlopen.return_value = _fake_response(json.dumps({"results": []}).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    client.list_library_items("weird id/with?chars")

    sent_request = mock_urlopen.call_args[0][0]
    assert sent_request.full_url == "https://abs.example.com/api/libraries/weird%20id%2Fwith%3Fchars/items"


@patch("calishelf.abs_client.urlopen")
def test_list_library_items_skips_entries_without_id(mock_urlopen):
    payload = {
        "results": [
            {"media": {"metadata": {"title": "No ID Here"}}},
            {"id": "item1", "media": {"metadata": {"title": "Dune"}}},
        ]
    }
    mock_urlopen.return_value = _fake_response(json.dumps(payload).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    items = client.list_library_items("lib1")

    assert [item.id for item in items] == ["item1"]


@patch("calishelf.abs_client.urlopen")
def test_trigger_scan_posts_to_scan_endpoint_with_auth_header(mock_urlopen):
    mock_urlopen.return_value = _fake_response(b"OK")
    client = ABSClient("https://abs.example.com", "secret-key")

    client.trigger_scan("lib1")

    sent_request = mock_urlopen.call_args[0][0]
    assert sent_request.full_url == "https://abs.example.com/api/libraries/lib1/scan"
    assert sent_request.headers.get("Authorization") == "Bearer secret-key"
    assert sent_request.get_method() == "POST"


@patch("calishelf.abs_client.urlopen")
def test_get_json_raises_abs_error_on_invalid_json(mock_urlopen):
    mock_urlopen.return_value = _fake_response(b"<html>not json</html>")
    client = ABSClient("https://abs.example.com", "secret-key")

    with pytest.raises(ABSClientError):
        client.list_libraries()


@patch("calishelf.abs_client.urlopen")
def test_get_json_raises_abs_error_on_unexpected_json_shape(mock_urlopen):
    mock_urlopen.return_value = _fake_response(json.dumps(["not", "a", "dict"]).encode())
    client = ABSClient("https://abs.example.com", "secret-key")

    with pytest.raises(ABSClientError):
        client.list_libraries()


@patch("calishelf.abs_client.urlopen")
def test_upload_book_posts_multipart_with_auth_header(mock_urlopen, tmp_path):
    audio_file = tmp_path / "book.m4b"
    audio_file.write_bytes(b"fake-audio-bytes")
    mock_urlopen.return_value = _fake_response(b"{}")
    client = ABSClient("https://abs.example.com", "secret-key")
    book = BookToSync(title="Dune", authors=("Frank Herbert",), file_path=str(audio_file), asin="B000ASIN1")

    client.upload_book("lib1", "folder1", book)

    sent_request = mock_urlopen.call_args[0][0]
    assert sent_request.headers.get("Authorization") == "Bearer secret-key"
    assert sent_request.headers.get("Content-type", "").startswith("multipart/form-data")
    assert sent_request.full_url == "https://abs.example.com/api/upload"
    assert b"fake-audio-bytes" in sent_request.data


def test_upload_book_missing_local_file_raises_abs_client_error(tmp_path):
    # The file went missing (or became unreadable) between scanning the
    # library and uploading it -- this must surface as an ABSClientError
    # (which SyncEngine.run catches per-book), not a raw OSError that would
    # crash the whole sync run.
    client = ABSClient("https://abs.example.com", "secret-key")
    book = BookToSync(
        title="Ghost Book",
        authors=("Nobody",),
        file_path=str(tmp_path / "does-not-exist.m4b"),
        asin=None,
    )

    with pytest.raises(ABSClientError):
        client.upload_book("lib1", "folder1", book)
