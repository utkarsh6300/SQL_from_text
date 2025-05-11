import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from generator.sql import SQLGenerator
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    # Initialize SQL Generator
    generator = SQLGenerator()

    # Add some example schema
    schema = """
    CREATE TABLE products (
        product_id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        category VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE customers (
        customer_id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE orders (
        order_id SERIAL PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(customer_id),
        product_id INTEGER REFERENCES products(product_id),
        quantity INTEGER NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    generator.add_schema_context(schema)

    # Add some example queries for training
    example_queries = [
        {
            "question": "Find all products in electronics category",
            "sql": "SELECT * FROM products WHERE category = 'electronics'"
        },
        {
            "question": "Show total sales by category",
            "sql": "SELECT category, SUM(total_amount) as total_sales FROM products p JOIN orders o ON p.product_id = o.product_id GROUP BY category"
        },
        {
            "question": "List customers who spent more than $1000",
            "sql": "SELECT c.name, SUM(o.total_amount) as total_spent FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name HAVING SUM(o.total_amount) > 1000"
        },
        # Adding 5 more examples
        {
            "question": "Find the most recent orders from the last 7 days",
            "sql": "SELECT o.*, c.name as customer_name, p.name as product_name FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN products p ON o.product_id = p.product_id WHERE o.order_date >= CURRENT_TIMESTAMP - INTERVAL '7 days'"
        },
        {
            "question": "Calculate average order value by customer",
            "sql": "SELECT c.name, AVG(o.total_amount) as avg_order_value FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name ORDER BY avg_order_value DESC"
        },
        {
            "question": "Find products that have never been ordered",
            "sql": "SELECT p.* FROM products p LEFT JOIN orders o ON p.product_id = o.product_id WHERE o.order_id IS NULL"
        },
        {
            "question": "Show customers who made purchases in all categories",
            "sql": "SELECT c.name FROM customers c WHERE NOT EXISTS (SELECT DISTINCT category FROM products WHERE category IS NOT NULL EXCEPT SELECT DISTINCT p.category FROM orders o JOIN products p ON o.product_id = p.product_id WHERE o.customer_id = c.customer_id)"
        },
        {
            "question": "Get monthly revenue trend for the past year",
            "sql": "SELECT DATE_TRUNC('month', order_date) as month, SUM(total_amount) as monthly_revenue FROM orders WHERE order_date >= CURRENT_TIMESTAMP - INTERVAL '1 year' GROUP BY DATE_TRUNC('month', order_date) ORDER BY month"
        }
    ]
    generator.train_from_examples(example_queries)

    # Add some documentation
    generator.add_documentation("""
    Database Schema Documentation:
    - products table stores product information including name, price and category
    - customers table contains customer details with email being unique
    - orders table tracks all orders with references to customers and products
    """)

    # Test some queries
    test_questions = [
        "What are the top 5 selling products?",
        "How many orders did each customer place?",
        "Find products priced above $100",
        "Show total revenue by month"
    ]

    print("\nTesting SQL Generation:")
    print("-" * 50)
    for question in test_questions:
        print(f"\nQuestion: {question}")
        sql = generator.generate_sql(question)
        print(f"Generated SQL: {sql}")

if __name__ == "__main__":
    main()