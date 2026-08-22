---
name: garage-ledger
description: How to use the garage ledger (parts wishlist, orders, budget, consumables, calendar) via sqlite3 — schema, usage rules, and integrity checks.
version: 0.1.0
author: owner
license: MIT
metadata:
  hermes:
    tags: [Automotive, Tracking, Budget]
---

# Garage Ledger

The ledger is one SQLite file: `$GARAGE_DATA_DIR/ledger.sqlite`
(set in the container to `/opt/data/garage`; locally `~/.hermes/garage`).
You access it with the `terminal` tool: `sqlite3 -header -column $GARAGE_DATA_DIR/ledger.sqlite`.
Schema is in the repo at `ledger/schema.sql` (also applied at first boot).

## Schema summary

- `parts` — wishlist: name, part_number, source, url, price, status
  (needed → found → ordered → received → installed), needed_for
- `orders` — orders: part_id, shop, order_ref, total, status, eta
- `costs` — every expense: date, category (parts|tools|fluids|consumables|
  services|other), description, amount (+spent/−refund), job
- `consumables` — inventory: kind, name, spec, qty_on_hand, unit
- `usage_log` — what went where: consumable_id, date, job, quantity, note
- `calendar` — maintenance items: title, due_date, recurrence, done
- Views: `budget_by_category`, `budget_by_job`, `open_parts`

## Hard rules

1. **Wrap every write in a transaction** and verify immediately:
   ```sh
   sqlite3 -bail ledger.sqlite "BEGIN; INSERT INTO parts(name) VALUES('…'); COMMIT;"
   sqlite3 ledger.sqlite "SELECT last_insert_rowid(), * FROM parts ORDER BY id DESC LIMIT 1;"
   ```
2. **Never DELETE financial rows.** Cancel with status changes; mistakes get
   a negative `costs` entry with a description referencing the mistake.
3. **Every part purchase becomes a `costs` row too** (category=parts,
   job=the work it belongs to). The budget views only know `costs`.
4. **Consumable usage**: when the owner reports using fluid/sealant/etc.,
   insert `usage_log` AND decrement `consumables.qty_on_hand` in the same
   transaction. Warn when qty_on_hand drops below a sensible reorder point.
5. **Currency**: default EUR; never mix currencies in one SUM — say so if
   data has mixed currencies.
6. Readable output: use `sqlite3 -header -column` for reports.

## Standard reports (on request or in the weekly digest)

- Budget: `SELECT * FROM budget_by_category;` and `budget_by_job`
- Open parts: `SELECT * FROM open_parts;`
- Late orders: `SELECT * FROM orders WHERE status IN ('placed','shipped') AND eta < date('now');`
- Calendar due: `SELECT * FROM calendar WHERE done=0 AND due_date <= date('now','+14 days') ORDER BY due_date;`

## Maintenance calendar & seasonal

- After a rebuild job, offer to add calendar rows for follow-ups
  (oil change after 1000 km, retorque heads, cam break-in checkpoints).
- In autumn, propose the winter-storage checklist; in spring, first-drive
  checks. Add them as calendar rows rather than one-off reminders.
