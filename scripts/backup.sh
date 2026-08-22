#!/bin/sh
# Nightly backup of all garage + hermes state.
# Uses restic when RESTIC_REPOSITORY is configured; otherwise falls back to
# a timestamped tar.gz under GARAGE_BACKUP_DIR (default ~/garage-backups).
#
# Called by the nightly cron heartbeat (no-agent mode).
set -eu

STATE="${HERMES_STATE:-$HOME/.hermes}"
GARAGE="${HERMES_GARAGE:-$HOME/.hermes/garage}"

if [ -n "${RESTIC_REPOSITORY:-}" ]; then
    restic backup "$STATE" "$GARAGE"
    [ -n "${RESTIC_KEEP_DAILY:-}" ] && restic forget --keep-daily "${RESTIC_KEEP_DAILY:-14}" --prune
else
    # Backups MUST land on a volume, not container-local storage.
# Default: under the garage data dir (~/.hermes/garage/backups on the host).
DEST_DEFAULT="${GARAGE_DATA_DIR:-$HOME/.hermes/garage}/backups"
dest="${GARAGE_BACKUP_DIR:-$DEST_DEFAULT}"
    mkdir -p "$dest"
    tar czf "$dest/hermes-$(date +%Y%m%d-%H%M%S).tar.gz" -C "$(dirname "$STATE")" "$(basename "$STATE")"
    # keep the last 14
    ls -1t "$dest"/hermes-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm --
fi
echo "backup ok $(date -Is)"
