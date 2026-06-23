"""
Seed 200,000 products using psycopg2 execute_values for maximum
batch-insert performance.  Resumable — pass --resume to skip
truncation and continue from the current row count.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from random import choice, randint, uniform

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env file")

CATEGORIES = ["Electronics", "Books", "Fashion", "Home", "Sports"]
ADJECTIVES = [
    "Premium", "Basic", "Pro", "Ultra", "Classic", "Modern",
    "Eco", "Smart", "Essential", "Deluxe", "Compact", "Portable",
]
NOUNS = [
    "Widget", "Gadget", "Tool", "Device", "Kit", "Set",
    "Pack", "Bundle", "Collection", "System", "Organizer", "Sensor",
]

TOTAL = 200_000
BATCH = 10_000

BASE_TIME = datetime.now(timezone.utc)
DAYS_SPAN = 730


def main():
    resume = "--resume" in sys.argv

    conn = psycopg2.connect(DATABASE_URL)

    if resume:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM products")
        existing = cur.fetchone()[0]
        cur.close()
        print(f"Resume mode — {existing:,} existing rows")
    else:
        cur = conn.cursor()
        cur.execute("TRUNCATE products RESTART IDENTITY CASCADE")
        conn.commit()
        cur.close()
        existing = 0
        print("Table truncated — starting fresh.")

    if existing >= TOTAL:
        print(f"Already {existing:,} ≥ {TOTAL:,}, nothing to do.")
        conn.close()
        return

    print(f"Seeding {TOTAL - existing:,} new products ...")
    for offset in range(existing, TOTAL, BATCH):
        size = min(BATCH, TOTAL - offset)
        rows = _make_rows(size, offset)
        _bulk_insert(conn, rows)
        print(f"  {offset + size:>7,} / {TOTAL:,}")

    conn.close()
    print("Done.")


def _make_rows(size: int, offset: int):
    rows = []
    for i in range(size):
        idx = offset + i
        age_days = DAYS_SPAN * (1 - idx / TOTAL) + randint(-3, 3)
        created = BASE_TIME - timedelta(days=age_days, hours=randint(0, 23))
        updated = created + timedelta(hours=randint(0, 72))
        rows.append((
            f"{choice(ADJECTIVES)} {choice(NOUNS)}",
            choice(CATEGORIES),
            round(uniform(5.0, 999.99), 2),
            created,
            updated,
        ))
    return rows


def _bulk_insert(conn, rows):
    execute_values(
        conn.cursor(),
        """
        INSERT INTO products (name, category, price, created_at, updated_at)
        VALUES %s
        """,
        rows,
        template="(%s, %s, %s, %s, %s)",
    )
    conn.commit()


if __name__ == "__main__":
    main()
