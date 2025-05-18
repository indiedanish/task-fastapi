from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.sale import PaymentMethod

class SaleItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float
    discount: float = 0.0
    total: float

class SaleItemCreate(SaleItemBase):
    pass

class SaleItemResponse(SaleItemBase):
    id: int
    sale_id: int
    product_name: Optional[str] = None
    
    class Config:
        orm_mode = True

class SaleBase(BaseModel):
    total_amount: float
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    payment_method: PaymentMethod
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    notes: Optional[str] = None

class SaleCreate(SaleBase):
    items: List[SaleItemCreate]

class SaleResponse(SaleBase):
    id: int
    reference_number: str
    created_at: datetime
    items: List[SaleItemResponse] = []
    
    class Config:
        orm_mode = True

class SaleFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None