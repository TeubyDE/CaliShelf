from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BookToSync:
    title: str
    authors: tuple[str, ...]
    file_path: str
    asin: str | None = None


@dataclass(frozen=True)
class ABSLibraryItem:
    id: str
    title: str
    authors: tuple[str, ...]
    asin: str | None = None


@dataclass
class SyncResult:
    uploaded: list[BookToSync] = field(default_factory=list)
    skipped: list[BookToSync] = field(default_factory=list)
    failed: list[tuple[BookToSync, str]] = field(default_factory=list)
