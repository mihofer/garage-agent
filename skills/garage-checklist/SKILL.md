---
name: garage-checklist
description: Generate printable job checklists / torque worksheets from the manuals — steps, torque values with citations, special tools, hazards.
version: 0.1.0
author: owner
license: MIT
metadata:
  hermes:
    tags: [Automotive, Workshop]
---

# Job Checklist / Torque Worksheet

When the owner is about to start a job ("I'm doing the front brakes
tomorrow"):

1. **Retrieve the procedure**: `search_manuals` for each phase of the job
   (removal, inspection, installation, torque, break-in). Use `get_page` to
   verify every number you will print.
2. **Produce a worksheet** with these sections:
   - **Tools & parts** — special tools called out by the manual (exact names;
     never suggest improvised substitutes for safety tools), consumables,
     ledger part numbers if known
   - **Steps** — numbered, short, in manual order; each step that has a
     spec shows it verbatim with `(FSM <manual> p.<page>)`
   - **Torque table** — every fastener: thread, value+unit verbatim, stage/
     angle if specified, page citation
   - **Hazards** — job-specific warnings (residual fuel pressure, spring
     compression, brake fluid, airbag connectors…)
   - **After the job** — checks, break-in notes, what to log
3. Output as markdown the owner can print. Offer to add a calendar follow-up
   (e.g. retorque after 100 km) via the ledger.
4. If the manual doesn't cover a step, mark it `⚠ not in FSM — verify` rather
   than filling from general knowledge.
