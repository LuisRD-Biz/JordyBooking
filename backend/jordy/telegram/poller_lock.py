"""One local poller per bot and operating-system user, across working copies."""

import os
from contextlib import contextmanager
from pathlib import Path


class PollerLockError(Exception):
    pass


@contextmanager
def single_poller(bot_id: str, directory: Path | None = None):
    if directory is None:
        cache = os.environ.get("LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME")
        directory = (Path(cache) if cache else Path.home() / ".cache") / "JordyBooking" / "locks"
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Only the bot's numeric ID is used. Never store its secret.
        lock = (directory / f"telegram-{bot_id}.lock").open("a+b")
    except OSError:
        raise PollerLockError("No se pudo abrir el bloqueo local de Telegram.") from None
    with lock:
        try:
            if os.name == "nt":
                import msvcrt

                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise PollerLockError("No se pudo tomar el bloqueo. Revisa otras instancias.") from None
        # The OS releases the lock on close or process exit. Keep the file:
        # deleting it would let two processes lock different files at this path.
        yield
