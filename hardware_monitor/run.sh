#!/bin/sh
set -e

echo "[hardware-monitor] starting..."
export PORT=8200
exec python3 /app/app.py
