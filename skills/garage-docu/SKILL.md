---
name: garage-docu
description: Photo documentation workflow and heartbeat behavior — captioning incoming photos, filing them, maintaining the restoration log, and generating progress reports/galleries.
version: 0.1.0
author: owner
license: MIT
metadata:
  hermes:
    tags: [Automotive, Documentation]
---

# Documentation & Progress

## Photo intake (whenever the owner sends photos)

1. Save each photo to `~/.hermes/garage/photos/YYYY/YYYY-MM-DD_<job-slug>/`
   keeping the original filename (EXIF stays intact — never re-encode).
2. Look at each photo (vision) and write a sidecar JSON next to it:
   `IMG_1234.jpg.json` (image filename + `.json`) → `{"caption": "<what it shows,
   part IDs if identifiable>", "job": "<job name>", "note":
   "<optional context from the owner>"}`.
3. If the photo shows damage/wear worth remembering, add a line to
   `~/.hermes/garage/restoration-log.md` under the current date with the
   relative photo path.

## Restoration log

`~/.hermes/garage/restoration-log.md` — append-only by date:

```markdown
## 2025-11-08 — brake overhaul
- Removed front calipers; pistons heavily pitted (see photos/2025/2025-11-08_brakes/IMG_1.jpg)
- Replaced: pads, discs; torqued bracket to 120 Nm (FSM Br-14)
- Parts: #42, #43 installed
```

Facts to always log: date, job, what was done, torque values applied (+manual
page), parts installed (ledger ids), anomalies found.

## Heartbeats

**Docu reminder (cron, weekly + on request)** — prompt shape:
"Ask the owner for photos/notes of this week's progress; caption and file
whatever arrives; update the log; confirm what's still undocumented."
Keep it to one short question, not a form. If nothing happened, say so and
stop (don't nag).

**Weekly digest (cron, Sunday evening)** — compose from:
restoration-log.md (this week), ledger reports (budget_by_category,
open_parts, late orders, calendar due), unhandled OBD alerts, and open
questions. End with: top 3 suggested next steps.

## Reports & gallery

- `python /opt/garage/scripts/build_gallery.py` regenerates the HTML
  timeline from the photo store — run it after filing photos, and mention
  the path to the owner.
- Progress report (on request): summarize log by month with photos, output
  as markdown; for sharing, produce the curated variant only from entries
  the owner approves.
