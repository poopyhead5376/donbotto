from __future__ import annotations

import socket


def auto_detect_rcon_host(default: str = "127.0.0.1") -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        detected = sock.getsockname()[0]
        return detected or default
    except OSError:
        return default
    finally:
        sock.close()
