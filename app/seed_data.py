import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
import uuid
import sys
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import ASYNC_DATABASE_URL, Base
from app.models.category import Category
from app.models.product import Product
from app.models.inventory import Inventory, InventoryChange
from app.models.sale import Sale, SaleItem, PaymentMethod

# Categories for Amazon and Walmart products
CATEGORIES = [
    {"name": "Electronics", "description": "Electronic devices and accessories"},
    {"name": "Home & Kitchen", "description": "Home appliances and kitchen essentials"},
    {"name": "Clothing", "description": "Apparel and fashion accessories"},
    {"name": "Beauty & Personal Care", "description": "Beauty products and personal care items"},
    {"name": "Grocery", "description": "Food and beverage items"},
    {"name": "Toys & Games", "description": "Toys, games, and entertainment products"},
    {"name": "Sports & Outdoors", "description": "Sports equipment and outdoor gear"},
    {"name": "Books", "description": "Books, e-books, and reading materials"}
]

# Sample products
PRODUCTS = [
    # Electronics
    {"sku": "AMZN-E001", "name": "Amazon Echo Dot (4th Gen)", "price": 49.99, "cost": 25.00, "category_index": 0},
    {"sku": "AMZN-E002", "name": "Amazon Fire TV Stick 4K", "price": 39.99, "cost": 20.00, "category_index": 0},
    {"sku": "AMZN-E003", "name": "Amazon Kindle Paperwhite", "price": 139.99, "cost": 70.00, "category_index": 0},
    {"sku": "WMT-E001", "name": "Walmart onn. 50\" 4K UHD TV", "price": 268.00, "cost": 180.00, "category_index": 0},
    {"sku": "WMT-E002", "name": "Walmart onn. Tablet Pro 10.1\"", "price": 129.00, "cost": 80.00, "category_index": 0},
    
    # Home & Kitchen
    {"sku": "AMZN-H001", "name": "Amazon Basics Microwave", "price": 59.99, "cost": 35.00, "category_index": 1},
    {"sku": "AMZN-H002", "name": "Amazon Smart Thermostat", "price": 79.99, "cost": 45.00, "category_index": 1},
    {"sku": "WMT-H001", "name": "Mainstays Stainless Steel Cookware Set", "price": 49.98, "cost": 25.00, "category_index": 1},
    {"sku": "WMT-H002", "name": "Keurig K-Express Coffee Maker", "price": 59.00, "cost": 35.00, "category_index": 1},
    
    # Clothing
    {"sku": "AMZN-C001", "name": "Amazon Essentials Men's T-Shirt", "price": 12.99, "cost": 5.00, "category_index": 2},
    {"sku": "AMZN-C002", "name": "Amazon Essentials Women's Cardigan", "price": 29.99, "cost": 12.00, "category_index": 2},
    {"sku": "WMT-C001", "name": "George Men's Regular Fit Jeans", "price": 16.98, "cost": 8.00, "category_index": 2},
    {"sku": "WMT-C002", "name": "Time and Tru Women's Knit Dress", "price": 14.98, "cost": 6.00, "category_index": 2},
    
    # Beauty & Personal Care
    {"sku": "AMZN-B001", "name": "Solimo Body Wash", "price": 5.99, "cost": 2.00, "category_index": 3},
    {"sku": "AMZN-B002", "name": "Amazon Elements Vitamin D3", "price": 10.99, "cost": 3.00, "category_index": 3},
    {"sku": "WMT-B001", "name": "Equate Beauty Face Cleanser", "price": 4.27, "cost": 1.50, "category_index": 3},
    {"sku": "WMT-B002", "name": "Equate Men's 5-Blade Razor", "price": 7.97, "cost": 3.00, "category_index": 3},
    
    # Grocery
    {"sku": "AMZN-G001", "name": "Happy Belly Coffee Pods", "price": 19.99, "cost": 10.00, "category_index": 4},
    {"sku": "AMZN-G002", "name": "Amazon Fresh Organic Bananas", "price": 1.99, "cost": 0.80, "category_index": 4},
    {"sku": "WMT-G001", "name": "Great Value Organic Milk", "price": 3.97, "cost": 2.00, "category_index": 4},
    {"sku": "WMT-G002", "name": "Great Value Sliced Bread", "price": 0.97, "cost": 0.40, "category_index": 4},
    
    # Toys & Games
    {"sku": "AMZN-T001", "name": "Amazon Basics Building Blocks", "price": 19.99, "cost": 8.00, "category_index": 5},
    {"sku": "AMZN-T002", "name": "Fire HD 8 Kids tablet", "price": 139.99, "cost": 70.00, "category_index": 5},
    {"sku": "WMT-T001", "name": "Play Day Outdoor Swing Set", "price": 149.00, "cost": 85.00, "category_index": 5},
    {"sku": "WMT-T002", "name": "KidKraft Wooden Kitchen Playset", "price": 99.00, "cost": 60.00, "category_index": 5},
    
    # Sports & Outdoors
    {"sku": "AMZN-S001", "name": "Amazon Basics Yoga Mat", "price": 19.99, "cost": 8.00, "category_index": 6},
    {"sku": "AMZN-S002", "name": "Amazon Basics Dumbbell Set", "price": 49.99, "cost": 25.00, "category_index": 6},
    {"sku": "WMT-S001", "name": "Athletic Works Resistance Bands", "price": 9.98, "cost": 3.00, "category_index": 6},
    {"sku": "WMT-S002", "name": "Ozark Trail Camping Tent", "price": 79.00, "cost": 45.00, "category_index": 6},
    
    # Books
    {"sku": "AMZN-BK001", "name": "Amazon Publishing Best Seller Fiction", "price": 12.99, "cost": 3.00, "category_index": 7},
    {"sku": "AMZN-BK002", "name": "Amazon Publishing Cookbook", "price": 24.99, "cost": 8.00, "category_index": 7},
    {"sku": "WMT-BK001", "name": "Children's Learning Workbook", "price": 5.98, "cost": 2.00, "category_index": 7},
    {"sku": "WMT-BK002", "name": "Popular Fiction Paperback", "price": 7.98, "cost": 3.00, "category_index": 7}
]

