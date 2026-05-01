"""
Ashritha Jewellers – SQLite Database Setup
Creates all tables and seeds admin user on first run.
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ashritha.db')

SCHEMA = """
-- ──────────────────────────────────────
-- USERS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fname       TEXT    NOT NULL,
    lname       TEXT    DEFAULT '',
    email       TEXT    NOT NULL UNIQUE,
    phone       TEXT    DEFAULT '',
    password    TEXT    NOT NULL,
    address     TEXT    DEFAULT '',
    is_admin    INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────
-- PRODUCTS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    category    TEXT    NOT NULL,   -- necklace | earrings | bangles | sets | rings | silver
    price       REAL    NOT NULL,
    mrp         REAL    DEFAULT NULL,
    stock       INTEGER DEFAULT 0,
    badge       TEXT    DEFAULT '',
    description TEXT    DEFAULT '',
    image_url   TEXT    DEFAULT '',
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────
-- ORDERS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_ref       TEXT    NOT NULL UNIQUE,   -- e.g. AJ123456
    user_id         INTEGER DEFAULT NULL,       -- NULL for guest orders
    customer_name   TEXT    NOT NULL,
    customer_phone  TEXT    NOT NULL,
    address         TEXT    NOT NULL,
    city            TEXT    NOT NULL,
    state           TEXT    DEFAULT '',
    pin_code        TEXT    NOT NULL,
    notes           TEXT    DEFAULT '',
    subtotal        REAL    NOT NULL,
    shipping        REAL    DEFAULT 0,
    total           REAL    NOT NULL,
    status          TEXT    DEFAULT 'pending',  -- pending | confirmed | shipped | delivered | cancelled
    created_at      TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ──────────────────────────────────────
-- ORDER ITEMS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    product_name TEXT   NOT NULL,   -- snapshot at time of order
    price       REAL   NOT NULL,    -- snapshot price
    qty         INTEGER NOT NULL,
    FOREIGN KEY (order_id)   REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- ──────────────────────────────────────
-- SETTINGS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""

SEED_PRODUCTS = [
    ("Kundan Bridal Necklace Set",   "necklace", 1850, 2800, 8,  "Bestseller", "Stunning Kundan work necklace with matching earrings. Perfect for bridal and festive occasions. Premium 1 gram gold finish.", ""),
    ("Temple Coin Drop Earrings",    "earrings", 450,  699,  15, "Trending",   "Traditional temple-style coin drop earrings with intricate gold work. Lightweight and comfortable for all-day wear.", ""),
    ("Antique Gold Bangles Set of 4","bangles",  780,  1100, 3,  "",           "Beautiful antique-finish bangles with floral motif. Set of 4. Matches any traditional outfit perfectly.", ""),
    ("Royal Kundan Bridal Set",      "sets",     3200, 4500, 5,  "Sale",       "Complete bridal jewellery set: heavy kundan necklace, jhumka earrings, and maang tikka.", ""),
    ("Classic Pearl Finger Ring",    "rings",    299,  450,  20, "New",        "Elegant adjustable ring with freshwater pearl. Perfect for daily wear or special occasions.", ""),
    ("Oxidised Choker Necklace",     "necklace", 650,  950,  12, "Trending",   "Gorgeous oxidised finish choker with beaded detailing.", ""),
    ("Chandbali Jhumka Earrings",    "earrings", 580,  850,  9,  "Bestseller", "Traditional chandbali design with peacock motif and pearl drops.", ""),
    ("92.5 Silver Jhumka Earrings",  "silver",   890,  1200, 7,  "",           "Hallmarked 92.5 pure silver jhumkas with delicate filigree work.", ""),
    ("92.5 Silver Bangles Set",      "silver",   1200, 1600, 4,  "New",        "Beautiful set of 4 hallmarked 92.5 silver bangles with intricate oxidised work.", ""),
    ("Meenakari Bangles Set of 2",   "bangles",  520,  750,  0,  "",           "Colourful meenakari work bangles in vibrant hues. Set of 2.", ""),
]

SEED_SETTINGS = [
    ("wa_number",       "919000000000"),
    ("upi_id",          ""),
    ("ann_text",        "Free Shipping on Orders Above Rs 499  |  100% Genuine 1 Gram Gold  |  92.5 Silver Collection Now Available"),
    ("free_shipping",   "499"),
    ("shipping_charge", "50"),
    ("store_name",      "Ashritha Jewellers"),
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)

    # Seed admin
    admin = conn.execute("SELECT id FROM users WHERE email = 'admin@ashritha.com'").fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users (fname, email, password, is_admin) VALUES (?, ?, ?, 1)",
            ("Admin", "admin@ashritha.com", generate_password_hash("admin123"))
        )

    # Seed products
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO products (name, category, price, mrp, stock, badge, description, image_url) VALUES (?,?,?,?,?,?,?,?)",
            SEED_PRODUCTS
        )

    # Seed settings
    for key, val in SEED_SETTINGS:
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    conn.commit()
    conn.close()
    print("Database initialised at:", DB_PATH)


if __name__ == "__main__":
    init_db()
