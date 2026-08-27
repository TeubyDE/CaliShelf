import pytest

from calishelf.config import CaliShelfConfig


def test_validate_raises_on_missing_required_fields():
    config = CaliShelfConfig(base_url="", api_key="", library_id="lib1", folder_id="folder1")
    with pytest.raises(ValueError, match="base_url"):
        config.validate()


def test_validate_passes_with_all_required_fields():
    config = CaliShelfConfig(
        base_url="https://abs.example.com", api_key="key", library_id="lib1", folder_id="folder1"
    )
    config.validate()  # should not raise


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("m4b, mp3, m4a", ("m4b", "mp3", "m4a")),
        (".m4b,.mp3", ("m4b", "mp3")),
        ("  m4b  ", ("m4b",)),
        ("", ("m4b",)),
        (",,", ("m4b",)),
    ],
)
def test_parse_audio_extensions(raw, expected):
    assert CaliShelfConfig.parse_audio_extensions(raw) == expected
