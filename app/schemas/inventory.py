from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class InventoryBase(BaseModel):
    product_id: int
    quantity: int
    low_stock_threshold: int = 10

class InventoryCreate(InventoryBase):
    pass

class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    last_restock_date: Optional[datetime] = None

class InventoryResponse(InventoryBase):
    id: int
    last_restock_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class InventoryChangeCreate(BaseModel):
    inventory_id: int
    quantity_change: int
    reason: Optional[str] = None

class InventoryChangeResponse(InventoryChangeCreate):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class LowStockAlert(BaseModel):
    product_id: int
    product_name: str
    product_sku: str
    current_quantity: int
    low_stock_threshold: int
    
    class Config:
        orm_mode = True