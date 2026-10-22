-- Application-owned v1 tables only. PHM and agent checkpoints are untouched.
CREATE TABLE IF NOT EXISTS v1_tasks (
    id uuid PRIMARY KEY,
    user_name text NOT NULL,
    user_role text NOT NULL CHECK (user_role IN ('worker', 'engineer', 'admin')),
    question text NOT NULL,
    command_id uuid NOT NULL,
    status text NOT NULL CHECK (status IN (
        'QUEUED', 'RUNNING', 'WAITING_INPUT', 'WAITING_APPROVAL',
        'DONE', 'INCOMPLETE', 'FAILED'
    )),
    report jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS v1_tasks_owner ON v1_tasks (user_name, created_at);
CREATE TABLE IF NOT EXISTS v1_events (
    task_id uuid NOT NULL REFERENCES v1_tasks(id),
    seq bigint NOT NULL,
    event_id text,
    type text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (task_id, seq),
    UNIQUE (task_id, event_id)
);
CREATE TABLE IF NOT EXISTS v1_messages (
    id bigserial PRIMARY KEY,
    task_id uuid NOT NULL REFERENCES v1_tasks(id),
    role text NOT NULL CHECK (role IN ('user', 'assistant')),
    text text NOT NULL,
    user_name text NOT NULL,
    user_role text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS v1_messages_task ON v1_messages (task_id, id);
CREATE TABLE IF NOT EXISTS v1_reviews (
    id bigserial PRIMARY KEY,
    task_id uuid NOT NULL REFERENCES v1_tasks(id),
    action text NOT NULL CHECK (action IN ('approve', 'revise')),
    comment text NOT NULL,
    user_name text NOT NULL,
    user_role text NOT NULL CHECK (user_role = 'engineer'),
    report jsonb,
    event_time timestamptz,
    lot_id text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS v1_reviews_task ON v1_reviews (task_id, id);
CREATE TABLE IF NOT EXISTS v1_investigations (
    id bigserial PRIMARY KEY,
    task_id uuid UNIQUE NOT NULL REFERENCES v1_tasks(id),
    review_id bigint NOT NULL REFERENCES v1_reviews(id),
    report jsonb NOT NULL,
    approved_by text NOT NULL,
    approved_role text NOT NULL CHECK (approved_role = 'engineer'),
    event_time timestamptz,
    lot_id text,
    approved_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- One system-requested task per (tool, chamber, lot) alert bundle; bundle keeps the evidence sent.
-- task_id is deferred so the key claim and the task row share one transaction.
CREATE TABLE IF NOT EXISTS v1_alert_tasks (
    alert_key text PRIMARY KEY,
    task_id uuid UNIQUE NOT NULL REFERENCES v1_tasks(id) DEFERRABLE INITIALLY DEFERRED,
    bundle jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Historical mock identities are not linked to accounts by display name.
ALTER TABLE v1_tasks ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE v1_messages ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE v1_reviews ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE v1_investigations ADD COLUMN IF NOT EXISTS approved_by_id text;

ALTER TABLE v1_tasks DROP CONSTRAINT IF EXISTS v1_tasks_user_role_check;
ALTER TABLE v1_tasks ADD CONSTRAINT v1_tasks_user_role_check
    CHECK (user_role IN ('user', 'worker', 'engineer', 'admin'));
ALTER TABLE v1_reviews DROP CONSTRAINT IF EXISTS v1_reviews_user_role_check;
ALTER TABLE v1_reviews ADD CONSTRAINT v1_reviews_user_role_check
    CHECK (user_role IN ('user', 'engineer'));
ALTER TABLE v1_investigations DROP CONSTRAINT IF EXISTS v1_investigations_approved_role_check;
ALTER TABLE v1_investigations ADD CONSTRAINT v1_investigations_approved_role_check
    CHECK (approved_role IN ('user', 'engineer'));
