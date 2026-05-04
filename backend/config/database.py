"""
Ashritha Jewellers — Database (PostgreSQL via Supabase)
Run standalone:  python config/database.py
"""
import os
import secrets
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
DOTENV_PATHS = [
    os.path.join(REPO_ROOT, ".env"),
    os.path.join(REPO_ROOT, "api", ".env"),
    os.path.join(os.path.dirname(__file__), ".env"),
]
for path in DOTENV_PATHS:
    if not os.path.exists(path):
        continue

    with open(path, "r", encoding="utf-8") as f:
        contents = f.read().strip()

    if contents and "=" not in contents and contents.startswith(("postgres://", "postgresql://")):
        os.environ.setdefault("DATABASE_URL", contents)
    else:
        load_dotenv(path, override=False)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    for fallback_key in ("PGDATABASE_URL", "DATABASE_URI", "DB_URL", "SUPABASE_DATABASE_URL"):
        DATABASE_URL = os.environ.get(fallback_key, "")
        if DATABASE_URL:
            break

DATABASE_URL = DATABASE_URL.strip()
ENABLE_SEED_DATA = os.environ.get("ENABLE_SEED_DATA", "false").lower() == "true"
PURGE_DEMO_DATA = os.environ.get("PURGE_DEMO_DATA", "false").lower() == "true"

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

SEED_PRODUCTS = [
    ("Kundan Bridal Necklace Set",  "necklace", 1850, 2800, 8,  "Bestseller", "Stunning Kundan work necklace with matching earrings.",   "", 1, 250, 2000, 7),
    ("Temple Coin Drop Earrings",   "earrings", 450,  699,  15, "Trending",   "Traditional temple-style coin drop earrings.",             "", 0, 0,   0,    7),
    ("Antique Gold Bangles Set",    "bangles",  780,  1100, 3,  "",           "Beautiful antique-finish bangles with floral motif.",      "", 1, 120, 1000, 5),
    ("Royal Kundan Bridal Set",     "sets",     3200, 4500, 5,  "Sale",       "Complete bridal jewellery set.",                           "", 1, 400, 3500, 3),
    ("Classic Pearl Finger Ring",   "rings",    299,  450,  20, "New",        "Elegant adjustable ring with freshwater pearl.",           "", 0, 0,   0,    7),
    ("Oxidised Choker Necklace",    "necklace", 650,  950,  12, "Trending",   "Gorgeous oxidised finish choker.",                        "", 1, 100, 700,  7),
    ("Chandbali Jhumka Earrings",   "earrings", 580,  850,  9,  "Bestseller", "Traditional chandbali design with peacock motif.",        "", 0, 0,   0,    7),
    ("Meenakari Bangles Set of 2",  "bangles",  520,  750,  0,  "",           "Colourful meenakari work bangles.",                       "", 0, 0,   0,    7),
]

SEED_SETTINGS = [
    ("wa_number",       "919381360636"),
    ("upi_id",          ""),
    ("ann_text",        "Free Shipping on Orders Above Rs 499  |  100% Genuine 1 Gram Gold"),
    ("free_shipping",   "499"),
    ("shipping_charge", "50"),
    ("store_name",      "Ashritha Jewellers"),
]

SEED_REVIEWS = [
    (1, None, "Priya R.",   5, "Absolutely stunning! The quality is far better than expected. So many compliments!", "approved"),
    (1, None, "Meena S.",   4, "Very pretty set. The gold finish looks real and lasts well.", "approved"),
    (2, None, "Ritu K.",    5, "Perfect for temple visits. Light weight and very comfortable.", "approved"),
    (4, None, "Anjali V.",  5, "Rented for my sister's wedding — gorgeous! The rental process was so smooth.", "approved"),
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
        raise Exception(
            "DATABASE_URL environment variable is not set! "
            "Set DATABASE_URL in your deployment environment or add a .env file with the Supabase PostgreSQL URL."
        )

    db_url = DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if "sslmode=" not in db_url:
        db_url = f"{db_url}?sslmode=require" if "?" not in db_url else f"{db_url}&sslmode=require"

    conn = psycopg2.connect(db_url)
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
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@ashritha.com").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password:
        admin_password = secrets.token_urlsafe(16)
        print("Warning: ADMIN_PASSWORD not set. Generated one-time admin password for this boot.")
    if not conn.execute("SELECT id FROM users WHERE email=%s", (admin_email,)).fetchone():
        conn.execute(
            "INSERT INTO users (fname,email,password,is_admin) VALUES (%s,%s,%s,1)",
            ("Admin", admin_email, generate_password_hash(admin_password))
        )

    # Optional development-only seeds
    if ENABLE_SEED_DATA:
        if conn.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"] == 0:
            conn.executemany(
                """INSERT INTO products
                   (name,category,price,mrp,stock,badge,description,image_url,rent_enabled,rent_price,deposit,max_days)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                SEED_PRODUCTS
            )

        if conn.execute("SELECT COUNT(*) AS count FROM reviews").fetchone()["count"] == 0:
            conn.executemany(
                "INSERT INTO reviews (product_id,user_id,author_name,rating,review_text,status) VALUES (%s,%s,%s,%s,%s,%s)",
                SEED_REVIEWS
            )
    elif PURGE_DEMO_DATA:
        demo_names = [row[0] for row in SEED_PRODUCTS]
        demo_authors = [row[2] for row in SEED_REVIEWS]
        conn.execute("DELETE FROM reviews WHERE user_id IS NULL AND author_name = ANY(%s)", (demo_authors,))
        conn.execute("DELETE FROM products WHERE name = ANY(%s)", (demo_names,))

    # Settings
    for k, v in SEED_SETTINGS:
        conn.execute("INSERT INTO settings (key,value) VALUES (%s,%s) ON CONFLICT (key) DO NOTHING", (k, v))

    conn.commit()
    conn.close()
    print("PostgreSQL Database is ready!")


if __name__ == "__main__":
    init_db()
