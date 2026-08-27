# CaliShelf

A Calibre plugin that pushes audiobooks flagged in your Calibre library to a
self-hosted [Audiobookshelf](https://www.audiobookshelf.org/) server,
skipping anything already present. No manual re-uploads, no mounted drives,
no local sync ledger -- Audiobookshelf is always asked live whether a book
is already there.

---

## Anleitung

CaliShelf lädt die Hörbücher, die du in Calibre markierst, automatisch zu
deinem Audiobookshelf-Server hoch. Kein manuelles Kopieren, keine
Duplikate bei erneutem Ausführen.

### Einmalig einrichten

1. Custom Column `#audiobook` (Ja/Nein) in Calibre anlegen, falls noch
   nicht vorhanden.
2. Plugin installieren (siehe unten).
3. Über den Toolbar-Button → Dropdown-Pfeil → "Configure CaliShelf..."
   eintragen: Audiobookshelf-URL, API-Key, Library-ID und Folder-ID (per
   "Discover libraries..." auswählbar, kein Abtippen nötig).

### Nutzung

1. Bücher in Calibre mit `#audiobook = Ja` markieren.
2. Auf den Sync-Button in der Toolbar klicken.
3. Fertig, sobald "Done" erscheint.

Erneutes Klicken ist unbedenklich — bereits vorhandene Bücher werden nicht
noch einmal hochgeladen.

### Gut zu wissen

- Liest nur aus Calibre, schreibt nie etwas zurück.
- Unterstützt nur Hörbücher als Einzeldatei (z. B. `.m4b`) — mehrteilige
  Hörbücher vorher zusammenführen.
- Titeländerung in Calibre nach dem ersten Sync kann zu einem erneuten
  Upload führen, solange das Buch in Audiobookshelf noch nicht per ASIN
  gematcht wurde.
- API-Key wie ein Passwort behandeln, nicht weitergeben.

---

## Guide

CaliShelf uploads the audiobooks you flag in Calibre to your Audiobookshelf
server automatically. No manual copying, no duplicates on repeated runs.

### One-time setup

1. Create the `#audiobook` custom column (Yes/No) in Calibre, if it
   doesn't exist yet.
2. Install the plugin (see below).
3. Via the toolbar button -> dropdown arrow -> "Configure CaliShelf...",
   enter the Audiobookshelf URL, API key, library ID and folder ID
   ("Discover libraries..." lets you pick these instead of typing them).

### Usage

1. Flag books in Calibre with `#audiobook = Yes`.
2. Click the sync button in the toolbar.
3. Done once the dialog shows "Done".

Clicking it again is safe -- books already present won't be re-uploaded.

### Good to know

- Read-only on the Calibre side, never writes anything back.
- Only single-file audiobooks (e.g. `.m4b`) are supported -- merge
  multi-track audiobooks first.
- Editing a book's title in Calibre after its first sync can trigger a
  re-upload, until the book has been ASIN-matched in Audiobookshelf.
- Treat the API key like a password -- don't share it.

---

## A short note

I've done a fair share of programming in my daily work, but Python isn't
my main language, so I built most of the above with the help of Claude
Code. I made the calls on scope and security, and reviewed everything -
but a lot of the actual Python was written with AI assistance. If you
spot something that doesn't look idiomatic, feel free to open an issue.

## License

MIT, see [LICENSE](LICENSE).
