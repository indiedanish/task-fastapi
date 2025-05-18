# E-commerce Admin API

An API that powers a web admin dashboard for e-commerce managers, providing detailed insights into sales, revenue, and inventory status, as well as allowing new product registration. Built with Python and FastAPI.

## Features

- **Sales Analysis**
  - Retrieve, filter, and analyze sales data
  - Analyze revenue by different time periods (daily, weekly, monthly, yearly)
  - Compare revenue across different periods and categories
  - Filter sales data by date range, product, and category

- **Inventory Management**
  - View current inventory status and low stock alerts
  - Update inventory levels
  - Track inventory changes over time

- **Product Management**
  - Register and manage products
  - Categorize products

- **Analytics**
  - Revenue breakdowns by category and product
  - Performance comparisons across time periods
  - Identify high and low-performing products

## Database Schema

The database schema includes the following tables:

1. **Categories**
   - `id`: Primary key
   - `name`: Category name
   - `description`: Category description

2. **Products**
   - `id`: Primary key
   - `sku`: Stock keeping unit
   - `name`: Product name
   - `description`: Product description
   - `price`: Selling price
   - `cost`: Cost price
   - `category_id`: Foreign key to categories
   - `image_url`: URL to product image
   - `created_at`: Creation timestamp
   - `updated_at`: Update timestamp

3. **Inventory**
   - `id`: Primary key
   - `product_id`: Foreign key to products
   - `quantity`: Current quantity
   - `low_stock_threshold`: Threshold for low stock alerts
   - `last_restock_date`: Date of last restock
   - `created_at`: Creation timestamp
   - `updated_at`: Update timestamp

4. **Inventory Changes**
   - `id`: Primary key
   - `inventory_id`: Foreign key to inventory
   - `quantity_change`: Change in quantity
   - `reason`: Reason for change
   - `created_at`: Timestamp of change

5. **Sales**
   - `id`: Primary key
   - `reference_number`: Unique reference number
   - `total_amount`: Total sale amount
   - `tax_amount`: Tax amount
   - `discount_amount`: Discount amount
   - `payment_method`: Payment method
   - `customer_name`: Customer name
   - `customer_email`: Customer email
   - `notes`: Additional notes
   - `created_at`: Sale timestamp

6. **Sale Items**
   - `id`: Primary key
   - `sale_id`: Foreign key to sales
   - `product_id`: Foreign key to products
   - `quantity`: Quantity sold
   - `price`: Price at time of sale
   - `discount`: Discount applied
   - `total`: Total for the item

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ecommerce-admin-api.git
   cd ecommerce-admin-api
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your database connection string:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/ecommerce
   ```

5. Run the application:
   ```bash
   npm run dev
   ```

6. Seed the database with demo data:
   ```bash
   npm run seed
   ```

## API Endpoints

Once the application is running, you can access the Swagger UI documentation at:
```
http://localhost:8000/docs
```

This provides a detailed, interactive documentation of all available endpoints.

### Key Endpoints

#### Categories
- `GET /api/categories` - Get all categories
- `POST /api/categories` - Create a new category
- `GET /api/categories/{category_id}` - Get a specific category
- `PATCH /api/categories/{category_id}` - Update a category
- `DELETE /api/categories/{category_id}` - Delete a category

#### Products
- `GET /api/products` - Get all products
- `POST /api/products` - Create a new product
- `GET /api/products/{product_id}` - Get a specific product
- `PATCH /api/products/{product_id}` - Update a product
- `DELETE /api/products/{product_id}` - Delete a product
- `GET /api/products/with-inventory` - Get products with inventory info

#### Inventory
- `GET /api/inventory` - Get all inventory
- `GET /api/inventory/low-stock` - Get low stock alerts
- `GET /api/inventory/{inventory_id}` - Get specific inventory
- `PATCH /api/inventory/{inventory_id}` - Update inventory
- `POST /api/inventory/changes` - Record inventory change
- `GET /api/inventory/changes/{inventory_id}` - Get inventory changes

#### Sales
- `GET /api/sales` - Get all sales
- `POST /api/sales` - Create a new sale
- `GET /api/sales/{sale_id}` - Get a specific sale
- `POST /api/sales/filter` - Filter sales

#### Analytics
- `GET /api/analytics/revenue` - Get revenue data
- `POST /api/analytics/compare-periods` - Compare revenue between periods
- `GET /api/analytics/category-revenue` - Get revenue by category
- `GET /api/analytics/product-revenue` - Get revenue by product
- `GET /api/analytics/low-performing-products` - Get low performing products

## License

This project is licensed under the MIT License.