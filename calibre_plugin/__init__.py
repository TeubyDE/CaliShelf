from typing import ClassVar

from calibre.customize import InterfaceActionBase


class CaliShelfPlugin(InterfaceActionBase):
    name = "CaliShelf"
    description = (
        "Push audiobooks flagged in Calibre (#audiobook = Yes) to a "
        "self-hosted Audiobookshelf server, skipping anything already "
        "present."
    )
    supported_platforms: ClassVar[list[str]] = ["windows", "osx", "linux"]
    author = "TeubyDE"
    version = (0, 1, 0)
    minimum_calibre_version = (5, 0, 0)
    repo_url = "https://github.com/TeubyDE/CaliShelf"

    actual_plugin = "calibre_plugins.calishelf.ui:CaliShelfAction"

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.calishelf.config_widget import ConfigWidget

        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
