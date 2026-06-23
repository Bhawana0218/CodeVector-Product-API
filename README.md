# Product Catalog API

Browse 200,000 products — newest first, filter by category, fast cursor-based pagination that stays correct even while data changes.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Runtime** | Python 3.11+ / FastAPI | Async-capable, auto-docs, great DX |
| **Database** | PostgreSQL (Neon) | Composite indexes, `ORDER BY` with `WHERE` pushdown, snapshot isolation |
| **ORM** | SQLAlchemy 2.0 | Expression-level control over queries while keeping a thin mapping layer |
| **Seed** | Raw SQL + batch inserts | 200 K rows in ~seconds instead of minutes with ORM-per-row |

## Design Decisions

### 1. Cursor-based pagination (not offset)

`OFFSET` / `LIMIT` forces the database to count and skip rows on every request — O(n) per page, so page 2000 is painfully slow. More critically, offset is **brittle under write load**: inserting a single new product shifts every offset boundary, causing users to see duplicates or skip items.

Cursor pagination uses a **keyset** `(created_at DESC, id DESC)`:

- The server returns an opaque `next_cursor` token with each page.
- The client sends it back for the next page; the server decodes it and adds a `WHERE` clause that picks up exactly where the last page stopped.
- Cost per page is identical regardless of depth — a simple index range scan.

### 2. Snapshot isolation for consistency

Even cursor pagination can miss or duplicate items if rows are inserted ahead of the cursor position mid-session.

**Solution**: On the first request, the server records `max(created_at)` — the snapshot boundary. Every subsequent page within that session filters with `created_at <= snapshot_boundary`. New rows (which always have `created_at > boundary`) are invisible until the user explicitly resets.

This guarantees:
- **No duplicates** — each row has a unique position in `(created_at, id)` ordering, and the cursor always advances monotonically.
- **No misses** — the snapshot is frozen; concurrent inserts cannot shift rows into or out of the window.
- **Freshness on demand** — the user sees the latest data when they start a new session.

### 3. Index strategy

Three indexes support the two query patterns:

```
ix_created_id_desc          (created_at, id)           — unfiltered pagination
ix_category                 (category)                  — category listing / filter
ix_category_created_id_desc (category, created_at, id)  — filtered pagination
```

All queries are index-only or index-range scans; no seq scans or in-memory sorts.

### 4. Efficient seeding

The seed script (`scripts/seed.py`):

- Uses **psycopg2 `execute_values`** — the fastest PostgreSQL bulk-insert method available to Python (equivalent to `COPY` for moderate batch sizes).
- Inserts in **batches of 10 000** per round-trip, reconnecting on failure.
- Supports `--resume` to continue from the current count instead of truncating.
- Spreads `created_at` across 2 years so "newest first" shows variety on every page.

## API

| Endpoint | Method | Params | Description |
|----------|--------|--------|-------------|
| `/products` | GET | `cursor`, `limit`, `category` | Paginated product list |
| `/categories` | GET | — | Distinct categories |
| `/ui` | GET | — | Simple browser UI |

### `/products` example

```bash
curl "https://yourapp.onrender.com/products?limit=20&category=Electronics"
```

Response:

```json
{
  "products": [
    { "id": 42, "name": "Smart Widget", "category": "Electronics",
      "price": 149.99, "created_at": "2026-06-20T...", "updated_at": "..." }
  ],
  "next_cursor": "eyJzIjoiMjAyNi0wNi0yMFQ...",
  "has_more": true
}
```

Pass `next_cursor` as the `cursor` parameter for the next page.

## Running Locally

1. **Set up the database**  
   Create a free database at [Neon](https://neon.tech) and copy the connection string.

2. **Configure**  
   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL
   ```

3. **Install dependencies**  
   ```bash
   python -m venv venv && venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Seed data**  
   ```bash
   python scripts/seed.py
   ```
   To continue from an interrupted run (e.g. after a timeout):
   ```bash
   python scripts/seed.py --resume
   ```

5. **Start**  
   ```bash
   uvicorn app.main:app --reload
   ```

Visit `http://localhost:8000/ui` for the browser UI.

## Notes

- The `next_cursor` is a base64-encoded JSON blob `{s: snapshot_at, c: cursor_created_at, i: cursor_id}`. It's opaque to clients.
- For simplicity, the category filter also uses the snapshot boundary. Switching categories resets the cursor (like starting a new search).
- The UI is intentionally minimal (vanilla HTML/JS) — the backend is the deliverable.
