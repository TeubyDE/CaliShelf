import queue

from qt.core import QDialog, QDialogButtonBox, QLabel, QProgressBar, QTimer, QVBoxLayout


class SyncDialog(QDialog):
    def __init__(self, gui, config):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.config = config
        self.job = None

        self.setWindowTitle("CaliShelf - Sync to Audiobookshelf")
        self.status_label = QLabel("Preparing...")
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.button_box)
        self.resize(480, 150)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._drain_notifications)
        self.finished.connect(self.timer.stop)

    def start(self, books):
        from calibre_plugins.calishelf.job import run_sync_job

        if not books:
            self.status_label.setText("No books flagged with the audiobook column were found.")
            return

        self.status_label.setText(f"Syncing {len(books)} book(s)...")
        from calibre.gui2.threaded_jobs import ThreadedJob

        self.job = ThreadedJob(
            "calishelf_sync",
            "Sync audiobooks to Audiobookshelf",
            run_sync_job,
            [self.config, books],
            {},
            self._on_finished,
        )
        self.gui.job_manager.run_threaded_job(self.job)
        self.timer.start(250)

    def _drain_notifications(self):
        if self.job is None:
            return
        try:
            while True:
                fraction, message = self.job.notifications.get_nowait()
                self.progress_bar.setValue(int(fraction * 100))
                self.status_label.setText(message)
        except queue.Empty:
            pass

    def _on_finished(self, job):
        self.timer.stop()
        if job.failed:
            from calibre_plugins.calishelf.job import SyncAborted

            if isinstance(job.exception, SyncAborted):
                self.status_label.setText(str(job.exception) or "Sync cancelled.")
            else:
                self.status_label.setText(f"Sync failed: {job.exception}")
            return

        result = job.result
        summary = (
            f"Done. Uploaded: {len(result.uploaded)}, "
            f"skipped (already present): {len(result.skipped)}, "
            f"failed: {len(result.failed)}."
        )
        if result.failed:
            details = "\n".join(f"- {book.title}: {reason}" for book, reason in result.failed)
            summary += f"\n\nFailures:\n{details}"
        self.status_label.setText(summary)
        self.progress_bar.setValue(100)
