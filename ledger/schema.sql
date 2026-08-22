-- Garage ledger schema. Applied idempotently by seed/ledger_init.
-- The agent uses this via `sqlite3 ~/.hermes/garage/ledger.sqlite`
-- (see skills/ledger/SKILL.md for usage rules).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    part_number TEXT DEFAULT '',
    source TEXT DEFAULT '',            -- shop / classifieds / swap meet
    url TEXT DEFAULT '',
    price REAL,                        -- asking or expected price
    currency TEXT DEFAULT 'EUR',
    status TEXT NOT NULL DEFAULT 'needed'
        CHECK (status IN ('needed','found','ordered','received','installed','cancelled')),
    needed_for TEXT DEFAULT '',        -- job / system reference
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    part_id INTEGER REFERENCES parts(id),
    shop TEXT NOT NULL,
    order_ref TEXT DEFAULT '',
    order_date TEXT NOT NULL DEFAULT (date('now')),
    total REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    status TEXT NOT NULL DEFAULT 'placed'
        CHECK (status IN ('placed','shipped','delivered','returned','cancelled')),
    eta TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL DEFAULT (date('now')),
    category TEXT NOT NULL,            -- parts | tools | fluids | consumables | services | other
    description TEXT NOT NULL,
    amount REAL NOT NULL,              -- positive = spent; negative = refund/resale
    currency TEXT DEFAULT 'EUR',
    job TEXT DEFAULT ''                -- free-text project phase, e.g. 'engine rebuild'
);

CREATE TABLE IF NOT EXISTS consumables (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,                -- fluid | sealant | fastener | filter | other
    name TEXT NOT NULL,
    spec TEXT DEFAULT '',              -- e.g. 'GL-4 75W-90', 'Loctite 243'
    qty_on_hand REAL NOT NULL DEFAULT 0,
    unit TEXT DEFAULT '',              -- l | ml | pcs | m
    notes TEXT DEFAULT ''
);

-- what went where: cross-links consumables to jobs and log entries
CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY,
    consumable_id INTEGER NOT NULL REFERENCES consumables(id),
    date TEXT NOT NULL DEFAULT (date('now')),
    job TEXT DEFAULT '',
    quantity REAL NOT NULL,
    unit TEXT DEFAULT '',
    note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS calendar (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    due_date TEXT,                     -- ISO date; NULL = unscheduled
    recurrence TEXT DEFAULT '',        -- '', 'monthly', 'yearly', 'per 10k km', ...
    details TEXT DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0
);

CREATE TRIGGER IF NOT EXISTS trg_parts_touch AFTER UPDATE ON parts
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE parts SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- budget views -------------------------------------------------------------
CREATE VIEW IF NOT EXISTS budget_by_category AS
SELECT category, ROUND(SUM(amount), 2) AS total, COUNT(*) AS items
FROM costs GROUP BY category ORDER BY total DESC;

CREATE VIEW IF NOT EXISTS budget_by_job AS
SELECT COALESCE(NULLIF(job, ''), '(general)') AS job,
       ROUND(SUM(amount), 2) AS total, COUNT(*) AS items
FROM costs GROUP BY job ORDER BY total DESC;

CREATE VIEW IF NOT EXISTS open_parts AS
SELECT * FROM parts WHERE status IN ('needed','found','ordered') ORDER BY status, name;
