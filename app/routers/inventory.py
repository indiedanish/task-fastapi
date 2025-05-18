from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from datetime import datetime

from app.database import get_db
from app.models.inventory import Inventory, InventoryChange
from app.models.product import Product
from app.schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryResponse,
    InventoryChangeCreate, InventoryChangeResponse, LowStockAlert
)

router = APIRouter()

@router.post("/", response_model=InventoryResponse, status_code=201)
async def create_inventory(
    inventory: InventoryCreate, 
    db: AsyncSession = Depends(get_db)
):
    product_result = await db.execute(select(Product).filter(Product.id == inventory.product_id))
    product = product_result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    inventory_result = await db.execute(
        select(Inventory).filter(Inventory.product_id == inventory.product_id)
    )
    existing_inventory = inventory_result.scalars().first()
    
    if existing_inventory:
        raise HTTPException(
            status_code=400, 
            detail=f"Inventory already exists for product {inventory.product_id}"
        )
    
    db_inventory = Inventory(**inventory.dict())
    db.add(db_inventory)
    await db.commit()
    await db.refresh(db_inventory)
    
    return db_inventory

@router.get("/", response_model=List[InventoryResponse])
async def get_all_inventory(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Inventory).offset(skip).limit(limit))
    inventory_items = result.scalars().all()
    return inventory_items

@router.get("/low-stock", response_model=List[LowStockAlert])
async def get_low_stock_alerts(
    db: AsyncSession = Depends(get_db)
):
    query = select(
        Inventory.product_id,
        Product.name.label("product_name"),
        Product.sku.label("product_sku"),
        Inventory.quantity.label("current_quantity"),
        Inventory.low_stock_threshold
    ).join(Product).filter(
        Inventory.quantity < Inventory.low_stock_threshold
    )
    
    result = await db.execute(query)
    
    alerts = [
        {
            "product_id": row[0],
            "product_name": row[1],
            "product_sku": row[2],
            "current_quantity": row[3],
            "low_stock_threshold": row[4]
        }
        for row in result
    ]
    
    return alerts

@router.get("/{inventory_id}", response_model=InventoryResponse)
async def get_inventory(
    inventory_id: int, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Inventory).filter(Inventory.id == inventory_id))
    inventory = result.scalars().first()
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    return inventory

@router.get("/product/{product_id}", response_model=InventoryResponse)
async def get_inventory_by_product(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Inventory).filter(Inventory.product_id == product_id))
    inventory = result.scalars().first()
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found for this product")
    
    return inventory

@router.patch("/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(
    inventory_id: int, 
    inventory_update: InventoryUpdate, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Inventory).filter(Inventory.id == inventory_id))
    db_inventory = result.scalars().first()
    
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    update_data = inventory_update.dict(exclude_unset=True)
    
    if "quantity" in update_data and db_inventory.quantity != update_data["quantity"]:
        quantity_change = update_data["quantity"] - db_inventory.quantity
        db_change = InventoryChange(
            inventory_id=inventory_id,
            quantity_change=quantity_change,
            reason=f"Manual update from {db_inventory.quantity} to {update_data['quantity']}"
        )
        db.add(db_change)
    
    if "quantity" in update_data and update_data["quantity"] > db_inventory.quantity:
        update_data["last_restock_date"] = datetime.now()
    
    for key, value in update_data.items():
        setattr(db_inventory, key, value)
    
    await db.commit()
    await db.refresh(db_inventory)
    
    return db_inventory

@router.post("/changes", response_model=InventoryChangeResponse)
async def record_inventory_change(
    change: InventoryChangeCreate, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Inventory).filter(Inventory.id == change.inventory_id))
    inventory = result.scalars().first()
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    db_change = InventoryChange(**change.dict())
    db.add(db_change)
    
    inventory.quantity += change.quantity_change
    
    if change.quantity_change > 0:
        inventory.last_restock_date = datetime.now()
    
    await db.commit()
    await db.refresh(db_change)
    
    return db_change

@router.get("/changes/{inventory_id}", response_model=List[InventoryChangeResponse])
async def get_inventory_changes(
    inventory_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    inv_result = await db.execute(select(Inventory).filter(Inventory.id == inventory_id))
    inventory = inv_result.scalars().first()
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    result = await db.execute(
        select(InventoryChange)
        .filter(InventoryChange.inventory_id == inventory_id)
        .order_by(InventoryChange.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    changes = result.scalars().all()
    
    return changes