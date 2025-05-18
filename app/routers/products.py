from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.product import Product
from app.models.inventory import Inventory
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductWithInventory

router = APIRouter()

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product
    """
    db_product = Product(**product.dict())
    
    try:
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        
        # Create default inventory for the product
        db_inventory = Inventory(product_id=db_product.id, quantity=0, low_stock_threshold=10)
        db.add(db_inventory)
        await db.commit()
        
        return db_product
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")

@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0, 
    limit: int = 100, 
    category_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products with optional category filter and pagination
    """
    query = select(Product)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()
    
    return products

@router.get("/with-inventory", response_model=List[ProductWithInventory])
async def get_products_with_inventory(
    skip: int = 0, 
    limit: int = 100, 
    category_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products with their inventory information
    """
    query = select(
        Product.id, Product.sku, Product.name, Product.description,
        Product.price, Product.cost, Product.category_id, Product.image_url,
        Product.created_at, Product.updated_at,
        Inventory.quantity, Inventory.low_stock_threshold
    ).join(Inventory)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    
    products = [
        {
            "id": row[0],
            "sku": row[1],
            "name": row[2],
            "description": row[3],
            "price": row[4],
            "cost": row[5],
            "category_id": row[6],
            "image_url": row[7],
            "created_at": row[8],
            "updated_at": row[9],
            "quantity": row[10],
            "low_stock_threshold": row[11]
        }
        for row in result
    ]
    
    return products

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific product by ID
    """
    result = await db.execute(select(Product).filter(Product.id == product_id))
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int, 
    product_update: ProductUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update a product
    """
    result = await db.execute(select(Product).filter(Product.id == product_id))
    db_product = result.scalars().first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    try:
        await db.commit()
        await db.refresh(db_product)
        return db_product
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")

@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product
    """
    result = await db.execute(select(Product).filter(Product.id == product_id))
    db_product = result.scalars().first()
    
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.delete(db_product)
    await db.commit()
    
    return None