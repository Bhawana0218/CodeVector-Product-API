from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.crud import get_categories, get_products
from app.database import Base, SessionLocal, engine
from app.schema import ProductListResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Catalog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", include_in_schema=False)
def home():
    return {"message": "Product Catalog API"}


@app.get("/products", response_model=ProductListResponse)
def list_products(
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    products, next_cursor, has_more = get_products(
        db, cursor=cursor, limit=limit, category=category
    )
    return ProductListResponse(
        products=products, next_cursor=next_cursor, has_more=has_more
    )


@app.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return get_categories(db)


@app.get("/ui", include_in_schema=False)
def ui():
    return HTMLResponse(UI_HTML)


UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Product Catalog</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; color: #333; }
  .container { max-width: 960px; margin: 0 auto; padding: 20px; }
  header { background: #1a1a2e; color: #fff; padding: 24px 0; text-align: center; margin-bottom: 24px; }
  header h1 { font-size: 1.5rem; font-weight: 600; }
  .controls { display: flex; gap: 12px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
  .controls label { font-weight: 600; font-size: 0.875rem; }
  .controls select, .controls button { padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.875rem; }
  .controls select { min-width: 160px; }
  .controls button { background: #0f3460; color: #fff; border: none; cursor: pointer; font-weight: 500; }
  .controls button:disabled { opacity: 0.5; cursor: not-allowed; }
  .controls button:hover:not(:disabled) { background: #1a5276; }
  .stats { font-size: 0.8rem; color: #666; margin-bottom: 12px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
  .card { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
  .card h3 { font-size: 1rem; margin-bottom: 8px; }
  .card .meta { font-size: 0.8rem; color: #666; }
  .card .meta span { display: inline-block; margin-right: 12px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
  .badge-electronics { background: #e3f2fd; color: #1565c0; }
  .badge-books { background: #fce4ec; color: #c62828; }
  .badge-fashion { background: #f3e5f5; color: #6a1b9a; }
  .badge-home { background: #e8f5e9; color: #2e7d32; }
  .badge-sports { background: #fff3e0; color: #e65100; }
  .price { font-size: 1.125rem; font-weight: 700; color: #0f3460; margin-top: 8px; }
  .loading { text-align: center; padding: 40px; color: #666; }
  .pagination-info { text-align: center; margin: 20px 0; font-size: 0.85rem; color: #888; }
  .error { color: #c62828; text-align: center; padding: 20px; }
</style>
</head>
<body>
<header><h1>Product Catalog</h1></header>
<div class="container">
  <div class="controls">
    <label for="category">Category</label>
    <select id="category"><option value="">All Categories</option></select>
    <button id="loadBtn">Load More</button>
    <button id="resetBtn">Reset</button>
  </div>
  <div class="stats" id="stats"></div>
  <div class="grid" id="grid"></div>
  <div class="pagination-info" id="paginationInfo"></div>
</div>
<script>
const API_BASE = window.location.origin;
let currentCursor = null;
let hasMore = true;
let loading = false;
let currentCategory = '';
let totalShown = 0;

async function loadCategories() {
  const res = await fetch(API_BASE + '/categories');
  const cats = await res.json();
  const sel = document.getElementById('category');
  cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    sel.appendChild(opt);
  });
}

function badgeClass(cat) {
  return 'badge badge-' + cat.toLowerCase();
}

function renderProducts(products) {
  const grid = document.getElementById('grid');
  products.forEach(p => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <span class="${badgeClass(p.category)}">${p.category}</span>
      <h3>${p.name}</h3>
      <div class="price">$${p.price.toFixed(2)}</div>
      <div class="meta">
        <span>ID: ${p.id}</span>
        <span>${new Date(p.created_at).toLocaleDateString()}</span>
      </div>`;
    grid.appendChild(card);
  });
  totalShown += products.length;
  document.getElementById('stats').textContent = `Showing ${totalShown} products`;
}

async function loadProducts() {
  if (loading || !hasMore) return;
  loading = true;
  document.getElementById('loadBtn').disabled = true;
  document.getElementById('loadBtn').textContent = 'Loading...';
  try {
    const params = new URLSearchParams();
    if (currentCursor) params.set('cursor', currentCursor);
    params.set('limit', '50');
    if (currentCategory) params.set('category', currentCategory);
    const res = await fetch(API_BASE + '/products?' + params.toString());
    const data = await res.json();
    renderProducts(data.products);
    currentCursor = data.next_cursor;
    hasMore = data.has_more;
    document.getElementById('paginationInfo').textContent = hasMore
      ? 'Scroll down and click "Load More" for next page'
      : 'All products loaded';
    document.getElementById('loadBtn').textContent = hasMore ? 'Load More' : 'All Loaded';
  } catch (e) {
    document.getElementById('paginationInfo').textContent = 'Error loading products';
    document.getElementById('loadBtn').textContent = 'Retry';
  } finally {
    loading = false;
    document.getElementById('loadBtn').disabled = !hasMore;
  }
}

function reset() {
  currentCursor = null;
  hasMore = true;
  totalShown = 0;
  document.getElementById('grid').innerHTML = '';
  document.getElementById('stats').textContent = '';
  document.getElementById('paginationInfo').textContent = '';
  currentCategory = document.getElementById('category').value;
  loadProducts();
}

document.getElementById('loadBtn').addEventListener('click', loadProducts);
document.getElementById('resetBtn').addEventListener('click', reset);
document.getElementById('category').addEventListener('change', reset);

loadCategories().then(loadProducts);
</script>
</body>
</html>
"""
