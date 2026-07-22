import argparse
import os
import signal
import subprocess
import sys

import uvicorn


PID_FILE = "comprepair.pid"
LOG_FILE = "comprepair.log"
PORT = 3592


def run_server():
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )


def _read_pid():

    if not os.path.exists(PID_FILE):
        return None

    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _is_running(pid):

    if pid is None:
        return False

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _start_daemon():

    existing_pid = _read_pid()

    if _is_running(existing_pid):
        print(f"CompRepair already running (PID {existing_pid})")
        return

    if existing_pid and os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    log_path = os.path.join(
        os.path.dirname(__file__),
        LOG_FILE,
    )

    with open(log_path, "a") as log_file:

        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(PORT),
                "--log-level",
                "info",
            ],
            cwd=os.path.dirname(__file__),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )

    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    print(f"Started CompRepair (PID {process.pid})")


def _stop_daemon():

    pid = _read_pid()

    if pid is None:
        print("CompRepair is not running.")
        return

    if not _is_running(pid):

        print("Removing stale PID file.")

        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

        return

    print(f"Stopping CompRepair (PID {pid})")

    os.kill(pid, signal.SIGINT)

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def _status_daemon():

    pid = _read_pid()

    if _is_running(pid):
        print(f"CompRepair is running (PID {pid})")
    elif pid:
        print(f"CompRepair is not running (stale PID {pid})")
    else:
        print("CompRepair is not running")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Manage the CompRepair service."
    )

    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the background service",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show service status",
    )

    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground",
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