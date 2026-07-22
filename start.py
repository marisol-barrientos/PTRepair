import argparse
import os
import signal
import subprocess
import sys
import time

import uvicorn


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PID_FILE = os.path.join(
    BASE_DIR,
    "comprepair.pid",
)

LOG_FILE = os.path.join(
    BASE_DIR,
    "comprepair.log",
)

PORT = 3592


def run_server() -> None:
    """
    Run CompRepair in the foreground.
    """

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        app_dir=BASE_DIR,
    )


def _read_pid() -> int | None:
    """
    Read the stored server PID.
    """

    if not os.path.exists(PID_FILE):
        return None

    try:
        with open(
            PID_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            return int(
                file.read().strip()
            )

    except (
        OSError,
        ValueError,
    ):
        return None


def _is_running(
    pid: int | None,
) -> bool:
    """
    Check whether a process exists.
    """

    if pid is None:
        return False

    try:
        os.kill(pid, 0)
        return True

    except OSError:
        return False


def _start_daemon() -> None:
    """
    Start CompRepair as a background process.
    """

    existing_pid = _read_pid()

    if _is_running(existing_pid):
        print(
            "CompRepair already running "
            f"(PID {existing_pid})"
        )
        return

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8",
    ) as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api:app",
                "--app-dir",
                BASE_DIR,
                "--host",
                "0.0.0.0",
                "--port",
                str(PORT),
                "--log-level",
                "info",
            ],
            cwd=BASE_DIR,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )

    with open(
        PID_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            str(process.pid)
        )

    print(
        "Started CompRepair "
        f"(PID {process.pid}, port {PORT})"
    )


def _stop_daemon() -> None:
    """
    Stop the background service gracefully.
    """

    pid = _read_pid()

    if pid is None:
        print(
            "CompRepair is not running."
        )
        return

    if not _is_running(pid):
        print(
            "Removing stale PID file."
        )

        os.remove(PID_FILE)
        return

    print(
        f"Stopping CompRepair (PID {pid})"
    )

    try:
        os.kill(
            pid,
            signal.SIGINT,
        )

    except OSError as error:
        print(
            f"Could not stop CompRepair: {error}"
        )
        return

    for _ in range(50):
        if not _is_running(pid):
            break

        time.sleep(0.1)

    if _is_running(pid):
        print(
            "CompRepair did not stop gracefully."
        )
        return

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    print(
        "CompRepair stopped."
    )


def _status_daemon() -> None:
    """
    Display the service status.
    """

    pid = _read_pid()

    if _is_running(pid):
        print(
            "CompRepair is running "
            f"(PID {pid}, port {PORT})"
        )

    elif pid is not None:
        print(
            "CompRepair is not running "
            f"(stale PID {pid})"
        )

    else:
        print(
            "CompRepair is not running."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Manage the CompRepair service."
        )
    )

    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the background service.",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show service status.",
    )

    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in the foreground.",
    )

    args = parser.parse_args()

    if args.stop:
        _stop_daemon()

    elif args.status:
        _status_daemon()

    elif args.foreground:
        run_server()

    else:
        _start_daemon()
