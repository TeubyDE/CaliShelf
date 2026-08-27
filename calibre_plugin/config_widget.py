"""Settings UI for the CaliShelf plugin.

Note the doubled `calishelf.calishelf` import path: the core engine lives in
the top-level `calishelf/` package of this repo and is copied verbatim into
this plugin's ZIP as a subpackage by scripts/build_plugin_zip.py, so it is
importable as `calibre_plugins.calishelf.calishelf.*` at runtime.
"""

from calibre.utils.config import JSONConfig
from calibre_plugins.calishelf.calishelf.config import DEFAULT_AUDIO_EXTENSIONS
from qt.core import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
)

prefs = JSONConfig("plugins/calishelf")
prefs.defaults["base_url"] = ""
prefs.defaults["api_key"] = ""
prefs.defaults["library_id"] = ""
prefs.defaults["folder_id"] = ""
prefs.defaults["audiobook_column"] = "#audiobook"
prefs.defaults["asin_identifier_key"] = "asin"
prefs.defaults["audio_extensions"] = ", ".join(DEFAULT_AUDIO_EXTENSIONS)
prefs.defaults["toolbar_setup_done"] = False


class DiscoverDialog(QDialog):
    """Pick a library and one of its folders from two linked lists."""

    def __init__(self, parent, libraries):
        QDialog.__init__(self, parent)
        self.setWindowTitle("CaliShelf - Discover libraries")
        self.selected_library_id = None
        self.selected_folder_id = None

        self.library_list = QListWidget(self)
        self.folder_list = QListWidget(self)
        for library in libraries:
            item = QListWidgetItem(library.get("name", "(unnamed)"))
            item.setData(Qt.ItemDataRole.UserRole, library)
            self.library_list.addItem(item)
        self.library_list.currentItemChanged.connect(self._on_library_selected)
        self.folder_list.currentItemChanged.connect(self._update_ok_enabled)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._accept_selection)
        self.button_box.rejected.connect(self.reject)

        lists_layout = QHBoxLayout()
        library_column = QVBoxLayout()
        library_column.addWidget(QLabel("Library:"))
        library_column.addWidget(self.library_list)
        folder_column = QVBoxLayout()
        folder_column.addWidget(QLabel("Folder:"))
        folder_column.addWidget(self.folder_list)
        lists_layout.addLayout(library_column)
        lists_layout.addLayout(folder_column)

        layout = QVBoxLayout(self)
        layout.addLayout(lists_layout)
        layout.addWidget(self.button_box)
        self.resize(560, 320)

        if libraries:
            self.library_list.setCurrentRow(0)
        self._update_ok_enabled()

    def _on_library_selected(self, current, _previous):
        self.folder_list.clear()
        if current is not None:
            library = current.data(Qt.ItemDataRole.UserRole)
            for folder in library.get("folders") or []:
                label = folder.get("fullPath") or folder.get("id", "")
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, folder)
                self.folder_list.addItem(item)
            if self.folder_list.count():
                self.folder_list.setCurrentRow(0)
        self._update_ok_enabled()

    def _update_ok_enabled(self, *_args):
        enabled = (
            self.library_list.currentItem() is not None
            and self.folder_list.currentItem() is not None
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def _accept_selection(self):
        self.selected_library_id = self.library_list.currentItem().data(
            Qt.ItemDataRole.UserRole
        )["id"]
        self.selected_folder_id = self.folder_list.currentItem().data(
            Qt.ItemDataRole.UserRole
        )["id"]
        self.accept()


class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.base_url = QLineEdit(prefs["base_url"], self)
        self.api_key = QLineEdit(prefs["api_key"], self)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.library_id = QLineEdit(prefs["library_id"], self)
        self.folder_id = QLineEdit(prefs["folder_id"], self)
        self.audiobook_column = QLineEdit(prefs["audiobook_column"], self)
        self.asin_identifier_key = QLineEdit(prefs["asin_identifier_key"], self)
        self.audio_extensions = QLineEdit(prefs["audio_extensions"], self)

        self.discover_button = QPushButton("Discover libraries...")
        self.discover_button.clicked.connect(self.discover_libraries)

        form = QFormLayout()
        form.addRow("Audiobookshelf URL:", self.base_url)
        form.addRow("API key:", self.api_key)
        form.addRow("", self.discover_button)
        form.addRow("Library ID:", self.library_id)
        form.addRow("Folder ID:", self.folder_id)
        form.addRow("Audiobook custom column:", self.audiobook_column)
        form.addRow("ASIN identifier key:", self.asin_identifier_key)
        form.addRow("Audio file extensions (comma-separated):", self.audio_extensions)

        layout = QVBoxLayout()
        layout.addLayout(form)
        self.setLayout(layout)

    def discover_libraries(self):
        from calibre_plugins.calishelf.calishelf.abs_client import (
            ABSClient,
            ABSClientError,
        )

        try:
            client = ABSClient(self.base_url.text(), self.api_key.text())
            libraries = client.list_libraries()
        except (ABSClientError, ValueError) as exc:
            QMessageBox.warning(self, "CaliShelf", f"Could not reach Audiobookshelf:\n{exc}")
            return

        if not libraries:
            QMessageBox.information(self, "CaliShelf", "No libraries found on this server.")
            return

        dialog = DiscoverDialog(self, libraries)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.library_id.setText(dialog.selected_library_id or "")
            self.folder_id.setText(dialog.selected_folder_id or "")

    def save_settings(self):
        prefs["base_url"] = self.base_url.text().strip()
        prefs["api_key"] = self.api_key.text().strip()
        prefs["library_id"] = self.library_id.text().strip()
        prefs["folder_id"] = self.folder_id.text().strip()
        prefs["audiobook_column"] = self.audiobook_column.text().strip() or "#audiobook"
        prefs["asin_identifier_key"] = self.asin_identifier_key.text().strip() or "asin"
        prefs["audio_extensions"] = self.audio_extensions.text().strip() or ", ".join(
            DEFAULT_AUDIO_EXTENSIONS
        )
