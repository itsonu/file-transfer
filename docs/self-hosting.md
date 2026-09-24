# Self-hosting

Open Transfer runs happily on a laptop you start when needed, but also as an always-on service on a home server, NAS or Raspberry Pi.

- [Docker](#docker)
- [systemd service (Linux)](#systemd-service-linux)
- [HTTPS with a reverse proxy](#https-with-a-reverse-proxy)
- [Tips](#tips)

## Docker

The repository includes a `Dockerfile` and `docker-compose.yml`.

```bash
git clone https://github.com/itsonu/file-transfer.git open-transfer
cd open-transfer
docker compose up -d
```

Edit `docker-compose.yml` to set options through environment variables:

```yaml
    environment:
      OPEN_TRANSFER_PUBLIC_URL: "http://192.168.1.24:5000"   # this host's LAN address
      OPEN_TRANSFER_PIN: "4821"
      OPEN_TRANSFER_MAX_SIZE: "8G"
```

**Why `PUBLIC_URL`?** Inside a container the app only sees the container's private address, so it can't know which address your phone should use. `PUBLIC_URL` sets the link and QR code shown in **Add a device**. On Linux you can alternatively use `network_mode: host` (and remove `ports:`) so the app detects the real address itself.

Files are stored in `./uploads` on the host (mounted at `/data`). The container runs as UID 1000; if you mount a folder owned by another user, add `user: "UID:GID"` to the service.

Release images are published to `ghcr.io/itsonu/open-transfer` for `linux/amd64` and `linux/arm64` (Raspberry Pi 4/5).

## systemd service (Linux)

```bash
sudo useradd --system --create-home --home-dir /srv/open-transfer open-transfer
sudo -u open-transfer python3 -m venv /srv/open-transfer/venv
sudo -u open-transfer /srv/open-transfer/venv/bin/pip install git+https://github.com/itsonu/file-transfer
```

`/etc/systemd/system/open-transfer.service`:

```ini
[Unit]
Description=Open Transfer
After=network-online.target
Wants=network-online.target

[Service]
User=open-transfer
ExecStart=/srv/open-transfer/venv/bin/open-transfer /srv/open-transfer/files --no-browser --no-qr --pin 4821
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/srv/open-transfer
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now open-transfer
journalctl -u open-transfer -f      # see who sent what
```

## HTTPS with a reverse proxy

Plain HTTP is fine on a network you trust. For encryption (or a friendly name like `files.home.arpa`), put a reverse proxy in front and tell Open Transfer about it:

```bash
open-transfer /srv/files --host 127.0.0.1 --behind-proxy \
  --public-url https://files.example.com --allow-host files.example.com
```

- `--host 127.0.0.1` — only the proxy can reach the app directly.
- `--behind-proxy` — trust `X-Forwarded-For/Proto/Host` from the proxy (correct client IPs for PIN rate limiting).
- `--public-url` — the address shown in the QR code; `https://` also marks the session cookie `Secure`.
- `--allow-host` — accept that host name (DNS-rebinding protection).

### Caddy

```caddyfile
files.example.com {
    reverse_proxy 127.0.0.1:5000
}
```

Caddy streams request bodies and has no upload size limit by default.

### nginx

```nginx
server {
    listen 443 ssl;
    server_name files.example.com;
    # ssl_certificate ... ;

    client_max_body_size 0;          # no upload limit (Open Transfer enforces --max-size)
    proxy_request_buffering off;     # stream uploads instead of spooling them
    proxy_buffering off;             # stream downloads and ZIPs
    proxy_read_timeout 1h;
    proxy_send_timeout 1h;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

> Exposing Open Transfer to the public internet is not recommended. If you do, always use a strong PIN (letters and digits) and HTTPS, and consider `--receive-only`.

## Tips

- **Health check:** `GET /api/health` returns `{"status": "ok", "version": "…"}` without authentication.
- **Disk space:** uploads are refused with a clear message when they would leave less than 256 MB free.
- **Backups:** the shared folder is just files. `.open-transfer/` holds temporary uploads, the undo trash and the session key; it's safe to exclude.
- **Serving an existing folder read-only:** `open-transfer ~/Photos --read-only`.
