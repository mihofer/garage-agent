# Garage Agent — Feature Scope

Status: **v1 scope freeze** — grouped into pillars, support systems, and phases.
Items marked (later) are in scope but sequenced after v1.

## Pillars

### P1 — Manual Intelligence
- RAG over workshop manuals (FSM, wiring diagrams, parts catalog, TSBs)
- Hybrid retrieval (FTS5 keyword + vectors, RRF fusion), answers cite manual + page
- `get_page()` verification, verbatim quoting of torque specs / part numbers
- Variant awareness (year/engine code remembered per project)
- **Data extraction:** wiring diagram lookup by circuit name/component,
  fuse/relay maps, vacuum & fluid routing diagrams — indexed as pages with
  component-level metadata so "wipers don't park" → correct diagram, cited
- **Audio diagnosis:**
  - Stage 1 (early): voice notes + spectrogram → VLM heuristic, ranked
    hypotheses with verification steps; confidence stated honestly
  - Stage 2 (later): fine-tuned audio classifier on labeled recordings.
    From day one, every diagnostic voice note is stored with conditions
    (cold/hot, RPM) and — once known — the confirmed cause, building a
    per-engine-family training set as a byproduct of the restoration itself

### P2 — Forum & Web Research
- Web-search tool with source-quality rules (consensus vs. one-off reports,
  confirmed fix vs. theory, always link threads)
- Local archive indexer for 2–3 key forums (scrape solved threads → FTS index;
  forums decay and go behind paywalls)
- **Community give-back:** draft forum posts from problems *you* solved
  (symptom → diagnosis → fix, with your photos), for review before posting

### P3 — Parts Sourcing & Management
- Part lookup → shop + classifieds search (eBay, Kleinanzeigen, specialty
  vendors), price comparison table with links
- **Classifieds watcher:** saved searches with price thresholds and
  back-in-stock alerts (rare/NOS parts appear randomly, vanish in hours)
- **Parts wishlist** with lifecycle status: needed → found → ordered →
  received → installed
- **Order tracking:** what was ordered where, when, arrival status
- **Price history** per watched item (SQLite)
- **Budget tracker:** total spend, per-category and per-job costs,
  budget vs. actual
- **Consumables inventory:** fluids, seals, fasteners on hand; what was
  used where (which oil in which gearbox, which thread locker on which
  fastener) — cross-linked to log entries

### P4 — OBD Telemetry (in-car phase)
- ELM327 USB adapter; python-OBD daemon sampling into SQLite timeseries
- MCP tools: `obd_status`, `obd_snapshot`, `obd_dtc`, `obd_history(pid, window)`
- DTC explanations cross-referenced against manuals
- Skill rules: never clear codes without explicit confirmation (freeze-frame
  evidence), fuel-trim sanity bands
- Session detection: start/stop logging on ignition (PID voltage or manual
  `/drive` command); logs survive for later analysis
- Graceful degradation if car has no OBD port: telemetry tools return
  "not available", agent falls back to manual-only workflow

### P5 — Documentation & Presentation
- Scheduled docu prompts (weekly + after work sessions): "send photos"
- Vision-model captions per photo (part ID, visible state), stored with
  timestamp, job tag, note, EXIF/GPS preserved
- **Before/after pairing** per job, auto-suggested from log entries
- Structured restoration log: `restoration-log.md` + photo store on disk
- **Auto-generated timeline / progress reports:** weekly digest with photos
  → markdown; on demand → PDF / static gallery
- **Shareable build page:** curated public export (chosen entries/photos
  only — the private log stays private)

## Lifecycle & Scheduling

- **Maintenance calendar:** fluid-change intervals after rebuild, recurring
  checks — computed from log entries, delivered via heartbeat
- **Break-in tracking:** camshaft/ring break-in procedures for rebuilt
  engines as guided checklists with OBD cross-checks (RPM limits, temp watch)
- **Seasonal reminders:** winter storage checklist, battery-tender status,
  first-drive-of-spring checks
- **Compliance reminders (light):** insurance/registration validity for test
  drives as checklist items in the weekly digest — no legal advice, just
  don't-forget prompts

## Heartbeat schedule (single Hermes cron config)

| Job | Interval | Action |
|---|---|---|
| Docu reminder | weekly + on session end | request photos, caption & file them |
| Weekly digest | Sunday evening | log summary, open questions, parts status, calendar/compliance items |
| OBD logger | per drive session | sample PIDs → SQLite; flag anomalies post-drive |
| Classifieds watcher | daily | run saved searches, alert on hits |
| Index refresh | monthly | re-ingest new manuals/forum archives |
| Backup | nightly | `~/.hermes`, index, photos, SQLite → restic/rclone target |

## Supporting systems (needed for v1 operation)

- **Project memory:** one workspace per project car — log, parts list,
  torque-spec worksheets, quirks learned
- **Job checklists / torque worksheets:** printable step+torque+special-tools
  sheets generated from the manual for the current job
- **Cost estimate helper:** for outsourcing decisions — manual labor times
  (from FSM time guides where available) × local shop rates vs. DIY,
  including special-tool cost amortization
- **Error learning loop:** record what worked / what didn't per job; feeds
  Hermes' native skill self-improvement so the agent gets better at *this
  specific car* over time
- **Voice hands-free garage mode** (in-car phase): voice query → spoken
  cited answer; large-photo replies for "greasy hands, phone on the workbench"
- **Safety rules layer** (skill-level, non-negotiable): brakes/steering/fuel/
  airbag jobs get hazard notes; special tools named; no invented specs
- **Backups & privacy:** everything local-first; photos/docs never leave
  self-hosted storage unless explicitly shared via the build page
- **Multi-car support** (later): workspace-per-car already the structure;
  UI/selection layer deferred

## Explicitly out of scope for v1

- WhatsApp channel (Telegram first; gateway swap later if ever)
- Real-time conversational voice (hands-free mode is Phase 3; push-to-talk,
  not always-listening)
- Public-facing web service (personal tool; manuals are licensed material)
- Automatic purchasing of parts (search, compare, alert — human confirms)

## Phase plan

1. **Phase 1** — Docker image + Telegram + P1 core (manuals RAG, incl. wiring/
   fuse extraction) + P5 basic (log file, photo captions, weekly heartbeat)
   + audio Stage 1 (spectrogram heuristic) + backups
2. **Phase 2** — P2 (forum research + archive + post drafting), P3 complete
   (watcher, wishlist, budget, inventory)
3. **Phase 3** — P4 (OBD daemon + MCP), job checklists, hands-free voice,
   lifecycle calendar & break-in tracking
4. **Phase 4** — In-car box hardening (offline fallback, autostart),
   build-page generator, audio Stage 2 (classifier on collected data),
   multi-car
