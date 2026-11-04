"""Start only this project's local services; never initialize or migrate a database."""

import ctypes
import hashlib
import json
import logging
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
ORIGIN = "http://127.0.0.1:8000"
INSTANCE = hashlib.sha256(str(ROOT).casefold().encode()).hexdigest()[:24]
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def occupied(port):
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def ready():
    try:
        with build_opener(ProxyHandler({})).open(ORIGIN + "/health/ready", timeout=2) as response:
            data = json.load(response)
        return (
            data.get("status") == "ready"
            and data.get("application") == "jordy-studio"
            and data.get("instance") == INSTANCE
        )
    except (URLError, HTTPError, ValueError, OSError):
        return False


def postgres_bin(cluster):
    version = (cluster / "PG_VERSION").read_text().strip()
    candidates = []
    if os.environ.get("PG_BIN"):
        candidates.append(Path(os.environ["PG_BIN"]))
    candidates.append(
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL" / version / "bin"
    )
    if os.name == "nt":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\PostgreSQL\Installations"
            ) as key:
                for index in range(winreg.QueryInfoKey(key)[0]):
                    with winreg.OpenKey(key, winreg.EnumKey(key, index)) as entry:
                        base, _ = winreg.QueryValueEx(entry, "Base Directory")
                        candidates.append(Path(base) / "bin")
        except OSError:
            pass
    for candidate in candidates:
        executable = candidate / "pg_ctl.exe"
        if executable.is_file():
            result = subprocess.run(
                [str(executable), "--version"], capture_output=True, text=True, creationflags=HIDDEN
            )
            if result.returncode == 0 and result.stdout.split()[-1].split(".")[0] == version:
                return candidate
    raise RuntimeError(
        f"No se encontró PostgreSQL {version}. Revisa su instalación o configura PG_BIN."
    )


def configuration():
    if not (ROOT / ".env").is_file():
        raise RuntimeError(
            "Falta la configuración local (.env). No se creó ni modificó la base de datos."
        )
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError(
            "Falta preparar el panel de React. Consulta docs/panel.md para compilarlo."
        )
    try:
        import psycopg  # noqa: F401
        import uvicorn  # noqa: F401
        from dotenv import dotenv_values
        from sqlalchemy.engine import make_url
    except ImportError as exc:
        raise RuntimeError(
            "Faltan dependencias. Consulta la instalación en docs/panel.md."
        ) from exc
    config = dotenv_values(ROOT / ".env")
    url = make_url(config.get("DATABASE_URL", ""))
    if url.host != "127.0.0.1" or url.port != 55433 or url.database != "jordy_panel":
        raise RuntimeError("La base no corresponde a 127.0.0.1:55433/jordy_panel. Revisa .env.")
    if config.get("PANEL_ORIGIN", ORIGIN).rstrip("/") != ORIGIN:
        raise RuntimeError("PANEL_ORIGIN debe corresponder al panel local en el puerto 8000.")
    if len(config.get("ADMIN_API_KEY", "")) < 32:
        raise RuntimeError("La clave administrativa no está configurada correctamente.")
    cluster = LOCAL / "panel-pgdata"
    if not (cluster / "PG_VERSION").is_file():
        raise RuntimeError("No se encontró el cluster existente. Recupera su respaldo.")
    return url, cluster, postgres_bin(cluster)


def database_ready(url, cluster):
    import psycopg
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    with psycopg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname=url.database,
        connect_timeout=4,
    ) as connection:
        actual = Path(connection.execute("SHOW data_directory").fetchone()[0]).resolve()
        if actual != cluster.resolve():
            raise RuntimeError(
                "El puerto de PostgreSQL pertenece a otro cluster. No se modificó ese servicio."
            )
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "migrations"))
        expected = ScriptDirectory.from_config(config).get_current_head()
        current = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        if expected != current:
            raise RuntimeError("La base necesita actualizarse. Consulta docs/panel.md.")


def pg_control(pg, cluster, *arguments):
    with (LOCAL / "launcher-postgres.log").open("a", encoding="utf-8") as log:
        return subprocess.run(
            [str(pg / "pg_ctl.exe"), "-D", str(cluster), *map(str, arguments)],
            stdout=log,
            stderr=log,
            creationflags=HIDDEN,
            timeout=40,
        ).returncode


def start():
    url, cluster, pg = configuration()
    if occupied(8000):
        if ready():
            database_ready(url, cluster)
            logging.info("Reusing ready application")
            return
        raise RuntimeError(
            "El puerto 8000 está ocupado o no preparado. Revisa el servidor existente."
        )
    pg_started = False
    server = None
    try:
        if pg_control(pg, cluster, "status") != 0:
            if occupied(url.port):
                raise RuntimeError(
                    "El puerto 55433 está ocupado por otro servicio. No se modificó."
                )
            pg_started = True
            if pg_control(
                pg,
                cluster,
                "-l",
                LOCAL / "panel-postgres.log",
                "-o",
                "-p 55433 -h 127.0.0.1",
                "-w",
                "-t",
                "30",
                "start",
            ):
                raise RuntimeError(
                    "PostgreSQL no pudo iniciar. Consulta los registros de arranque."
                )
        database_ready(url, cluster)
        with (
            (LOCAL / "panel-server.log").open("a", encoding="utf-8") as out,
            (LOCAL / "panel-server-error.log").open("a", encoding="utf-8") as err,
        ):
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "jordy.main:app",
                    "--app-dir",
                    "backend",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    **{
                        k: v
                        for k, v in __import__("dotenv").dotenv_values(ROOT / ".env").items()
                        if v is not None
                    },
                },
                stdout=out,
                stderr=err,
                creationflags=HIDDEN,
            )
        (LOCAL / "panel-server.pid").write_text(str(server.pid))
        for _ in range(60):
            if server.poll() is not None:
                raise RuntimeError("El servidor no pudo iniciar. Consulta panel-server-error.log.")
            if ready():
                logging.info("Application ready")
                return
            time.sleep(0.5)
        raise RuntimeError(
            "El panel no estuvo preparado a tiempo. Consulta los registros antes de reintentar."
        )
    except Exception:
        if server and server.poll() is None:
            # Only the process tree created here, never a process selected by port or name.
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(server.pid), "/T", "/F"],
                    capture_output=True,
                    creationflags=HIDDEN,
                )
            else:
                server.terminate()
            server.wait(timeout=10)
        if pg_started:
            pg_control(pg, cluster, "-m", "fast", "-w", "stop")
        raise


def main():
    LOCAL.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOCAL / "launcher.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        import msvcrt

        with (LOCAL / "launcher.lock").open("a+b") as lock:
            lock.seek(0)
            if not lock.read(1):
                lock.write(b"0")
                lock.flush()
            for attempt in range(90):
                try:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                raise RuntimeError(
                    "Otro arranque sigue en curso. Espera un momento y vuelve a intentarlo."
                )
            try:
                start()
                if "--no-browser" not in sys.argv:
                    webbrowser.open(ORIGIN)
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception as exc:
        # Driver exception arguments can contain credentials; only our messages are displayed.
        message = (
            str(exc)
            if isinstance(exc, RuntimeError)
            else "No se pudo iniciar. Revisa PostgreSQL, configuración y dependencias."
        )
        logging.error("%s: %s", type(exc).__name__, message)
        if "--no-browser" not in sys.argv:
            ctypes.windll.user32.MessageBoxW(
                0, message + "\n\nRegistro: " + str(LOCAL / "launcher.log"), "Jordy Studio", 0x10
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
