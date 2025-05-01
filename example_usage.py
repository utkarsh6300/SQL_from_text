from vectorStore.chroma import ChromaDB_VectorStore
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os

def main():
    load_dotenv()
    
    # Initialize OpenAI embedding function
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-ada-002"
    )
    
    # Initialize the vector store with OpenAI embeddings
    vector_store = ChromaDB_VectorStore(config={
        "path": "./chroma_db_new",  # Using a new database path
        "client": "persistent",  # Use persistent storage
        "n_results": 5,  # Default number of results to return for queries
        "embedding_function": openai_ef  # Use OpenAI embeddings
    })

    # Add some example SQL questions and queries
    vector_store.add_question_sql(
        question="What is the total sales for each product category?",
        sql="SELECT category, SUM(sales_amount) as total_sales FROM sales GROUP BY category"
    )

    vector_store.add_question_sql(
        question="Who are our top 10 customers by revenue?",
        sql="SELECT customer_name, SUM(amount) as total_revenue FROM orders GROUP BY customer_name ORDER BY total_revenue DESC LIMIT 10"
    )

    # Add some DDL examples
    vector_store.add_ddl("""
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Add documentation
    vector_store.add_documentation("""
    The sales table contains all transaction records.
    Fields:
    - transaction_id: Unique identifier for each sale
    - product_id: Reference to products table
    - customer_id: Reference to customers table
    - amount: Transaction amount in USD
    - transaction_date: Date and time of the sale
    """)

    # Query for similar SQL questions
    similar_queries = vector_store.get_similar_question_sql(
        question="How much revenue did each customer generate?"
    )
    print("\nSimilar SQL queries:", similar_queries)

    # Get related DDL
    related_ddl = vector_store.get_related_ddl(
        question="customer table schema"
    )
    print("\nRelated DDL:", related_ddl)

    # Get related documentation
    related_docs = vector_store.get_related_documentation(
        question="sales table structure"
    )
    print("\nRelated Documentation:", related_docs)

    # Get all training data
    training_data = vector_store.get_training_data()
    print("\nTraining Data Shape:", training_data.shape)

if __name__ == "__main__":
    main()