# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.0.0] — 2026-09-24

The project is now **Open Transfer**: a rewrite of the original Flask "File Transfer" app into a complete, installable product. Existing URLs (`/upload`, `/downloads`, `/download/<name>`, `POST /transfer`) keep working.

### Added
- Single-page interface: drag & drop anywhere, paste files, multi-file queue with live speed/ETA, cancel and retry, file list with thumbnails, search, **Download all** as ZIP, delete with **Undo**, automatic dark mode, phone-friendly layout, accessibility (keyboard, labels, live regions, reduced motion).
- **Add a device** sheet with QR code, copyable link and other addresses; QR code in the terminal.
- Live updates across devices via `ETag` polling, with offline/reconnecting states.
- Optional **PIN** (`--pin`, auto-generated if no value) with rate limiting; the QR code signs people in.
- `--receive-only`, `--read-only`, `--no-delete`, `--max-size`, `--public-url`, `--allow-host`, `--behind-proxy`, `--verbose`; every option also as an `OPEN_TRANSFER_*` environment variable.
- JSON API (`/api/files`, `/api/info`, `/api/archive`, …) documented in `docs/api.md`.
- One-command runners (`run.sh`, `run.ps1`), `Makefile`, Dockerfile + Compose, PyInstaller spec, CI (Linux/macOS/Windows, Python 3.10–3.14, browser tests, Docker smoke test), CodeQL, pip-audit, Dependabot, release workflow.
- Test suite: storage, API, security and CLI unit tests plus Playwright end-to-end tests.
- Documentation: README, architecture, self-hosting, API, contributing, security policy, code of conduct.

### Changed
- Uploads stream to disk (constant memory, no temp copy) via the cheroot server, and are published atomically; duplicate names get ` (1)` suffixes instead of overwriting.
- LAN address detection now finds the real interface instead of `127.0.1.1`; the next free port is used if 5000 is busy (macOS AirPlay).
- New icon and visual design; manifest fixed (icons were nested incorrectly).

### Fixed
- Path traversal in uploads and downloads (`../` in file names).
- Files with the same name silently overwrote each other.
- `/shutdown` crashed (`threading.join` does not exist).
- The service worker cached the home page forever; it has been removed.

### Security
- CSRF and DNS-rebinding protection, strict Content-Security-Policy and hardening headers, sandboxed downloads, hidden files and symlinks are never served.

### Removed
- Unrelated packet-sniffing and network-scanning scripts (`get.py`, `get2.py`, `scan.py`), the duplicate `backup.py`, the unused Tkinter import and IDE settings.
