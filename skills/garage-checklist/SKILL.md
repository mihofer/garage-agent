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
   - **TOOLS REQUIRED** — every tool needed: socket sizes, torque wrench,
     special tools called out by the manual (exact names; never suggest
     improvised substitutes for safety tools), consumables, ledger part
     numbers if known
   - **PARTS REQUIRED** — every part: OEM part number + manufacturer, the
     aftermarket equivalent where known, and exact consumable specs
     (e.g. `H7 55W`, `5W-30`, `SAE 90`); note variant differences if the
     car-profile differs from the manual's market
   - **ESTIMATED TIME** — realistic time for a competent home mechanic on
     this specific car
   - **Steps** — numbered, short, in manual order; each step that has a
     spec shows it verbatim with `(FSM <manual> p.<page>)`. Fasteners are
     always located precisely ("2 screws at the top corners of the trim
     panel", "1 bolt behind the glove box door hinge") — never just
     "remove the screws". High-risk steps carry their own
     `⚠ ATTENTION: [warning]` line immediately BEFORE the step.
   - **Torque table** — every fastener: thread, value+unit verbatim, stage/
     angle if specified, page citation
   - **Hazards** — job-specific warnings (residual fuel pressure, spring
     compression, brake fluid, airbag connectors…); electrical jobs start
     with the battery-disconnect pre-flight line (see garage skill)
   - **After the job** — checks, break-in notes, what to log
3. **WHILE YOU'RE IN THERE:** — always end every job with this section.
   Think about what else is accessible, exposed, or worth inspecting given
   what has been removed or disassembled. List additional jobs,
   inspections, or replacements worth doing at the same time — because it
   saves labour, prevents a future failure, or because the part is a known
   failure item at this age/mileage. Be specific to this car, not generic.
4. Output as markdown the owner can print. Offer to add a calendar follow-up
   (e.g. retorque after 100 km) via the ledger.
5. If the manual doesn't cover a step, mark it `⚠ not in FSM — verify` rather
   than filling from general knowledge.
