"""``open-transfer`` command-line entry point."""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import secrets
import sys
import threading
import webbrowser
from collections.abc import Sequence
from pathlib import Path

from open_transfer import __version__, network
from open_transfer.config import Config, env, env_bool, parse_size

log = logging.getLogger("open_transfer")


class _Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def __call__(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return self(text, "1")

    def dim(self, text: str) -> str:
        return self(text, "2")

    def blue(self, text: str) -> str:
        return self(text, "1;34")

    def green(self, text: str) -> str:
        return self(text, "32")

    def yellow(self, text: str) -> str:
        return self(text, "33")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="open-transfer",
        description="Share files with any device on your network — just open the link.",
        epilog="Every option can also be set with an OPEN_TRANSFER_<NAME> environment variable.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="folder to share and save uploads to (default: ./uploads, env: OPEN_TRANSFER_DIR)",
    )
    parser.add_argument(
        "-p", "--port", type=int, default=None, help="port to listen on (default: 5000)"
    )
    parser.add_argument(
        "--host", default=None, help="interface to bind (default: 0.0.0.0 = every network)"
    )
    parser.add_argument(
        "--pin",
        nargs="?",
        const="auto",
        default=None,
        help="require a PIN to connect; pass no value to generate a random one",
    )
    parser.add_argument(
        "--max-size",
        default=None,
        help="largest allowed upload, e.g. 500M or 4G (default: no limit)",
    )
    parser.add_argument(
        "--receive-only",
        action="store_true",
        default=None,
        help="visitors can send files but not browse or download",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        default=None,
        help="visitors can download but not upload",
    )
    parser.add_argument(
        "--no-delete", action="store_true", default=None, help="visitors cannot delete files"
    )
    parser.add_argument(
        "--public-url", default=None, help="URL to advertise, e.g. behind Docker or a proxy"
    )
    parser.add_argument(
        "--allow-host",
        action="append",
        default=None,
        metavar="NAME",
        help="extra host name to accept (repeatable; '*' disables the check)",
    )
    parser.add_argument(
        "--behind-proxy",
        action="store_true",
        default=None,
        help="trust X-Forwarded-* headers from a reverse proxy (nginx, Caddy, Traefik)",
    )
    parser.add_argument(
        "--no-browser", action="store_true", default=None, help="don't open a browser"
    )
    parser.add_argument("--no-qr", action="store_true", default=None, help="don't print a QR code")
    parser.add_argument("-v", "--verbose", action="store_true", help="log every request")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _pick(cli_value: object, env_name: str, default: object = None) -> object:
    if cli_value is not None:
        return cli_value
    value = env(env_name)
    return value if value is not None else default


def config_from_args(args: argparse.Namespace) -> Config:
    pin = _pick(args.pin, "PIN")
    if pin == "auto":
        pin = f"{secrets.randbelow(10**4):04d}"
    allowed = args.allow_host or [h for h in (env("ALLOWED_HOSTS") or "").split(",") if h]
    read_only = bool(args.read_only) or env_bool("READ_ONLY")
    return Config(
        storage_dir=Path(str(_pick(args.directory, "DIR", "uploads"))),
        host=str(_pick(args.host, "HOST", "0.0.0.0")),
        port=int(str(_pick(args.port, "PORT", 5000))),
        pin=str(pin) if pin else None,
        max_upload_size=parse_size(str(_pick(args.max_size, "MAX_SIZE", "0"))),
        allow_upload=not read_only,
        allow_delete=not (read_only or bool(args.no_delete) or env_bool("NO_DELETE")),
        allow_browse=not (bool(args.receive_only) or env_bool("RECEIVE_ONLY")),
        public_url=_pick(args.public_url, "PUBLIC_URL"),  # type: ignore[arg-type]
        allowed_hosts=tuple(allowed),
        trust_proxy=bool(args.behind_proxy) or env_bool("BEHIND_PROXY"),
    )


def _print_banner(config: Config, port: int, style: _Style, show_qr: bool) -> str:
    ips = network.lan_ips()
    share = config.public_url or (f"http://{ips[0]}:{port}" if ips else f"http://localhost:{port}")
    out = sys.stdout
    out.write("\n  " + style.blue("Open Transfer") + style.dim(f"  v{__version__}") + "\n\n")
    out.write(f"  {style.dim('On this computer')}   http://localhost:{port}\n")
    if config.public_url:
        out.write(f"  {style.dim('Public address')}     {style.bold(config.public_url)}\n")
    for ip in ips:
        out.write(f"  {style.dim('On your network')}    {style.bold(f'http://{ip}:{port}')}\n")
    if not ips and not config.public_url:
        out.write(style.yellow("  No network connection found — only this computer can connect.\n"))
    if config.pin:
        out.write(f"  {style.dim('PIN')}                {style.bold(config.pin)}\n")
    out.write(f"  {style.dim('Saving files to')}    {config.storage_dir}\n")
    if show_qr and (ips or config.public_url):
        qr_url = share + (f"/?pin={config.pin}" if config.pin else "")
        try:
            import segno

            out.write("\n  " + style.dim("Scan with your phone's camera:") + "\n\n")
            segno.make(qr_url, error="l").terminal(out=out, compact=True, border=2)
        except (UnicodeEncodeError, OSError):
            # Some Windows consoles can't draw block characters; the URL above is enough.
            log.debug("could not print the QR code", exc_info=True)
    out.write("\n  " + style.dim("Press Ctrl+C to stop sharing.") + "\n\n")
    out.flush()
    return share


def _configure_logging(verbose: bool, style: _Style) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(style.dim("  %(asctime)s") + "  %(message)s", "%H:%M:%S")
    )
    root = logging.getLogger("open_transfer")
    root.handlers[:] = [handler]
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.propagate = False


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    style = _Style(sys.stdout.isatty() and "NO_COLOR" not in os.environ)
    _configure_logging(args.verbose, style)

    try:
        config = config_from_args(args)
    except ValueError as exc:
        print(f"open-transfer: error: {exc}", file=sys.stderr)
        return 2

    try:
        port = network.find_free_port(config.host, config.port)
    except OSError as exc:
        print(f"open-transfer: error: {exc}", file=sys.stderr)
        return 1
    if port != config.port and config.port:
        print(style.yellow(f"\n  Port {config.port} is busy, using {port} instead."))

    from cheroot import wsgi

    from open_transfer.app import create_app

    try:
        app = create_app(config)
    except OSError as exc:
        print(f"open-transfer: error: cannot use {config.storage_dir}: {exc}", file=sys.stderr)
        return 1
    app.config["OT_PORT"] = port

    server = wsgi.Server(
        (config.host, port),
        app,
        numthreads=config.threads,
        server_name=f"open-transfer/{__version__}",
        timeout=60,
    )
    server.max_request_body_size = 0  # limits are enforced by the app while streaming

    try:
        server.prepare()
    except OSError as exc:
        print(f"open-transfer: error: could not listen on port {port}: {exc}", file=sys.stderr)
        return 1

    _print_banner(config, port, style, show_qr=not (args.no_qr or env_bool("NO_QR")))
    if not (args.no_browser or env_bool("NO_BROWSER")):
        threading.Timer(0.4, webbrowser.open, args=(f"http://localhost:{port}",)).start()

    with contextlib.suppress(KeyboardInterrupt):  # Ctrl+C is the normal way to stop
        try:
            server.serve()
        finally:
            server.stop()
    print("\n  " + style.dim("Stopped sharing. Your files are still in ") + str(config.storage_dir))
    return 0
