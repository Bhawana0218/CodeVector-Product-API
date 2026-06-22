from datetime import datetime

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: int
    name: str
    category: str
    price: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    products: list[ProductOut]
    next_cursor: str | None = None
    has_more: bool = False
