#!/bin/sh
# First-boot seeding for the garage-hermes image.
#
# IMPORTANT ORDERING FACT: the base image's own init runs BEFORE this script
# and seeds its generic ~/.hermes/SOUL.md and a full default config.yaml.
# So "skip if file exists" is wrong for those — we'd never win. Instead:
#   - SOUL.md: force-overwritten on first boot (marker-gated)
#   - config.yaml: our blocks MERGED into whatever exists
#   - a .garage-seeded marker marks first boot done; afterwards the user's
#     edits always win.
set -e

DATA=/opt/data
GARAGE="$DATA/garage"

# 1b. Agent identity (SOUL.md = slot #1 of the system prompt).
#     Force-install on FIRST BOOT ONLY (overwrites the generic starter the
#     base image created moments earlier). Never touched again afterwards.
if [ ! -f "$DATA/.garage-seeded" ]; then
    echo "[seed] installing SOUL.md"
    cp -f /opt/garage/soul.seed.md "$DATA/SOUL.md"
fi

# 1c. Status phrases (KITT catalog) — first boot only, like SOUL.md
if [ ! -f "$DATA/status_phrases.yaml" ]; then
    echo "[seed] installing status_phrases.yaml"
    cp /opt/garage/status_phrases.seed.yaml "$DATA/status_phrases.yaml"
fi

# 1d. KITT scanner GIF into garage assets (build artifact — refresh each boot)
mkdir -p "$GARAGE/assets"
cp -f /opt/garage/assets/kitt_scanner.gif "$GARAGE/assets/kitt_scanner.gif" 2>/dev/null || true

# 2. Skills — three-way update logic:
#      - not installed yet            -> install
#      - shipped version unchanged    -> nothing
#      - locally untouched            -> fast-forward to shipped update
#      - locally modified (agent      -> KEEP local version, park the shipped
#        learning loop / user edits)     update in $DATA/skill-updates/<name>
#                                        for manual reconciliation
#    "Locally modified" is detected against the hash recorded at install time.
mkdir -p "$DATA/skills" "$DATA/.skill-hashes"
for skill_dir in /opt/garage/skills/*/; do
    name=$(basename "$skill_dir")
    live="$DATA/skills/$name/SKILL.md"
    incoming="$skill_dir/SKILL.md"
    hash_file="$DATA/.skill-hashes/$name"

    if [ ! -f "$live" ]; then
        echo "[seed] installing skill: $name"
        cp -r "$skill_dir" "$DATA/skills/$name"
        sha256sum "$incoming" | cut -d' ' -f1 > "$hash_file"
        continue
    fi

    installed_hash=$(cat "$hash_file" 2>/dev/null || echo "")
    live_hash=$(sha256sum "$live" | cut -d' ' -f1)
    incoming_hash=$(sha256sum "$incoming" | cut -d' ' -f1)

    if [ "$live_hash" = "$incoming_hash" ]; then
        echo "$incoming_hash" > "$hash_file"          # already current
        continue
    fi
    if [ "$incoming_hash" = "$installed_hash" ]; then
        continue                                    # no shipped change
    fi
    if [ -z "$installed_hash" ]; then
        # Pre-three-way deployment: no baseline recorded. Adopt the live
        # file as baseline and park the shipped update — never overwrite
        # blindly, but make FUTURE comparisons work.
        echo "$live_hash" > "$hash_file"
    fi
    if [ "$live_hash" = "$installed_hash" ]; then
        echo "[seed] updating skill: $name"
        rm -rf "$DATA/skills/$name"
        cp -r "$skill_dir" "$DATA/skills/$name"
        echo "$incoming_hash" > "$hash_file"
    else
        echo "[seed] CONFLICT: skill '$name' was modified locally — kept yours,"
        echo "[seed]          shipped update parked in $DATA/skill-updates/$name"
        mkdir -p "$DATA/skill-updates"
        rm -rf "$DATA/skill-updates/$name"
        cp -r "$skill_dir" "$DATA/skill-updates/$name"
    fi
done

# 3. Garage data dirs + ledger DB (idempotent schema)
mkdir -p "$GARAGE/knowledge" "$GARAGE/manuals" "$GARAGE/photos" \
         "$GARAGE/audio" "$GARAGE/archive" "$GARAGE/alerts"
if [ ! -f "$GARAGE/ledger.sqlite" ]; then
    echo "[seed] creating ledger.sqlite"
    python3 -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.executescript(open(sys.argv[2]).read())" \
        "$GARAGE/ledger.sqlite" /opt/garage/ledger/schema.sql
fi

# 4. Config merge (first boot only): add our MCP server + guardrails into
#    whatever config exists — Hermes generates a large default config during
#    init and OVERWRITING it would discard required defaults.
if [ ! -f "$DATA/.garage-seeded" ]; then
    echo "[seed] merging garage settings into config.yaml"
    export GARAGE_SEED_DATA="$DATA"
    python3 - <<'PY'
import os, yaml

path = os.path.join(os.environ["GARAGE_SEED_DATA"], "config.yaml")
try:
    cfg = yaml.safe_load(open(path)) or {}
except FileNotFoundError:
    cfg = {}
if not isinstance(cfg, dict):
    cfg = {}

ms = cfg.setdefault("mcp_servers", {})
ms.setdefault("garage-knowledge", {
    "command": "/opt/garage/.venv/bin/python",
    "args": ["-m", "mcp_server.server"],
    "cwd": "/opt/garage",
})
tlg = cfg.setdefault("tool_loop_guardrails", {})
tlg.setdefault("hard_stop_enabled", True)
tlg.setdefault("hard_stop_after",
               {"exact_failure": 5, "idempotent_no_progress": 5})

with open(path, "w") as fh:
    yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)
print("[seed] config merge done")
PY
    touch "$DATA/.garage-seeded"
fi

# 5. Secrets check — never bake keys into images.
if [ ! -f "$DATA/.env" ]; then
    echo "[seed] NOTE: no .env yet — run the setup wizard once:"
    echo "  docker run -it --rm -v ~/.hermes:/opt/data ghcr.io/mihofer/garage-agent:latest setup"
fi

# 6. Standing cron jobs (heartbeats); best-effort
/opt/garage/setup_heartbeats.sh || echo "[seed] WARNING: heartbeat registration failed"

# 7. Hand off to the base image's supervised gateway.
exec hermes gateway run
