from sqlalchemy import BigInteger, Column, DateTime, Float, Index, String
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_created_id_desc", "created_at", "id"),
        Index("ix_category_created_id_desc", "category", "created_at", "id"),
    )
