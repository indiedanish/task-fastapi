from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    price: float
    cost: float
    category_id: int
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class ProductWithInventory(ProductResponse):
    quantity: int
    low_stock_threshold: int
    
    class Config:
        orm_mode = True