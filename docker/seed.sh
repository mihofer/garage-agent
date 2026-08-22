#!/bin/sh
# First-boot seeding for the garage-hermes image.
# Copies baked-in defaults into /opt/data (the ~/.hermes volume) ONLY where
# files don't exist yet — safe on every start; user edits survive upgrades.
set -e

DATA=/opt/data
GARAGE="$DATA/garage"

# 1. Hermes config (non-secret; secrets live in $DATA/.env via setup wizard)
if [ ! -f "$DATA/config.yaml" ]; then
    echo "[seed] installing default config.yaml"
    cp /opt/garage/config.seed.yaml "$DATA/config.yaml"
fi

# 1b. Agent identity (SOUL.md = slot #1 of the system prompt). Hermes also
#     seeds a starter if absent and never overwrites — same rule for us:
#     first boot only, your edits always win.
if [ ! -f "$DATA/SOUL.md" ]; then
    echo "[seed] installing SOUL.md"
    cp /opt/garage/soul.seed.md "$DATA/SOUL.md"
fi

# 2. Skills
mkdir -p "$DATA/skills"
for skill_dir in /opt/garage/skills/*/; do
    name=$(basename "$skill_dir")
    if [ ! -d "$DATA/skills/$name" ]; then
        echo "[seed] installing skill: $name"
        cp -r "$skill_dir" "$DATA/skills/$name"
    fi
done

# 3. Garage data dirs + ledger DB (idempotent schema)
mkdir -p "$GARAGE/knowledge" "$GARAGE/photos" "$GARAGE/audio" \
         "$GARAGE/archive" "$GARAGE/alerts"
if [ ! -f "$GARAGE/ledger.sqlite" ]; then
    echo "[seed] creating ledger.sqlite"
    python3 -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.executescript(open(sys.argv[2]).read())" \
        "$GARAGE/ledger.sqlite" /opt/garage/ledger/schema.sql
fi

# 4. Secrets check — never bake keys into images.
if [ ! -f "$DATA/.env" ]; then
    echo "[seed] NOTE: no .env yet — run the setup wizard once:"
    echo "  docker run -it --rm -v ~/.hermes:/opt/data garage-hermes setup"
fi

# 5. Standing cron jobs (heartbeats); best-effort
/opt/garage/setup_heartbeats.sh || echo "[seed] WARNING: heartbeat registration failed"

# 6. Hand off to the base image's supervised gateway.
exec hermes gateway run
