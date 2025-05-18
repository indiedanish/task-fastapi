from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter()

@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    category: CategoryCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new category
    """
    db_category = Category(**category.dict())
    
    try:
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        return db_category
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Category with this name already exists")

@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with pagination
    """
    result = await db.execute(select(Category).offset(skip).limit(limit))
    categories = result.scalars().all()
    return categories

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific category by ID
    """
    result = await db.execute(select(Category).filter(Category.id == category_id))
    category = result.scalars().first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category

@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int, 
    category_update: CategoryUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update a category
    """
    result = await db.execute(select(Category).filter(Category.id == category_id))
    db_category = result.scalars().first()
    
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_category, key, value)
    
    try:
        await db.commit()
        await db.refresh(db_category)
        return db_category
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Category with this name already exists")

@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a category
    """
    result = await db.execute(select(Category).filter(Category.id == category_id))
    db_category = result.scalars().first()
    
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    await db.delete(db_category)
    await db.commit()
    
    return None