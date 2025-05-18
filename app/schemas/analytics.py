from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
from enum import Enum

class TimeFrame(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class AnalyticsFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    product_id: Optional[int] = None
    category_id: Optional[int] = None
    time_frame: TimeFrame = TimeFrame.DAILY

class ComparisonRequest(BaseModel):
    first_period_start: datetime
    first_period_end: datetime
    second_period_start: datetime
    second_period_end: datetime
    category_id: Optional[int] = None
    product_id: Optional[int] = None

class RevenuePoint(BaseModel):
    date: date
    revenue: float
    count: int

class RevenueData(BaseModel):
    data: List[RevenuePoint]
    total_revenue: float
    average_revenue: float
    total_count: int

class ComparisonResult(BaseModel):
    first_period: RevenueData
    second_period: RevenueData
    percentage_change: float

class CategoryRevenue(BaseModel):
    category_id: int
    category_name: str
    revenue: float
    percentage: float
    
class ProductRevenue(BaseModel):
    product_id: int
    product_name: str
    product_sku: str
    category_name: str
    revenue: float
    quantity_sold: int
    percentage: float