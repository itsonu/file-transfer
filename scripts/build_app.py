"""Build the standalone Open Transfer app in one command.

    python scripts/build_app.py        (python3 on macOS/Linux, py on Windows)

Produces a single executable that needs no Python on the target machine:

    dist/open-transfer        macOS / Linux
    dist/open-transfer.exe    Windows

Build on each OS you want to ship for (PyInstaller doesn't cross-compile).
Uses an isolated ``.build-venv`` so your own environment is left alone, then
smoke-tests the result by starting it and calling ``/api/health``.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".build-venv"
SPEC = ROOT / "packaging" / "open-transfer.spec"
DIST = ROOT / "dist"
EXE = DIST / ("open-transfer.exe" if os.name == "nt" else "open-transfer")


def say(message: str) -> None:
    print(f"  {message}", flush=True)


def run(*cmd: str | Path) -> None:
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT)  # noqa: S603


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def build() -> None:
    if sys.version_info < (3, 10):  # noqa: UP036 - friendly message on old Pythons
        sys.exit("Open Transfer needs Python 3.10 or newer to build.")
    if not venv_python().exists():
        say("Creating build environment (.build-venv)…")
        venv.EnvBuilder(with_pip=True, clear=True).create(VENV)
    say("Installing Open Transfer and PyInstaller…")
    run(venv_python(), "-m", "pip", "install", "-q", "--disable-pip-version-check",
        "--upgrade", ".", "pyinstaller>=6.10")  # fmt: skip
    say("Building the executable (takes a minute)…")
    run(venv_python(), "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
        "--distpath", DIST, "--workpath", ROOT / "build" / "pyinstaller", SPEC)  # fmt: skip


def smoke_test() -> None:
    say("Checking that it starts…")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory() as share:
        proc = subprocess.Popen(  # noqa: S603
            [str(EXE), share, "--host", "127.0.0.1", "--port", str(port),
             "--no-browser", "--no-qr"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )  # fmt: skip
        try:
            deadline = time.time() + 60  # first start unpacks the bundle
            while True:
                try:
                    url = f"http://127.0.0.1:{port}/api/health"
                    with urllib.request.urlopen(url, timeout=2) as res:
                        if res.status == 200:
                            break
                except OSError:
                    if proc.poll() is not None or time.time() > deadline:
                        output = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
                        sys.exit(f"The built app did not start:\n{output}")
                    time.sleep(0.5)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    build()
    smoke_test()
    size = EXE.stat().st_size / 1_000_000
    say("")
    say(f"Done: {EXE.relative_to(ROOT)} ({size:.0f} MB)")
    say("Double-click it, or run it from a terminal — options work like the CLI:")
    say(f"  {EXE.relative_to(ROOT)} --help")
    if "--keep-build-files" not in sys.argv:
        shutil.rmtree(ROOT / "build" / "pyinstaller", ignore_errors=True)


if __name__ == "__main__":
    main()
