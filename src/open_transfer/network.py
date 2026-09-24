"""Helpers for figuring out how other devices can reach this computer."""

from __future__ import annotations

import ipaddress
import socket
import sys
from contextlib import closing


def _is_usable(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.version == 4 and not (addr.is_loopback or addr.is_link_local or addr.is_unspecified)


def primary_ip() -> str | None:
    """The IPv4 address of the interface used for outbound traffic.

    Connecting a UDP socket sends no packets; it only asks the OS which
    interface it *would* route through. This works offline on a LAN too,
    unlike the old ``gethostbyname(gethostname())`` which often returned
    ``127.0.1.1`` on Linux.
    """
    for probe in ("10.255.255.255", "192.168.255.255", "8.8.8.8"):
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
                sock.connect((probe, 1))
                ip: str = sock.getsockname()[0]
        except OSError:
            continue
        if _is_usable(ip):
            return ip
    return None


def lan_ips() -> list[str]:
    """All usable IPv4 addresses of this machine, primary first."""
    found: list[str] = []
    primary = primary_ip()
    if primary:
        found.append(primary)
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        infos = []
    for info in infos:
        ip = str(info[4][0])
        if _is_usable(ip) and ip not in found:
            found.append(ip)
    return found


def hostname() -> str:
    name = socket.gethostname() or "this computer"
    return name.removesuffix(".local").removesuffix(".lan")


def port_is_free(host: str, port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        # Match the server socket (cheroot sets SO_REUSEADDR) so a port that only
        # has TIME_WAIT leftovers from a restart counts as free. Not on Windows,
        # where SO_REUSEADDR would let us "share" a port that is really in use.
        if sys.platform != "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_free_port(host: str, preferred: int, attempts: int = 20) -> int:
    """``preferred`` if it is free, otherwise the next free port above it.

    macOS uses port 5000 for AirPlay Receiver, so falling back matters.
    """
    if preferred == 0:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])
    for port in range(preferred, min(preferred + attempts, 65536)):
        if port_is_free(host, port):
            return port
    raise OSError(f"No free port found between {preferred} and {preferred + attempts - 1}")
