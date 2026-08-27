from dataclasses import dataclass, field

DEFAULT_AUDIO_EXTENSIONS: tuple[str, ...] = ("m4b", "mp3", "m4a")


@dataclass
class CaliShelfConfig:
    base_url: str
    api_key: str
    library_id: str
    folder_id: str
    audiobook_column: str = "#audiobook"
    asin_identifier_key: str = "asin"
    audio_extensions: tuple[str, ...] = field(default=DEFAULT_AUDIO_EXTENSIONS)

    def validate(self) -> None:
        missing = [
            name
            for name in ("base_url", "api_key", "library_id", "folder_id")
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"Missing required config field(s): {', '.join(missing)}")

    @staticmethod
    def parse_audio_extensions(raw: str) -> tuple[str, ...]:
        extensions = tuple(ext.strip().lstrip(".") for ext in raw.split(","))
        return tuple(ext for ext in extensions if ext) or DEFAULT_AUDIO_EXTENSIONS[:1]
