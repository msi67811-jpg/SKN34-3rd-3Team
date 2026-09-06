-- App columns that SQLite persist uses but DB/schema.sql did not include yet.
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(40);
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS dispatched BOOLEAN DEFAULT FALSE;
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE announcements ADD COLUMN IF NOT EXISTS apply_method TEXT;
ALTER TABLE announcement_summaries ADD COLUMN IF NOT EXISTS llm_used BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS notifications (
    id         SERIAL PRIMARY KEY,
    user_id    INT REFERENCES users(id) ON DELETE CASCADE,
    kind       VARCHAR(50),
    title      TEXT,
    body       TEXT,
    channel    VARCHAR(50),
    status     VARCHAR(50),
    read_flag  BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS meta_ids (
    name  TEXT PRIMARY KEY,
    value INT
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id  TEXT PRIMARY KEY,
    policy_id INT,
    title     TEXT,
    source    TEXT,
    page      INT,
    content   TEXT,
    embedding VECTOR(1536)
);
