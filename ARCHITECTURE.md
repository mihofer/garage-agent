# Garage Agent — Architecture

Status: draft, reflects decisions taken in scope discussion (see DECISIONS).
Companion to [SCOPE.md](SCOPE.md).

## Component inventory

Exactly one custom long-lived component in v1:

| Component | Type | Ships in |
|---|---|---|
| `garage-knowledge` MCP server | stdio MCP (child of Hermes) | baked into image |
| Manual/forum archive indexes | SQLite FTS5 + vectors on disk | mounted volume |
| Ledger (parts/budget/inventory/calendar) | SQLite file + skill (agent runs `sqlite3`) | schema in skill, DB on volume |
| Photo store | plain filesystem, EXIF preserved | mounted volume |
| Behavior skills (garage, research rules, docu, checklists…) | SKILL.md files | seeded into `~/.hermes/skills` |
| Heartbeats (docu, digest, watcher, backups) | Hermes cron → agent itself | seeded config |
| OBD daemon + MCP | sidecar + stdio MCP (**Phase 3**) | own container |

## Runtime topology (v1)

Single container. The compose file is the architecture diagram:

```yaml
services:
  gateway:
    build: docker/Dockerfile          # official hermes-agent + our layer
    volumes:
      - ~/.hermes:/opt/data           # config, sessions, skills, .env
      - ./garage-data:/opt/data/garage  # everything WE own, one place:
                                        #   knowledge/  index.sqlite, vectors.npz
                                        #   ledger.sqlite
                                        #   photos/YYYY/MM/...
                                        #   archive/    forum scrapes
```

Everything we generate lives under `/opt/data/garage` so a single host
directory (`~/.hermes/garage`) is the complete backup target alongside
Hermes' own state.

## Data flow

```
Telegram ⇄ Hermes gateway ⇄ agent core
             │
             ├─ tools/web_search      → live forum/shop research (skill-guided)
             ├─ mcp garage-knowledge  → manual/archive retrieval (citations)
             ├─ terminal: sqlite3     → ledger reads/writes (skill-defined schema)
             ├─ terminal: ffmpeg/file → spectrograms, photo filing, gallery builds
             └─ cron                  → heartbeats wake the AGENT (not scripts):
                                        docu reminders, weekly digest,
                                        classifieds sweep, backup trigger
```

Heartbeats drive the agent, not scripts: each scheduled job is a prompt.
The agent then uses its ordinary tools. One execution model, nothing new
to monitor.

## Decisions (with revisit triggers)

| # | Decision | Revisit when |
|---|---|---|
| D1 | Ledger = skill + sqlite3 CLI, not MCP | agent repeatedly writes malformed SQL or loses records → promote to MCP (`garage-ledger`) with typed tools |
| D2 | Classifieds watch = agent cron heartbeat | token cost per sweep too high, or sites need deterministic parsing → extract scraper into a sidecar container writing hits to ledger.sqlite |
| D3 | ONE MCP server (manuals + forum archive) | failure modes interfere (reindex blocks lookups) or index count grows ≥3 → split per index |
| D4 | Photos = plain filesystem + EXIF | gallery build slow / duplicates annoy → hash-named content-addressed layout |
| D5 | Single image; OBD will be 2nd container | — (Phase 3 adds it as compose service, same image, different command) |
| D6 | Sidecars (when they exist) share state ONLY via garage-data volumes; no HTTP between containers | never unless a real need appears |

## Packaging

- `docker/Dockerfile`: FROM official hermes-agent → bake MCP server + venv +
  seed files; CMD seeds first boot then runs supervised gateway
- Skills & seed config: versioned in repo, copied into `~/.hermes` first boot
  only (edits survive upgrades)
- Index rebuilds: batch job against mounted volume, no image involvement
- Backup: restic/rclone over `~/.hermes` nightly (heartbeat-triggered)

## In-car delta (Phase 3/4 preview)

Same image, plus:
- `obd` compose service (same image, `obd-daemon` command, USB device passthrough)
- TTS/STT providers configured; hands-free push-to-talk skill
- offline fallback profile (local model via Ollama on the box)
- ignition-triggered session logging (voltage sense or `/drive` command)
