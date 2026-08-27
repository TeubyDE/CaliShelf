"""Adapts calishelf.sync.SyncEngine to calibre's ThreadedJob function contract."""


class SyncAborted(Exception):
    pass


def run_sync_job(config, books, abort, log, notifications):
    from calibre_plugins.calishelf.calishelf.sync import SyncEngine

    engine = SyncEngine(config)

    def progress_cb(fraction, message):
        if abort.is_set():
            log("Sync aborted by user.")
            raise SyncAborted("Sync cancelled by user.")
        log(message)
        notifications.put((fraction, message))

    return engine.run(books, progress_cb=progress_cb)
