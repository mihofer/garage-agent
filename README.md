# Garage Agent

A car-restoration companion built on [Hermes Agent](https://github.com/NousResearch/hermes-agent):
answers workshop questions from your indexed service manuals (with citations),
researches forums and classifieds, tracks parts/budget/inventory in a ledger,
documents progress with captioned photos, and (Phase 3) reads OBD telemetry.

- Scope: [SCOPE.md](SCOPE.md) · Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## Layout

```
garage-agent/
├── mcp_server/
│   ├── knowledge.py        # retrieval logic: hybrid search, archive, chunking
│   ├── server.py           # garage-knowledge MCP server (manuals + forum archive)
│   └── obd_server.py       # garage-obd MCP server (Phase 3, reads telemetry.sqlite)
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
│   ├── obd-daemon.py       # Phase 3 sidecar: PID sampling -> telemetry.sqlite (+ --simulate)
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

### Option A: prebuilt image (no build needed)

CI publishes images to GHCR on every push to `main`:

```bash
# in docker/docker-compose.yml, comment out `build:` and set:
#   image: ghcr.io/<repo-owner>/garage-agent:latest
docker pull ghcr.io/<repo-owner>/garage-agent:latest
docker run -it --rm -v ~/.hermes:/opt/data \
  ghcr.io/<repo-owner>/garage-agent:latest setup    # once: keys + Telegram token
```

### Option B: build it yourself

```bash
cd docker
docker compose build

# ONE-TIME: interactive wizard — provider keys + Telegram bot token.
docker run -it --rm -v ~/.hermes:/opt/data garage-hermes setup

# Index your manuals (host-side python with pypdf+sentence-transformers,
# or inside a throwaway container):
python -m ingest.build_index manuals/*.pdf

docker compose up -d                 # supervised always-on gateway
docker compose logs -f gateway       # watch first boot (seeding, heartbeats)
```

Then message the bot on Telegram and try the acceptance test: ask for a
torque spec that's only in your manual — it must cite manual + page.

### In-car / OBD (Phase 3)

```bash
# uncomment garage-obd in ~/.hermes/config.yaml, then:
docker compose --profile car up -d
```

The `obd` service shares the same image, gets `/dev/ttyUSB0`, samples PIDs
into `garage/telemetry.sqlite`, and writes DTC alert files. Test without a
car: `python3 scripts/obd-daemon.py --simulate --duration 30`.

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
