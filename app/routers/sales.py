from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, between
from datetime import datetime, timedelta
import uuid

from app.database import get_db
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.inventory import Inventory, InventoryChange
from app.schemas.sale import SaleCreate, SaleResponse, SaleFilter

router = APIRouter()

@router.post("/", response_model=SaleResponse, status_code=201)
async def create_sale(
    sale: SaleCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new sale with items
    """
    # Generate a unique reference number
    reference_number = f"SALE-{uuid.uuid4().hex[:8].upper()}"
    
    # Create the sale
    db_sale = Sale(
        reference_number=reference_number,
        total_amount=sale.total_amount,
        tax_amount=sale.tax_amount,
        discount_amount=sale.discount_amount,
        payment_method=sale.payment_method,
        customer_name=sale.customer_name,
        customer_email=sale.customer_email,
        notes=sale.notes
    )
    
    db.add(db_sale)
    await db.commit()
    await db.refresh(db_sale)
    
    # Create the sale items and update inventory
    for item in sale.items:
        db_sale_item = SaleItem(
            sale_id=db_sale.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            discount=item.discount,
            total=item.total
        )
        
        db.add(db_sale_item)
        
        # Update inventory
        result = await db.execute(
            select(Inventory).filter(Inventory.product_id == item.product_id)
        )
        inventory = result.scalars().first()
        
        if inventory:
            # Record inventory change
            db_change = InventoryChange(
                inventory_id=inventory.id,
                quantity_change=-item.quantity,  # Negative because we're selling
                reason=f"Sale: {reference_number}"
            )
            db.add(db_change)
            
            # Update inventory quantity
            inventory.quantity -= item.quantity
    
    await db.commit()
    
    # Get the complete sale with items
    result = await db.execute(
        select(Sale)
        .filter(Sale.id == db_sale.id)
    )
    
    created_sale = result.scalars().first()
    
    # Get product names for the response
    for item in created_sale.items:
        result = await db.execute(select(Product).filter(Product.id == item.product_id))
        product = result.scalars().first()
        if product:
            setattr(item, "product_name", product.name)
    
    return created_sale

@router.get("/", response_model=List[SaleResponse])
async def get_sales(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    product_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all sales with optional filtering and pagination
    """
    query = select(Sale)
    
    # Apply filters
    filters = []
    
    if start_date:
        filters.append(Sale.created_at >= start_date)
    
    if end_date:
        filters.append(Sale.created_at <= end_date)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Product and category filters require joins and subqueries, so we'll handle them separately
    if product_id or category_id:
        # First, get the sale IDs that match our product/category filter
        sale_id_query = select(SaleItem.sale_id).distinct()
        
        if product_id:
            sale_id_query = sale_id_query.filter(SaleItem.product_id == product_id)
        
        if category_id:
            sale_id_query = sale_id_query.join(Product, SaleItem.product_id == Product.id).filter(
                Product.category_id == category_id
            )
        
        sale_id_result = await db.execute(sale_id_query)
        sale_ids = [row[0] for row in sale_id_result]
        
        if not sale_ids:
            return []
        
        query = query.filter(Sale.id.in_(sale_ids))
    
    # Apply pagination
    query = query.order_by(Sale.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    sales = result.scalars().all()
    
    # Create a list to hold our processed sales
    processed_sales = []
    
    # Explicitly load the items for each sale to avoid lazy loading issues
    for sale in sales:
        # Create a new dict or object to hold the sale data
        sale_dict = {
            "id": sale.id,
            "reference_number": sale.reference_number,
            "total_amount": sale.total_amount,
            "tax_amount": sale.tax_amount,
            "discount_amount": sale.discount_amount,
            "payment_method": sale.payment_method,
            "customer_name": sale.customer_name,
            "customer_email": sale.customer_email,
            "notes": sale.notes,
            "created_at": sale.created_at,
            "items": []
        }
        
        # Explicitly load items for each sale
        items_result = await db.execute(
            select(SaleItem).filter(SaleItem.sale_id == sale.id)
        )
        sale_items = items_result.scalars().all()
        
        # Process each item and add to the sale_dict
        for item in sale_items:
            item_dict = {
                "id": item.id,
                "sale_id": item.sale_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "discount": item.discount,
                "total": item.total
            }
            
            # Get product name
            product_result = await db.execute(select(Product).filter(Product.id == item.product_id))
            product = product_result.scalars().first()
            if product:
                item_dict["product_name"] = product.name
            
            sale_dict["items"].append(item_dict)
        
        processed_sales.append(sale_dict)
    
    return processed_sales

@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific sale by ID
    """
    result = await db.execute(select(Sale).filter(Sale.id == sale_id))
    sale = result.scalars().first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    # Create a dictionary to hold the sale data
    sale_dict = {
        "id": sale.id,
        "reference_number": sale.reference_number,
        "total_amount": sale.total_amount,
        "tax_amount": sale.tax_amount,
        "discount_amount": sale.discount_amount,
        "payment_method": sale.payment_method,
        "customer_name": sale.customer_name,
        "customer_email": sale.customer_email,
        "notes": sale.notes,
        "created_at": sale.created_at,
        "items": []
    }
    
    # Explicitly load items for the sale
    items_result = await db.execute(
        select(SaleItem).filter(SaleItem.sale_id == sale.id)
    )
    sale_items = items_result.scalars().all()
    
    # Process each item and add to the sale_dict
    for item in sale_items:
        item_dict = {
            "id": item.id,
            "sale_id": item.sale_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": item.price,
            "discount": item.discount,
            "total": item.total
        }
        
        # Get product name
        product_result = await db.execute(select(Product).filter(Product.id == item.product_id))
        product = product_result.scalars().first()
        if product:
            item_dict["product_name"] = product.name
        
        sale_dict["items"].append(item_dict)
    
    return sale_dict

@router.post("/filter", response_model=List[SaleResponse])
async def filter_sales(
    filter_params: SaleFilter,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Advanced filtering of sales
    """
    query = select(Sale)
    
    # Apply filters
    filters = []
    
    if filter_params.start_date:
        filters.append(Sale.created_at >= filter_params.start_date)
    
    if filter_params.end_date:
        filters.append(Sale.created_at <= filter_params.end_date)
    
    if filter_params.min_amount is not None:
        filters.append(Sale.total_amount >= filter_params.min_amount)
    
    if filter_params.max_amount is not None:
        filters.append(Sale.total_amount <= filter_params.max_amount)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Product and category filters require joins and subqueries
    if filter_params.product_id or filter_params.category_id:
        sale_id_query = select(SaleItem.sale_id).distinct()
        
        if filter_params.product_id:
            sale_id_query = sale_id_query.filter(SaleItem.product_id == filter_params.product_id)
        
        if filter_params.category_id:
            sale_id_query = sale_id_query.join(Product, SaleItem.product_id == Product.id).filter(
                Product.category_id == filter_params.category_id
            )
        
        sale_id_result = await db.execute(sale_id_query)
        sale_ids = [row[0] for row in sale_id_result]
        
        if not sale_ids:
            return []
        
        query = query.filter(Sale.id.in_(sale_ids))
    
    # Apply pagination
    query = query.order_by(Sale.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    sales = result.scalars().all()
    
    # Explicitly load the items for each sale
    for sale in sales:
        # Explicitly load items for each sale
        items_result = await db.execute(
            select(SaleItem).filter(SaleItem.sale_id == sale.id)
        )
        sale_items = items_result.scalars().all()
        
        # Get product names for each sale item
        for item in sale_items:
            product_result = await db.execute(select(Product).filter(Product.id == item.product_id))
            product = product_result.scalars().first()
            if product:
                setattr(item, "product_name", product.name)
        
        # Manually set the items attribute
        sale.items = sale_items
    
    return sales