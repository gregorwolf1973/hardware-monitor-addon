#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting Hardware Monitor..."

export PORT=8200

bashio::log.info "Web GUI starting on port ${PORT}..."
exec python3 /app/app.py
