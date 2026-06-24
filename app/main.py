from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/")
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
