from generator.sql import SQLGenerator
from index import get_schema
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    # Initialize connection parameters
    connection_params = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 5432))
    }

    # Initialize SQL Generator
    generator = SQLGenerator()

    # Get database schema
    schema = get_schema(connection_params)
    
    # Add schema context to vector store
    generator.add_schema_context(schema)

    # Add some example queries for training
    example_queries = [
        {
            "question": "Show all users who signed up in the last month",
            "sql": "SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '1 month'"
        },
        {
            "question": "Find total number of orders by customer",
            "sql": "SELECT customer_id, COUNT(*) as total_orders FROM orders GROUP BY customer_id"
        }
    ]
    generator.train_from_examples(example_queries)

    # Add some documentation
    generator.add_documentation("""
    The users table contains user account information including:
    - user_id: Primary key
    - email: User's email address
    - created_at: Timestamp when user signed up
    - status: Account status (active/inactive)
    """)

    # Test the SQL generation
    questions = [
        "How many active users do we have?",
        "What is the average number of orders per customer?",
        "List all orders from last week"
    ]

    print("Generating SQL queries for test questions:")
    print("-" * 50)
    for question in questions:
        print(f"\nQuestion: {question}")
        sql = generator.generate_sql(question)
        print(f"Generated SQL: {sql}")

if __name__ == "__main__":
    main()