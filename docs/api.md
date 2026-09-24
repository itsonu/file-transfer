# HTTP API

Everything the web app does is available over a small JSON API, so you can script Open Transfer with `curl`, shortcuts or other tools.

- Base URL: the address printed on start, e.g. `http://192.168.1.24:5000`.
- Errors are JSON: `{"error": {"code": "too_large", "message": "File is larger than the 500 MB limit."}}` with a matching HTTP status.
- Browser requests that change data must be same-origin (CSRF protection). Non-browser clients like `curl` are unaffected.

## Authentication (PIN mode)

When started with `--pin`, every endpoint except `/api/health`, `/api/info` and `/api/auth` requires a session cookie.

```bash
curl -c jar -H 'Content-Type: application/json' -d '{"pin":"4821"}' http://HOST:5000/api/auth
curl -b jar http://HOST:5000/api/files
```

| Status | Meaning |
| ------ | ------- |
| `401 pin_required` | No valid session |
| `401 wrong_pin` | Wrong PIN |
| `429 too_many_attempts` | 5 wrong PINs in a minute; see `Retry-After` |

## Endpoints

### `GET /api/health`
`{"status": "ok", "version": "2.0.0"}` — for monitoring. Never requires a PIN.

### `GET /api/info`
Server name, version, auth state and — once authenticated — share URLs, permissions and limits.

```json
{
  "app": "Open Transfer", "version": "2.0.0", "device": "studio-mac",
  "auth": {"required": false, "authenticated": true, "numeric": false},
  "share_url": "http://192.168.1.24:5000",
  "urls": ["http://192.168.1.24:5000"],
  "permissions": {"upload": true, "browse": true, "delete": true},
  "limits": {"max_upload_size": 0},
  "storage": {"free": 182736451584},
  "pin": null
}
```

### `GET /api/files`
Newest first. Supports `If-None-Match` → `304 Not Modified`.

```json
{
  "files": [
    {"name": "Q3 Report.pdf", "size": 2412000, "modified": 1790276747.18,
     "mime": "application/pdf", "kind": "document"}
  ],
  "total_size": 2412000,
  "storage": {"free": 182736451584}
}
```

`kind` is one of `image video audio archive document spreadsheet presentation code app other`.

### `POST /api/files` — upload
**Raw body (recommended, streams any size):**

```bash
curl -T "Holiday video.mp4" -X POST \
  -H "X-Filename: $(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' 'Holiday video.mp4')" \
  http://HOST:5000/api/files
```

The file name goes in `X-Filename` (percent-encoded UTF-8) or a `?name=` query parameter.

**Multipart (one or more files):**

```bash
curl -F file=@photo.jpg -F file=@notes.txt http://HOST:5000/api/files
```

`/transfer` is kept as an alias for older scripts. Returns `201` with the saved files — names may get a ` (1)` suffix if taken:

```json
{"files": [{"name": "photo (1).jpg", "size": 48213, "modified": 1790276747.2, "mime": "image/jpeg", "kind": "image"}]}
```

Errors: `400 invalid_name`, `400 incomplete_upload`, `403 upload_disabled`, `413 too_large`, `507 insufficient_storage`.

### `GET /files/<name>` — download
Always an attachment, with `Range` support for resuming (`curl -C - -O`). `?inline=1` displays images, audio and video in the browser. `/download/<name>` is a legacy alias.

### `DELETE /api/files/<name>`
Moves the file to the trash: `{"undo_token": "…", "undo_seconds": 30}`. `403 delete_disabled` if turned off.

### `POST /api/trash/<token>/restore`
Restores a deleted file within `undo_seconds`: `{"file": {…}}`, or `404`.

### `GET /api/archive`
Streams a ZIP of all files, or only those given as `?name=a.txt&name=b.jpg`.

### `GET /api/qr.svg`
QR code (SVG) for the share URL; includes the PIN when one is set.

### `POST /api/logout`
Clears the session.
