#!/usr/bin/env python
"""Start the API server + a Cloudflare Quick Tunnel and print the public URL.

Made for Colab (where you can't bind a public port). Run it from a cell:

    !python -m scripts.colab_serve

It launches `python run.py`, downloads `cloudflared` if missing, opens a quick
tunnel, parses the `https://*.trycloudflare.com` URL from cloudflared's logs and
prints it. Point your laptop / backend at `<url>/v1`.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import time
import urllib.request

PORT = int(os.environ.get("CT2_PORT", "8000"))
CF_BIN = os.environ.get("CLOUDFLARED_BIN", "./cloudflared")
URL_RE = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com")


def ensure_cloudflared() -> str:
    if os.path.exists(CF_BIN) and os.access(CF_BIN, os.X_OK):
        return CF_BIN
    arch = {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine(), "amd64"
    )
    url = (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        f"cloudflared-linux-{arch}"
    )
    print(f"[colab_serve] downloading cloudflared ({arch})...")
    urllib.request.urlretrieve(url, CF_BIN)
    os.chmod(CF_BIN, 0o755)
    return CF_BIN


def main() -> int:
    server = subprocess.Popen([sys.executable, "run.py"])
    print(f"[colab_serve] API starting on :{PORT} (pid {server.pid})")

    cf = ensure_cloudflared()
    tunnel = subprocess.Popen(
        [cf, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    public_url = None
    try:
        for line in tunnel.stdout:  # type: ignore[union-attr]
            print(line, end="")
            m = URL_RE.search(line)
            if m and not public_url:
                public_url = m.group(0)
                print("\n" + "=" * 64)
                print(f"  Translation Lab: {public_url}/translation-lab")
                print(f"  PUBLIC API:  {public_url}/v1")
                print(f"  health:      {public_url}/admin/status")
                print("=" * 64 + "\n", flush=True)
        tunnel.wait()
    except KeyboardInterrupt:
        pass
    finally:
        tunnel.terminate()
        server.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
