"""
Ashritha Jewellers — Database (PostgreSQL via Supabase)
Run standalone:  python config/database.py
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")

SCHEMA = """
-- ── USERS ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    fname      TEXT    NOT NULL,
    lname      TEXT    DEFAULT '',
    email      TEXT    NOT NULL UNIQUE,
    phone      TEXT    DEFAULT '',
    password   TEXT    NOT NULL,
    address    TEXT    DEFAULT '',
    cart_data  TEXT    DEFAULT '[]',
    is_admin   INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── PRODUCTS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id           SERIAL PRIMARY KEY,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    price        REAL    NOT NULL,
    mrp          REAL    DEFAULT NULL,
    stock        INTEGER DEFAULT 0,
    badge        TEXT    DEFAULT '',
    description  TEXT    DEFAULT '',
    image_url    TEXT    DEFAULT '',
    is_active    INTEGER DEFAULT 1,
    rent_enabled INTEGER DEFAULT 0,
    rent_price   REAL    DEFAULT 0,
    deposit      REAL    DEFAULT 0,
    max_days     INTEGER DEFAULT 7,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── ORDERS ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id             SERIAL PRIMARY KEY,
    order_ref      TEXT    NOT NULL UNIQUE,
    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    customer_name  TEXT    NOT NULL,
    customer_phone TEXT    NOT NULL,
    address        TEXT    NOT NULL,
    city           TEXT    NOT NULL,
    state          TEXT    DEFAULT '',
    pin_code       TEXT    NOT NULL,
    notes          TEXT    DEFAULT '',
    subtotal       REAL    NOT NULL,
    shipping       REAL    DEFAULT 0,
    total          REAL    NOT NULL,
    status         TEXT    DEFAULT 'pending',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── ORDER ITEMS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id),
    product_name TEXT    NOT NULL,
    price        REAL    NOT NULL,
    qty          INTEGER NOT NULL
);

-- ── REVIEWS ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    id           SERIAL PRIMARY KEY,
    product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    author_name  TEXT    NOT NULL,
    rating       INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    review_text  TEXT    NOT NULL,
    status       TEXT    DEFAULT 'pending',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── RENT REQUESTS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rent_requests (
    id             SERIAL PRIMARY KEY,
    product_id     INTEGER NOT NULL REFERENCES products(id),
    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    customer_name  TEXT    NOT NULL,
    customer_phone TEXT    NOT NULL,
    address        TEXT    NOT NULL,
    start_date     TEXT    NOT NULL,
    end_date       TEXT    NOT NULL,
    days           INTEGER NOT NULL,
    rent_total     REAL    NOT NULL,
    deposit        REAL    NOT NULL,
    grand_total    REAL    NOT NULL,
    status         TEXT    DEFAULT 'pending',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── SETTINGS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SEED_SETTINGS = [
    ("wa_number",       "919000000000"),
    ("upi_id",          ""),
    ("ann_text",        "Free Shipping on Orders Above Rs 499  |  100% Genuine 1 Gram Gold"),
    ("free_shipping",   "499"),
    ("shipping_charge", "50"),
    ("store_name",      "Ashritha Jewellers"),
]


class DBWrapper:
    """Wrapper to make psycopg2 act like sqlite3 for this app."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return self._conn.cursor(cursor_factory=RealDictCursor)

    def execute(self, sql, args=None):
        cur = self.cursor()
        if args:
            cur.execute(sql, args)
        else:
            cur.execute(sql)
        return cur

    def executemany(self, sql, args):
        cur = self._conn.cursor()
        cur.executemany(sql, args)
        return cur

    def executescript(self, script):
        cur = self._conn.cursor()
        cur.execute(script)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_conn():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set!")
    conn = psycopg2.connect(DATABASE_URL)
    return DBWrapper(conn)


def init_db():
    try:
        conn = get_conn()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    conn.executescript(SCHEMA)

    try:
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS cart_data TEXT DEFAULT '[]'")
    except Exception:
        pass # Ignored if unsupported or already exists

    # Admin user
    if not conn.execute("SELECT id FROM users WHERE email=%s", ("admin@ashritha.com",)).fetchone():
        conn.execute(
            "INSERT INTO users (fname,email,password,is_admin) VALUES (%s,%s,%s,1)",
            ("Admin", "admin@ashritha.com", generate_password_hash("admin123"))
        )



    # Settings
    for k, v in SEED_SETTINGS:
        conn.execute("INSERT INTO settings (key,value) VALUES (%s,%s) ON CONFLICT (key) DO NOTHING", (k, v))

    conn.commit()
    conn.close()
    print("PostgreSQL Database is ready!")


if __name__ == "__main__":
    init_db()
