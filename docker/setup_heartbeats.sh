#!/bin/sh
# Register the standing cron jobs (heartbeats). Idempotent: skips jobs whose
# name already exists in `hermes cron list`. Best-effort — failures are
# logged but never block the gateway from starting.
set -u

GARAGE_SKILLS="/opt/garage/skills"
DATA=/opt/data

have_job() {
    hermes cron list 2>/dev/null | grep -q "$1"
}

create() {
    name="$1"; schedule="$2"; prompt="$3"; shift 3
    if have_job "$name"; then
        echo "[heartbeats] '$name' already registered"
        return 0
    fi
    if hermes cron create "$schedule" "$prompt" --name "$name" "$@" 2>&1; then
        echo "[heartbeats] registered '$name'"
    else
        echo "[heartbeats] WARNING: could not register '$name' — register manually:"
        echo "  hermes cron create \"$schedule\" \"$prompt\" --name $name $*"
    fi
}

create docu-reminder "0 8 * * 1" \
  "Weekly docu check: ask the owner for photos/notes of this week's workshop progress (one short question). Caption and file whatever arrives per the garage-docu skill; update the restoration log; mention anything still undocumented." \
  --skill garage-docu

create weekly-digest "0 18 * * 0" \
  "Compose the weekly digest per the garage-docu skill: this week's log entries, budget_by_category and open_parts from the ledger, late orders, calendar due items, unhandled OBD alerts; end with top-3 suggested next steps." \
  --skill garage-docu --skill garage-ledger

create classifieds-sweep "0 7 * * *" \
  "Daily classifieds sweep per the garage-research skill: run saved searches for parts with status='needed', check eBay/Kleinanzeigen/specialty vendors, record meaningful hits as status='found' with url+price, report links to the owner. Never contact sellers." \
  --skill garage-research --skill garage-ledger

# Backup is a pure script — run in cron's no-agent mode (zero LLM cost).
# If your Hermes version names the flag differently, check `hermes cron create --help`.
# Backup is a pure script — run in cron's no-agent mode (zero LLM cost).
# Contract: --script must point under ~/.hermes/scripts/, so we install it
# there first. Re-synced on every boot so image updates propagate.
mkdir -p "$DATA/scripts"
cp -f /opt/garage/scripts/backup.sh "$DATA/scripts/garage-backup.sh"
if have_job "backup-nightly"; then
    echo "[heartbeats] 'backup-nightly' already registered"
elif hermes cron create "0 3 * * *" --name backup-nightly \
        --script garage-backup.sh --no-agent 2>&1; then
    echo "[heartbeats] registered 'backup-nightly' (no-agent)"
else
    echo "[heartbeats] WARNING: could not register 'backup-nightly'"
fi

echo "[heartbeats] done"
