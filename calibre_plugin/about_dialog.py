from qt.core import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class AboutDialog(QDialog):
    def __init__(self, parent, base_plugin):
        QDialog.__init__(self, parent)
        self.setWindowTitle("About CaliShelf")

        version = ".".join(str(part) for part in base_plugin.version)
        repo_line = (
            f'<p><a href="{base_plugin.repo_url}">{base_plugin.repo_url}</a></p>'
            if base_plugin.repo_url
            else "<p>Repository: not published yet</p>"
        )
        html = (
            f"<h3>CaliShelf {version}</h3>"
            f"<p>{base_plugin.description}</p>"
            f"<p>Author: {base_plugin.author}<br>License: MIT</p>"
            f"{repo_line}"
        )

        label = QLabel(html, self)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(button_box)
        self.resize(380, 220)
