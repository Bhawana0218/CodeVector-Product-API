import base64
import json
from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models import Product


def _encode_cursor(snapshot_at: datetime, last_created: datetime, last_id: int) -> str:
    payload = {
        "s": snapshot_at.isoformat(),
        "c": last_created.isoformat(),
        "i": last_id,
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str):
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor))
        return (
            datetime.fromisoformat(payload["s"]),
            datetime.fromisoformat(payload["c"]),
            payload["i"],
        )
    except Exception:
        return None


def get_products(
    db: Session,
    cursor: str | None = None,
    limit: int = 50,
    category: str | None = None,
):
    if cursor is None:
        snapshot_at = db.query(func.max(Product.created_at)).scalar()
        last_created = None
        last_id = None
    else:
        decoded = _decode_cursor(cursor)
        if decoded is None:
            snapshot_at = db.query(func.max(Product.created_at)).scalar()
            last_created = None
            last_id = None
        else:
            snapshot_at, last_created, last_id = decoded

    query = db.query(Product)

    if category:
        query = query.filter(Product.category == category)

    if snapshot_at is not None:
        query = query.filter(Product.created_at <= snapshot_at)

    if last_created is not None:
        query = query.filter(
            or_(
                Product.created_at < last_created,
                and_(
                    Product.created_at == last_created,
                    Product.id < last_id,
                ),
            )
        )

    query = query.order_by(Product.created_at.desc(), Product.id.desc())
    products = query.limit(limit + 1).all()

    has_more = len(products) > limit
    products = products[:limit]

    next_cursor = None
    if has_more and products:
        last = products[-1]
        next_cursor = _encode_cursor(snapshot_at, last.created_at, last.id)

    return products, next_cursor, has_more


def get_categories(db: Session):
    return [
        row[0]
        for row in db.query(Product.category)
        .distinct()
        .order_by(Product.category)
        .all()
    ]
