-- DocuPilot HR / IT database (PostgreSQL 13+).
-- Run once:  psql "$DATABASE_URL" -f hr/schema.sql -f hr/seed.sql
-- or:        python -m docupilot.hr_db
-- Safe to re-run: it drops and recreates the demo tables.

DROP VIEW  IF EXISTS leave_balance_summary;
DROP TABLE IF EXISTS it_tickets;
DROP TABLE IF EXISTS leave_balances;
DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    employee_id  TEXT PRIMARY KEY CHECK (employee_id ~ '^E[0-9]{3,6}$'),
    full_name    TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    phone        TEXT,
    department   TEXT NOT NULL,
    job_title    TEXT NOT NULL,
    manager_id   TEXT REFERENCES employees (employee_id),
    location     TEXT NOT NULL,
    join_date    DATE NOT NULL
);

CREATE TABLE leave_balances (
    employee_id      TEXT NOT NULL REFERENCES employees (employee_id),
    leave_year       INT  NOT NULL,
    leave_type       TEXT NOT NULL CHECK (leave_type IN ('earned', 'casual', 'sick')),
    entitled_days    NUMERIC(4, 1) NOT NULL,
    carried_forward  NUMERIC(4, 1) NOT NULL DEFAULT 0,
    taken_days       NUMERIC(4, 1) NOT NULL DEFAULT 0,
    PRIMARY KEY (employee_id, leave_year, leave_type)
);

-- remaining = entitled + carried forward - taken
CREATE VIEW leave_balance_summary AS
SELECT employee_id, leave_year, leave_type, entitled_days, carried_forward, taken_days,
       entitled_days + carried_forward - taken_days AS remaining_days
FROM leave_balances;

CREATE TABLE it_tickets (
    ticket_id      TEXT PRIMARY KEY CHECK (ticket_id ~ '^IT-[0-9]{3,6}$'),
    employee_id    TEXT NOT NULL REFERENCES employees (employee_id),
    category       TEXT NOT NULL,
    title          TEXT NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    priority       TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    assigned_team  TEXT NOT NULL,
    opened_at      TIMESTAMPTZ NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL
);

CREATE INDEX it_tickets_employee_idx ON it_tickets (employee_id);

-- A login role that can only read. Point the MCP server's DATABASE_URL at this role in production:
--   ALTER ROLE docupilot_reader PASSWORD '<choose one>';
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'docupilot_reader') THEN
        CREATE ROLE docupilot_reader LOGIN;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA public TO docupilot_reader;
GRANT SELECT ON employees, leave_balances, leave_balance_summary, it_tickets TO docupilot_reader;
ALTER ROLE docupilot_reader SET default_transaction_read_only = on;
