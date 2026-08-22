# Garage Agent

A car-restoration companion built on [Hermes Agent](https://github.com/NousResearch/hermes-agent):
answers workshop questions from your indexed service manuals (with citations),
researches forums and classifieds, tracks parts/budget/inventory in a ledger,
documents progress with captioned photos, and reads OBD telemetry (optional,
built in — see below).

- Scope: [SCOPE.md](SCOPE.md) · Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## Layout

```
garage-agent/
├── mcp_server/
│   ├── knowledge.py        # retrieval logic: hybrid search, archive, chunking
│   ├── server.py           # garage-knowledge MCP server (manuals + forum archive)
│   └── obd_server.py       # garage-obd MCP server (reads telemetry.sqlite)
├── ingest/
│   ├── build_index.py      # PDFs -> chunks -> FTS5 + embeddings
│   └── import_archive.py   # JSONL forum threads -> archive index
├── skills/                 # Hermes skills (behavior rules)
│   ├── garage/             # core Q&A rules + safety layer
│   ├── garage-research/    # forum/web research + classifieds sweep rules
│   ├── garage-ledger/      # sqlite3 ledger usage (parts/budget/inventory/calendar)
│   ├── garage-docu/        # photo intake, captions, restoration log, digests
│   ├── garage-checklist/   # printable torque worksheets per job
│   └── garage-audio/       # noise triage via spectrogram + labeled data collection
├── scripts/
│   ├── obd-daemon.py       # OBD sidecar: PID sampling -> telemetry.sqlite (+ --simulate)
│   ├── build_gallery.py    # photo store -> static HTML timeline
│   ├── spectrogram.py      # audio -> spectrogram PNG (ffmpeg)
│   └── backup.sh           # restic or tar.gz nightly backup
├── ledger/schema.sql       # parts/orders/costs/consumables/usage_log/calendar
├── docker/
│   ├── Dockerfile          # official hermes-agent + garage layer (one image)
│   ├── docker-compose.yml  # gateway service; "car" profile adds the OBD daemon
│   ├── seed.sh             # first-boot: config/skills/ledger into ~/.hermes
│   ├── setup_heartbeats.sh # registers standing cron jobs (idempotent)
│   └── config.seed.yaml    # MCP wiring + tool-loop guardrails
└── tests/                  # pytest suite (runs on stdlib only)
```

All generated state lives under `~/.hermes/garage/` (container:
`/opt/data/garage`): `knowledge/`, `ledger.sqlite`, `photos/`, `audio/`,
`archive/`, `alerts/`. That directory + Hermes' own state is your complete
backup target.

## Quick start (Docker)

### Option A: prebuilt image (recommended — this is what a friend does)

CI publishes `ghcr.io/mihofer/garage-agent:latest` on every push to the
default branch. No repo clone needed — two commands.

**1. ONE-TIME setup wizard** (provider keys + Telegram bot token;
create the bot with @BotFather beforehand):

```bash
docker run -it --rm -v ~/.hermes:/opt/data \
  ghcr.io/mihofer/garage-agent:latest setup
```

The wizard walks you through provider, model, and Telegram — have your bot
token and your numeric Telegram user ID ready (it writes both).

**2. Run the gateway:**

```bash
docker run -d \
  --name hermes-garage \
  --restart unless-stopped \
  -v ~/.hermes:/opt/data \
  -e TZ=Europe/Berlin \
  -e HERMES_UID=$(id -u) \
  -e HERMES_GID=$(id -g) \
  ghcr.io/mihofer/garage-agent:latest

# watch first boot (seeding + heartbeat registration):
docker logs -f hermes-garage
```

Updating later is just: stop + remove the container, pull, run again — all
state survives in `~/.hermes`. First boot auto-installs skills, `SOUL.md`,
the ledger, and merges the MCP wiring into Hermes' generated config.

### Option B: build it yourself

```bash
cd docker
docker compose build

# ONE-TIME: interactive wizard — provider keys + Telegram bot token.
docker run -it --rm -v ~/.hermes:/opt/data garage-hermes setup

# Index your manuals (host-side python with pypdf+sentence-transformers,
# or just send PDFs to the bot on Telegram — it copies, OCRs and indexes
# them itself):
python -m ingest.build_index manuals/*.pdf

docker compose up -d                 # supervised always-on gateway
docker compose logs -f gateway       # watch first boot (seeding, heartbeats)
```

Then message the bot on Telegram and try the acceptance test: ask for a
torque spec that's only in your manual — it must cite manual + page.

### In-car / OBD (optional, ships built-in but disabled)

The OBD telemetry stack is included in the image: the MCP server
(`garage-obd`) and the sampling daemon. It's off by default — enable it in
two steps:

1. **Start the daemon** (needs an ELM327 adapter on USB):
   ```bash
   # uncomment garage-obd in ~/.hermes/config.yaml, then:
   docker compose --profile car up -d
   ```
2. The daemon samples PIDs into `garage/telemetry.sqlite`, writes DTC alert
   files, and the agent gains `obd_status` / `obd_snapshot` / `obd_dtc` /
   `obd_history` tools.

Test without a car:
`python3 scripts/obd-daemon.py --simulate --duration 30`.

## Heartbeats (standing cron jobs)

Registered automatically at first boot (`setup_heartbeats.sh`, idempotent):

| Job | Schedule | Mode |
|---|---|---|
| docu-reminder | Mon 08:00 | agent (garage-docu skill) |
| weekly-digest | Sun 18:00 | agent (docu + ledger skills) |
| classifieds-sweep | daily 07:00 | agent (research + ledger skills) |
| backup-nightly | daily 03:00 | script-only (no LLM cost) |

Manage with plain language ("pause the classifieds sweep") — Hermes exposes
a `cronjob` tool. Session-scoped watching uses `/heartbeat every 15m …`.

## Local development & tests

```bash
pip install pytest            # stdlib-only suite
python -m pytest tests/ -q
```

The suite covers chunking, FTS/escape behavior, RRF fusion, archive
round-trip + replace semantics, ledger schema constraints/views/triggers,
gallery generation, JSONL import, spectrogram output, and an end-to-end
simulated OBD session (DB, alerts, MCP queries). Heavy deps
(fastmcp, sentence-transformers, numpy, obd, pypdf) are only needed where used.

## Notes

- Keep manuals private — personal use only; don't expose the bot publicly.
- The agent must cite manual + page for every spec (enforced by skills).
- Never clear OBD codes without explicit confirmation.

## Credits & License

This project is a specialized layer on top of
[Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research
(MIT) — the agent runtime, gateway, skills system, cron scheduler, and the
base container image all come from upstream; this repo adds the automotive
RAG backend, skills, ledger schema, OBD integration, and packaging.

This repository is MIT-licensed (see [LICENSE](LICENSE)). The published GHCR
images are derivative works of the MIT-licensed upstream image and carry the
same license. **Workshop manuals, forum archives, and your project data are
NOT included and remain the property of their respective copyright holders —
users must supply their own legally obtained copies.**
