ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);

ALTER TABLE reminders ADD COLUMN IF NOT EXISTS dispatched BOOLEAN DEFAULT false;

ALTER TABLE expenses ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id);

ALTER TABLE announcements ADD COLUMN IF NOT EXISTS apply_method VARCHAR(255);

ALTER TABLE announcement_summaries ADD COLUMN IF NOT EXISTS llm_used BOOLEAN DEFAULT false;

CREATE TABLE IF NOT EXISTS notifications (
    id         SERIAL PRIMARY KEY,
    user_id    INT REFERENCES users(id),
    kind       VARCHAR(50),
    title      VARCHAR(255),
    body       TEXT,
    channel    VARCHAR(50),
    status     VARCHAR(50),
    read_flag  BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now()
);