# Payment methods to use randomly
PAYMENT_METHODS = [
    PaymentMethod.CREDIT_CARD,
    PaymentMethod.DEBIT_CARD,
    PaymentMethod.PAYPAL,
    PaymentMethod.BANK_TRANSFER,
    PaymentMethod.CASH
]

# Sample customer information
CUSTOMERS = [
    {"name": "John Doe", "email": "john.doe@example.com"},
    {"name": "Jane Smith", "email": "jane.smith@example.com"},
    {"name": "Michael Johnson", "email": "michael.johnson@example.com"},
    {"name": "Emily Davis", "email": "emily.davis@example.com"},
    {"name": "Robert Wilson", "email": "robert.wilson@example.com"},
    {"name": "Sarah Brown", "email": "sarah.brown@example.com"},
    {"name": "David Lee", "email": "david.lee@example.com"},
    {"name": "Lisa Taylor", "email": "lisa.taylor@example.com"},
    {"name": "James Anderson", "email": "james.anderson@example.com"},
    {"name": "Patricia Martinez", "email": "patricia.martinez@example.com"},
    {"name": None, "email": None}  # For anonymous purchases
]

async def seed_database():
    """
    Seed the database with demo data
    """
    # Create engine with proper SSL settings for asyncpg
    # Parse the URL to remove sslmode parameter
    parsed_url = urlparse(ASYNC_DATABASE_URL)
    query_params = parse_qs(parsed_url.query)
    
    # Remove sslmode from query parameters
    if 'sslmode' in query_params:
        del query_params['sslmode']
    
    # Reconstruct URL without sslmode
    clean_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        urlencode(query_params, doseq=True),
        parsed_url.fragment
    ))
    
    engine = create_async_engine(
        clean_url,
        echo=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Seed categories
        categories = []
        for category_data in CATEGORIES:
            category = Category(**category_data)
            session.add(category)
            categories.append(category)
        
        await session.commit()
        
        # Refresh categories to get their IDs
        for category in categories:
            await session.refresh(category)
        
        # Seed products
        products = []
        for product_data in PRODUCTS:
            category_index = product_data.pop("category_index")
            product = Product(
                **product_data,
                category_id=categories[category_index].id,
                description=f"Description for {product_data['name']}",
                image_url=f"https://example.com/images/{product_data['sku'].lower()}.jpg"
            )
            session.add(product)
            products.append(product)
        
        await session.commit()
        
        # Refresh products to get their IDs
        for product in products:
            await session.refresh(product)
        
        # Seed inventory
        inventories = []
        for product in products:
            # Random inventory quantity between 10 and 100
            quantity = random.randint(10, 100)
            inventory = Inventory(
                product_id=product.id,
                quantity=quantity,
                low_stock_threshold=random.randint(5, 15),
                last_restock_date=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            session.add(inventory)
            inventories.append(inventory)
        
        await session.commit()
        
        # Refresh inventories to get their IDs
        for inventory in inventories:
            await session.refresh(inventory)
        
        # Seed inventory changes (for history)
        for inventory in inventories:
            # Add a few random inventory changes
            for _ in range(random.randint(2, 5)):
                change_quantity = random.randint(5, 20) * (1 if random.random() > 0.3 else -1)
                change = InventoryChange(
                    inventory_id=inventory.id,
                    quantity_change=change_quantity,
                    reason="Initial stock" if change_quantity > 0 else "Inventory adjustment",
                    created_at=datetime.now() - timedelta(days=random.randint(1, 60))
                )
                session.add(change)
        
        await session.commit()
        
        # Seed sales data for the last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        current_date = start_date
        
        # Create more sales for recent dates to show growth
        while current_date <= end_date:
            # Number of sales per day increases as we get closer to the present
            days_ago = (end_date - current_date).days
            sales_count = max(1, int(10 - (days_ago / 10)))
            
            for _ in range(sales_count):
                # Create a sale
                customer = random.choice(CUSTOMERS)
                payment_method = random.choice(PAYMENT_METHODS)
                
                # Generate a reference number
                reference_number = f"SALE-{uuid.uuid4().hex[:8].upper()}"
                
                # Determine how many items in this sale (1-5)
                num_items = random.randint(1, 5)
                sale_items_data = []
                total_amount = 0
                
                # Choose random products
                sale_products = random.sample(products, num_items)
                
                for product in sale_products:
                    quantity = random.randint(1, 3)
                    
                    # Apply a random discount sometimes
                    discount = round(product.price * random.choice([0, 0, 0, 0.05, 0.1, 0.15]), 2) if random.random() > 0.7 else 0
                    
                    # Calculate total for this item
                    item_total = round((product.price - discount) * quantity, 2)
                    total_amount += item_total
                    
                    sale_items_data.append({
                        "product_id": product.id,
                        "quantity": quantity,
                        "price": product.price,
                        "discount": discount,
                        "total": item_total
                    })
                
                # Apply tax (random between 5% and 10%)
                tax_rate = random.uniform(0.05, 0.1)
                tax_amount = round(total_amount * tax_rate, 2)
                
                # Apply order-level discount sometimes
                order_discount = round(total_amount * random.choice([0, 0, 0, 0.05, 0.1]), 2) if random.random() > 0.8 else 0
                
                # Final total
                final_total = round(total_amount + tax_amount - order_discount, 2)
                
                # Create the sale with a timestamp within the current day
                sale_time = current_date.replace(
                    hour=random.randint(8, 20),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                sale = Sale(
                    reference_number=reference_number,
                    total_amount=final_total,
                    tax_amount=tax_amount,
                    discount_amount=order_discount,
                    payment_method=payment_method,
                    customer_name=customer["name"],
                    customer_email=customer["email"],
                    notes="Demo sale data",
                    created_at=sale_time
                )
                
                session.add(sale)
                await session.commit()
                await session.refresh(sale)
                
                # Add the sale items
                for item_data in sale_items_data:
                    sale_item = SaleItem(
                        sale_id=sale.id,
                        **item_data
                    )
                    session.add(sale_item)
                    
                    # Update inventory
                    inventory_result = await session.execute(
                        select(Inventory).filter(Inventory.product_id == item_data["product_id"])
                    )
                    inventory = inventory_result.scalars().first()
                    
                    if inventory:
                        # Record inventory change
                        inventory_change = InventoryChange(
                            inventory_id=inventory.id,
                            quantity_change=-item_data["quantity"],
                            reason=f"Sale: {reference_number}",
                            created_at=sale_time
                        )
                        session.add(inventory_change)
                        
                        # Update inventory quantity
                        inventory.quantity -= item_data["quantity"]
                
                await session.commit()
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())