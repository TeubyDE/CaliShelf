"""Minimal Audiobookshelf REST client, stdlib-only (no requests/httpx).

Kept dependency-free on purpose: this module is copied verbatim into the
Calibre plugin's ZIP, which runs inside Calibre's bundled Python
interpreter where third-party packages are not guaranteed to be present.
"""

import json
import mimetypes
import os
import uuid
from urllib.parse import quote
from urllib.request import Request, urlopen

from .models import ABSLibraryItem, BookToSync


class ABSClientError(Exception):
    pass


class ABSClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _get_json(self, path: str) -> dict:
        request = Request(f"{self.base_url}{path}", headers=self._headers())
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw_body = response.read()
        except OSError as exc:
            raise ABSClientError(f"GET {path} failed: {exc}") from exc

        try:
            data = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ABSClientError(f"GET {path} returned an unparseable response: {exc}") from exc

        if not isinstance(data, dict):
            raise ABSClientError(f"GET {path} returned unexpected JSON (expected an object)")
        return data

    def list_libraries(self) -> list[dict]:
        return self._get_json("/api/libraries").get("libraries", [])

    def list_library_items(self, library_id: str) -> list[ABSLibraryItem]:
        data = self._get_json(f"/api/libraries/{quote(library_id, safe='')}/items")
        items = []
        for raw in data.get("results") or []:
            item_id = raw.get("id")
            if not item_id:
                continue
            media = raw.get("media") or {}
            metadata = media.get("metadata") or {}
            # Splitting "authorName" on "," can misparse a single author
            # whose own name contains a comma (rare) -- accepted, ABS gives
            # us no structured author list here.
            author_name = metadata.get("authorName") or ""
            items.append(
                ABSLibraryItem(
                    id=item_id,
                    title=metadata.get("title") or "",
                    authors=tuple(a.strip() for a in author_name.split(",") if a.strip()),
                    asin=metadata.get("asin") or None,
                )
            )
        return items

    def trigger_scan(self, library_id: str) -> None:
        """Ask Audiobookshelf to scan a library for new files.

        Uploads don't get picked up as library items on their own -- ABS's
        folder watcher can be slow or disabled, so we kick a scan explicitly
        after uploading. Fire-and-forget: the scan runs async on the server,
        we don't wait for it to finish.
        """
        request = Request(
            f"{self.base_url}/api/libraries/{quote(library_id, safe='')}/scan",
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response.read()
        except OSError as exc:
            raise ABSClientError(f"Triggering scan of library {library_id} failed: {exc}") from exc

    def upload_book(self, library_id: str, folder_id: str, book: BookToSync) -> None:
        fields = {
            "library": library_id,
            "folder": folder_id,
            "title": book.title,
            "author": ", ".join(book.authors),
        }
        boundary = uuid.uuid4().hex
        try:
            # Reading the local file happens in here too (see
            # _build_multipart_body) -- a book whose file went missing or
            # became unreadable between scanning the library and uploading
            # it must be recorded as a per-book failure, not crash the
            # whole sync run.
            body = _build_multipart_body(boundary, fields, book.file_path)
            headers = self._headers()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            request = Request(
                f"{self.base_url}/api/upload", data=body, headers=headers, method="POST"
            )
            with urlopen(request, timeout=self.timeout) as response:
                response.read()
        except OSError as exc:
            raise ABSClientError(f"Upload of '{book.title}' failed: {exc}") from exc


def _strip_crlf(value: str) -> str:
    """Strip CR/LF so a value can't inject an extra multipart header/part."""
    return value.replace("\r", "").replace("\n", "")


def _sanitize_header_value(value: str) -> str:
    """Strip CR/LF (header injection) and escape quotes for a header attribute."""
    return _strip_crlf(value).replace('"', "'")


def _build_multipart_body(boundary: str, fields: dict[str, str], file_path: str) -> bytes:
    crlf = b"\r\n"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b"")
        parts.append(_strip_crlf(value).encode("utf-8"))

    filename = _sanitize_header_value(os.path.basename(file_path))
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    parts.append(f"--{boundary}".encode())
    parts.append(
        f'Content-Disposition: form-data; name="0"; filename="{filename}"'.encode()
    )
    parts.append(f"Content-Type: {content_type}".encode())
    parts.append(b"")
    parts.append(file_bytes)
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")

    return crlf.join(parts)
