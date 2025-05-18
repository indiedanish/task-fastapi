from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, text, extract

from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.category import Category
from app.schemas.analytics import (
    TimeFrame, AnalyticsFilter, ComparisonRequest, RevenuePoint,
    RevenueData, ComparisonResult, CategoryRevenue, ProductRevenue
)

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_revenue(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        time_frame: TimeFrame = TimeFrame.DAILY
    ) -> RevenueData:
        if not end_date:
            end_date = datetime.now()
        
        if not start_date:
            if time_frame == TimeFrame.DAILY:
                start_date = end_date - timedelta(days=30)
            elif time_frame == TimeFrame.WEEKLY:
                start_date = end_date - timedelta(weeks=12)
            elif time_frame == TimeFrame.MONTHLY:
                start_date = end_date - timedelta(days=365)
            else:
                start_date = end_date - timedelta(days=5*365)
        
        if time_frame == TimeFrame.DAILY:
            date_trunc = text("DATE(created_at)")
        elif time_frame == TimeFrame.WEEKLY:
            date_trunc = text("DATE(DATE_TRUNC('week', created_at))")
        elif time_frame == TimeFrame.MONTHLY:
            date_trunc = text("DATE(DATE_TRUNC('month', created_at))")
        else:
            date_trunc = text("DATE(DATE_TRUNC('year', created_at))")
        
        query = select(
            date_trunc.label("date"),
            func.sum(Sale.total_amount).label("revenue"),
            func.count(Sale.id).label("count")
        ).filter(
            Sale.created_at.between(start_date, end_date)
        ).group_by(
            text("date")
        ).order_by(
            text("date")
        )
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        total_revenue = sum(row.revenue for row in rows)
        total_count = sum(row.count for row in rows)
        average_revenue = total_revenue / len(rows) if rows else 0
        
        data = [
            {
                "date": row.date,
                "revenue": float(row.revenue),
                "count": row.count
            }
            for row in rows
        ]
        
        return {
            "data": data,
            "total_revenue": float(total_revenue),
            "average_revenue": float(average_revenue),
            "total_count": total_count
        }

    async def compare_periods(self, comparison: ComparisonRequest) -> ComparisonResult:
        first_period = await self._get_period_data(
            comparison.first_period_start, 
            comparison.first_period_end,
            comparison.category_id,
            comparison.product_id
        )
        
        second_period = await self._get_period_data(
            comparison.second_period_start,
            comparison.second_period_end,
            comparison.category_id,
            comparison.product_id
        )
        
        if first_period["total_revenue"] == 0:
            percentage_change = 100.0 if second_period["total_revenue"] > 0 else 0.0
        else:
            percentage_change = (
                (second_period["total_revenue"] - first_period["total_revenue"]) / 
                first_period["total_revenue"] * 100
            )
        
        return {
            "first_period": first_period,
            "second_period": second_period,
            "percentage_change": float(percentage_change)
        }

    async def _get_period_data(self, start, end, category_id=None, product_id=None):
        query = select(
            func.date(Sale.created_at).label("date"),
            func.sum(Sale.total_amount).label("revenue"),
            func.count(Sale.id).label("count")
        ).filter(
            Sale.created_at.between(start, end)
        )
        
        if category_id or product_id:
            sale_id_query = select(SaleItem.sale_id).distinct()
            
            if product_id:
                sale_id_query = sale_id_query.filter(SaleItem.product_id == product_id)
            
            if category_id:
                sale_id_query = sale_id_query.join(Product, SaleItem.product_id == Product.id).filter(
                    Product.category_id == category_id
                )
            
            sale_id_result = await self.db.execute(sale_id_query)
            sale_ids = [row[0] for row in sale_id_result]
            
            if not sale_ids:
                return {"data": [], "total_revenue": 0, "average_revenue": 0, "total_count": 0}
            
            query = query.filter(Sale.id.in_(sale_ids))
        
        query = query.group_by(text("date")).order_by(text("date"))
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        total_revenue = sum(row.revenue for row in rows)
        total_count = sum(row.count for row in rows)
        average_revenue = total_revenue / len(rows) if rows else 0
        
        data = [
            {
                "date": row.date,
                "revenue": float(row.revenue),
                "count": row.count
            }
            for row in rows
        ]
        
        return {
            "data": data,
            "total_revenue": float(total_revenue),
            "average_revenue": float(average_revenue),
            "total_count": total_count
        }

    async def get_category_revenue(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CategoryRevenue]:
        if not end_date:
            end_date = datetime.now()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        query = select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.sum(Sale.total_amount).label("revenue")
        ).join(
            SaleItem, Sale.id == SaleItem.sale_id
        ).join(
            Product, SaleItem.product_id == Product.id
        ).join(
            Category, Product.category_id == Category.id
        ).filter(
            Sale.created_at.between(start_date, end_date)
        ).group_by(
            Category.id,
            Category.name
        ).order_by(
            text("revenue DESC")
        )
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        total_revenue = sum(row.revenue for row in rows)
        
        categories = [
            {
                "category_id": row.category_id,
                "category_name": row.category_name,
                "revenue": float(row.revenue),
                "percentage": float(row.revenue / total_revenue * 100) if total_revenue else 0
            }
            for row in rows
        ]
        
        return categories

    async def get_product_revenue(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
        limit: int = 10
    ) -> List[ProductRevenue]:
        if not end_date:
            end_date = datetime.now()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        query = select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
            Category.name.label("category_name"),
            func.sum(SaleItem.total).label("revenue"),
            func.sum(SaleItem.quantity).label("quantity_sold")
        ).join(
            Sale, SaleItem.sale_id == Sale.id
        ).join(
            Product, SaleItem.product_id == Product.id
        ).join(
            Category, Product.category_id == Category.id
        ).filter(
            Sale.created_at.between(start_date, end_date)
        )
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        query = query.group_by(
            Product.id,
            Product.name,
            Product.sku,
            Category.name
        ).order_by(
            text("revenue DESC")
        ).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        total_revenue = sum(row.revenue for row in rows)
        
        products = [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_sku": row.product_sku,
                "category_name": row.category_name,
                "revenue": float(row.revenue),
                "quantity_sold": row.quantity_sold,
                "percentage": float(row.revenue / total_revenue * 100) if total_revenue else 0
            }
            for row in rows
        ]
        
        return products

    async def get_low_performing_products(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[ProductRevenue]:
        if not end_date:
            end_date = datetime.now()
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        query = select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
            Category.name.label("category_name"),
            func.sum(SaleItem.total).label("revenue"),
            func.sum(SaleItem.quantity).label("quantity_sold")
        ).join(
            Sale, SaleItem.sale_id == Sale.id
        ).join(
            Product, SaleItem.product_id == Product.id
        ).join(
            Category, Product.category_id == Category.id
        ).filter(
            Sale.created_at.between(start_date, end_date)
        ).group_by(
            Product.id,
            Product.name,
            Product.sku,
            Category.name
        ).order_by(
            text("revenue ASC")
        ).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        total_revenue = sum(row.revenue for row in rows)
        
        products = [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_sku": row.product_sku,
                "category_name": row.category_name,
                "revenue": float(row.revenue),
                "quantity_sold": row.quantity_sold,
                "percentage": float(row.revenue / total_revenue * 100) if total_revenue else 0
            }
            for row in rows
        ]
        
        return products 