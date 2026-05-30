#!/usr/bin/env bash
# Expose the local API over a public HTTPS URL via Cloudflare Quick Tunnel.
# No Cloudflare account or domain needed. Usage:
#   ./scripts/tunnel.sh            # tunnels http://localhost:8000
#   ./scripts/tunnel.sh 9000       # tunnels http://localhost:9000
set -euo pipefail

PORT="${1:-${CT2_PORT:-8000}}"
BIN="${CLOUDFLARED_BIN:-./cloudflared}"

if ! command -v "$BIN" >/dev/null 2>&1 && [ ! -x "$BIN" ]; then
  case "$(uname -m)" in
    x86_64|amd64) ARCH=amd64 ;;
    aarch64|arm64) ARCH=arm64 ;;
    *) echo "unsupported arch: $(uname -m)" >&2; exit 1 ;;
  esac
  URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}"
  echo "[tunnel] downloading cloudflared ($ARCH)..."
  curl -fsSL "$URL" -o "$BIN"
  chmod +x "$BIN"
fi

echo "[tunnel] exposing http://localhost:${PORT} -- public URL appears below (https://*.trycloudflare.com)"
exec "$BIN" tunnel --no-autoupdate --url "http://localhost:${PORT}"
