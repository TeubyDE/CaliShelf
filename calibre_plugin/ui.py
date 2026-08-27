from calibre.gui2 import error_dialog, gprefs
from calibre.gui2.actions import InterfaceAction
from qt.core import QDesktopServices, QUrl


class CaliShelfAction(InterfaceAction):
    name = "CaliShelf"
    action_spec = (
        "Sync to Audiobookshelf",
        None,
        "Push flagged audiobooks to your Audiobookshelf server",
        None,
    )
    # Gives the toolbar button a dropdown arrow with a small menu. The main
    # click still triggers the sync directly (connected below); "Sync to
    # Audiobookshelf" is also added explicitly as the first menu entry
    # (rather than relying on action_menu_clone_qaction's automatic clone,
    # which doesn't pick up the icon set in genesis()).
    action_add_menu = True

    def genesis(self):
        # get_icons is injected into this module's namespace by Calibre's
        # plugin loader at runtime, not a real import.
        icon = get_icons("images/icon.png", "CaliShelf")  # noqa: F821
        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.show_dialog)
        self.create_menu_action(
            self.qaction.menu(),
            "calishelf_sync",
            "Sync to Audiobookshelf",
            icon="view-refresh.png",
            triggered=self.show_dialog,
        )
        self.create_menu_action(
            self.qaction.menu(),
            "calishelf_configure",
            "Configure CaliShelf...",
            icon="config.png",
            triggered=self.show_configuration,
        )
        self.create_menu_action(
            self.qaction.menu(),
            "calishelf_about",
            "About CaliShelf...",
            icon="dialog_information.png",
            triggered=self.show_about,
        )
        self.create_menu_action(
            self.qaction.menu(),
            "calishelf_help",
            "Help / Instructions...",
            icon="help.png",
            triggered=self.show_help,
        )
        self.create_menu_action(
            self.qaction.menu(),
            "calishelf_report_bug",
            "Report a Bug...",
            icon="debug.png",
            triggered=self.show_report_bug,
        )

    def initialization_complete(self):
        # Runs once, after the main window and its toolbars already exist --
        # unlike genesis(), a blocking dialog here can't stall calibre's own
        # startup sequence.
        self._ensure_toolbar_placement()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def show_about(self):
        from calibre_plugins.calishelf.about_dialog import AboutDialog

        AboutDialog(self.gui, self.interface_action_base_plugin).exec()

    def show_help(self):
        self._open_repo_url()

    def show_report_bug(self):
        self._open_repo_url("/issues")

    def _open_repo_url(self, path=""):
        repo_url = self.interface_action_base_plugin.repo_url
        if not repo_url:
            error_dialog(
                self.gui,
                "CaliShelf",
                "No repository URL is configured yet.",
                show=True,
            )
            return
        QDesktopServices.openUrl(QUrl(repo_url + path))

    def _ensure_toolbar_placement(self):
        """Add our own button to the main toolbar the first time this plugin
        runs, so the user doesn't have to dig through Preferences ->
        Toolbars & Menus manually. Only done once (tracked in our own
        prefs) so a later manual removal by the user is respected."""
        from calibre_plugins.calishelf.config_widget import prefs

        if prefs.get("toolbar_setup_done"):
            return
        prefs["toolbar_setup_done"] = True

        layout = list(gprefs.get("action-layout-toolbar") or [])
        if self.name in layout:
            return
        layout.append(self.name)
        gprefs["action-layout-toolbar"] = layout

    def show_dialog(self):
        from calibre_plugins.calishelf.calibre_reader import get_books_to_sync
        from calibre_plugins.calishelf.calishelf.config import CaliShelfConfig
        from calibre_plugins.calishelf.config_widget import prefs
        from calibre_plugins.calishelf.main import SyncDialog

        config = CaliShelfConfig(
            base_url=prefs["base_url"],
            api_key=prefs["api_key"],
            library_id=prefs["library_id"],
            folder_id=prefs["folder_id"],
            audiobook_column=prefs["audiobook_column"],
            asin_identifier_key=prefs["asin_identifier_key"],
            audio_extensions=CaliShelfConfig.parse_audio_extensions(prefs["audio_extensions"]),
        )
        try:
            config.validate()
        except ValueError as exc:
            error_dialog(
                self.gui,
                "CaliShelf",
                f"Please configure CaliShelf first (click the dropdown arrow "
                f"on the CaliShelf toolbar button -> Configure CaliShelf...):\n{exc}",
                show=True,
            )
            return

        books, errors = get_books_to_sync(
            self.gui.current_db,
            config.audiobook_column,
            config.asin_identifier_key,
            config.audio_extensions,
        )

        if errors:
            details = "\n".join(f"- book id {book_id}: {message}" for book_id, message in errors)
            error_dialog(
                self.gui,
                "CaliShelf",
                f"Skipped {len(errors)} book(s) that couldn't be read (the rest "
                f"will still be synced):\n{details}",
                show=True,
            )

        dialog = SyncDialog(self.gui, config)
        dialog.show()
        dialog.start(books)
