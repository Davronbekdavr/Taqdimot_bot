import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS users(
 telegram_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, last_active_at TEXT,
 is_blocked INTEGER NOT NULL DEFAULT 0, free_limit_override INTEGER
);
CREATE TABLE IF NOT EXISTS plans(
 id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 price INTEGER NOT NULL DEFAULT 0, currency TEXT NOT NULL DEFAULT 'XTR', duration_days INTEGER NOT NULL DEFAULT 30,
 daily_limit INTEGER, monthly_limit INTEGER, features TEXT NOT NULL DEFAULT '', max_slides INTEGER NOT NULL DEFAULT 10,
 allow_pdf INTEGER NOT NULL DEFAULT 0, allow_pptx INTEGER NOT NULL DEFAULT 1,
 examples_limit INTEGER NOT NULL DEFAULT 0, tests_limit INTEGER NOT NULL DEFAULT 0,
 ai_model TEXT, is_active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS subscriptions(
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(telegram_id),
 plan_id INTEGER NOT NULL REFERENCES plans(id), status TEXT NOT NULL, starts_at TEXT NOT NULL,
 ends_at TEXT NOT NULL, payment_id INTEGER, reminder_sent INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions(user_id,status,ends_at);
CREATE TABLE IF NOT EXISTS payments(
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(telegram_id),
 plan_id INTEGER NOT NULL REFERENCES plans(id), provider TEXT NOT NULL, provider_charge_id TEXT UNIQUE,
 invoice_payload TEXT NOT NULL UNIQUE, amount INTEGER NOT NULL, currency TEXT NOT NULL,
 status TEXT NOT NULL, test_mode INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 confirmed_at TEXT, refunded_at TEXT
);
CREATE TABLE IF NOT EXISTS usage_records(
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(telegram_id),
 feature TEXT NOT NULL, tokens INTEGER, success INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_usage_user_time ON usage_records(user_id,created_at);
CREATE TABLE IF NOT EXISTS promo_codes(
 code TEXT PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES plans(id), discount_percent INTEGER NOT NULL DEFAULT 0,
 starts_at TEXT, ends_at TEXT, max_uses INTEGER, uses INTEGER NOT NULL DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS promo_redemptions(code TEXT NOT NULL REFERENCES promo_codes(code), user_id INTEGER NOT NULL REFERENCES users(telegram_id), redeemed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(code,user_id));
CREATE TABLE IF NOT EXISTS admin_audit_logs(
 id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER NOT NULL, action TEXT NOT NULL,
 target_user_id INTEGER, details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS system_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO schema_migrations(version) VALUES(1);
"""

DEFAULT_PLANS = [
    ("free", "Free", 0, 0, 3, 10, "generate", 10, 0, 1, 3, 1, None),
    ("basic", "Basic", 100, 30, 30, 300, "generate,pptx,pdf", 20, 1, 1, 30, 10, None),
    ("pro", "Pro", 300, 30, 100, 1500, "generate,pptx,pdf,tests,examples", 40, 1, 1, 100, 50, None),
    ("premium", "Premium", 700, 30, 300, 5000, "generate,pptx,pdf,tests,examples", 80, 1, 1, 300, 200, None),
]


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None, factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        return connection

    def initialize(self) -> None:
        with self.connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            migration_dir = Path(__file__).with_name("migrations")
            for migration in sorted(migration_dir.glob("[0-9]*.sql")):
                version = int(migration.name.split("_", 1)[0])
                applied = con.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone()
                if not applied:
                    con.executescript(migration.read_text(encoding="utf-8"))
                    con.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES(?)", (version,))
            con.executemany(
                "INSERT OR IGNORE INTO plans(code,name,price,duration_days,daily_limit,monthly_limit,features,max_slides,allow_pdf,allow_pptx,examples_limit,tests_limit,ai_model) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                DEFAULT_PLANS,
            )
            con.execute("INSERT OR IGNORE INTO system_settings(key,value) VALUES('monetization_mode','FREE')")
            con.execute("INSERT OR IGNORE INTO system_settings(key,value) VALUES('expire_to_free','true')")
            con.execute("INSERT OR IGNORE INTO system_settings(key,value) VALUES('trial_days','0')")
            con.execute("INSERT OR IGNORE INTO system_settings(key,value) VALUES('trial_plan_code','basic')")
            for key,value in {
                "enabled_languages":"uz,en,ru,tr", "enabled_formats":"pptx,docx,pdf",
                "min_pages":"1", "max_pages":"50", "min_font_pt":"10", "max_font_pt":"16",
                "file_retention_days":"30", "free_formats":"pptx,docx", "presentation_max_slides":"20",
                "presentation_free_generations":"1",
            }.items():
                con.execute("INSERT OR IGNORE INTO system_settings(key,value) VALUES(?,?)",(key,value))

    def transaction(self):
        return self.connect()
