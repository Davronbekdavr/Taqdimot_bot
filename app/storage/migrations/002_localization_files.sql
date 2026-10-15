ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'uz';
ALTER TABLE users ADD COLUMN language_selected INTEGER NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS generated_files(
 id TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
 file_path TEXT NOT NULL,
 display_name TEXT NOT NULL,
 format TEXT NOT NULL,
 page_count INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_generated_files_owner ON generated_files(user_id,created_at);
