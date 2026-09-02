"""
Creates a tiny demo SQLite database so the backend can be run and
tested immediately, without needing a real production database on
hand. Swap DATABASE_URL in .env for a real read-only connection string
when you're ready to move past this.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "demo.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    product TEXT NOT NULL,
    revenue REAL NOT NULL,
    order_date TEXT NOT NULL
);
"""

SAMPLE_ROWS = [
    (1, "West", "Widget A", 1200.0, "2026-01-05"),
    (2, "West", "Widget B", 850.5, "2026-01-12"),
    (3, "East", "Widget A", 990.0, "2026-01-15"),
    (4, "East", "Widget C", 1500.75, "2026-02-01"),
    (5, "South", "Widget B", 430.0, "2026-02-03"),
    (6, "North", "Widget A", 1100.0, "2026-02-10"),
    (7, "West", "Widget C", 2200.0, "2026-02-14"),
    (8, "South", "Widget A", 675.25, "2026-03-01"),
]


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    conn.executemany(
        "INSERT INTO orders (id, region, product, revenue, order_date) VALUES (?, ?, ?, ?, ?)",
        SAMPLE_ROWS,
    )
    conn.commit()
    conn.close()
    print(f"Seeded demo database at {DB_PATH}")


if __name__ == "__main__":
    main()
