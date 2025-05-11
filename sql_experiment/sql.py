# TODO: generate sql from text using the OpenAI API
# hybrid of cag + rag
# use table agent(Allowing users to select the tables used in the query generation came up as feedback from some users who saw that the tables that were eventually picked)
# Column Prune Agent (LLM call to prune the irrelevant columns from the schemas)

import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
from openai import OpenAI
import json
from vectorStore.chroma import ChromaDB_VectorStore
from chromadb.utils import embedding_functions
from typing import Any, Dict

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

connection_params_example = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432))
}  # creds should be view only.

# Initialize OpenAI embedding function and vector store
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-ada-002"
)

vector_store = ChromaDB_VectorStore(config={
    "path": "./chroma_db_new",
    "client": "persistent",
    "n_results": 5,
    "embedding_function": openai_ef
})

def generate_sql_from_text(input_text: str, schema_info: dict, interactive: bool = False) -> str:
    """
    Generate SQL query from natural language text input.
    
    Args:
        input_text: The natural language query
        schema_info: Database schema information
        interactive: Whether to prompt for table selection interactively
    
    Returns:
        str: Generated SQL query or None if generation fails
    """
    if not input_text or not schema_info:
        raise ValueError("Input text and schema information are required")

    try:
        # Get similar questions and their SQL queries
        similar_queries = vector_store.get_similar_question_sql(input_text)
        print(f"Found {len(similar_queries) if similar_queries else 0} similar queries")
        
        # Get related schema information
        schema_context = vector_store.get_related_ddl(input_text)
        print(f"Retrieved schema context: {len(schema_context) if schema_context else 0} items")
        
        # Get related documentation
        docs_context = vector_store.get_related_documentation(input_text)
        print(f"Retrieved documentation context: {len(docs_context) if docs_context else 0} items")
        
        # Prepare context with truncation
        context = prepare_context(similar_queries, schema_context, docs_context)

        # Step 1: Context Retrieval - Identify relevant tables with truncated schema
        schema_summary = str(schema_info)
        if len(schema_summary) > 4000:  # Truncate schema if too long
            schema_summary = schema_summary[:4000] + "... (schema truncated)"

        table_response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use 3.5-turbo for better token management
            messages=[
                {
                    "role": "system",
                    "content": """You are a database schema analyst. Your task is to:
1. Analyze the user query and context carefully
2. Identify tables that are directly relevant to answering the query
3. Return ONLY a JSON array of table names
4. Consider table relationships and joins that might be needed

Ensure your response contains only the JSON array."""
                },
                {
                    "role": "user",
                    "content": f"""
User Query: {input_text}
Schema Summary: {schema_summary}

Return a JSON array of relevant table names."""
                }
            ]
        )

        suggested_tables = json.loads(table_response.choices[0].message.content)
        print("Suggested Tables:", suggested_tables)

        # Step 2: Table Selection
        if interactive:
            selected_tables = input("Enter the selected tables as a JSON array (e.g., [\"sales\", \"employees\"]): ")
            selected_tables = json.loads(selected_tables)
        else:
            selected_tables = suggested_tables

        if not selected_tables:
            raise ValueError("No tables were selected for query generation")

        # Step 3: Column Pruning with context
        column_prune_response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Switch to 3.5-turbo
            messages=[
                {
                    "role": "system",
                    "content": """You are a database optimization expert. Your task is to:
1. Analyze the selected tables and user query
2. Identify only the columns necessary to:
   - Filter the data (WHERE conditions)
   - Join tables (key relationships)
   - Display in the final result
3. Return a JSON object mapping tables to their required columns
4. Include primary/foreign keys even if not directly queried

"""
                },
                {
                    "role": "user",
                    "content": f"""
Given the following context:
{context}

User Query: {input_text}
Selected Tables: {json.dumps(selected_tables)}

Return a JSON object mapping table names to arrays of relevant column names."""
                }
            ]
        )

        try:
            refined_columns = json.loads(column_prune_response.choices[0].message.content)
        except json.JSONDecodeError:
            print("Warning: Failed to parse column pruning response as JSON")
            refined_columns = column_prune_response.choices[0].message.content
        print("Refined Columns:", refined_columns)

        # Step 4: SQL Query Generation with context
        sql_response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Switch to 3.5-turbo
            messages=[
                {
                    "role": "system",
                    "content": """You are an SQL optimization expert. Your task is to:
1. Generate a SQL query that is:
   - Efficient (using appropriate indexes)
   - Standards-compliant
   - Safe from SQL injection
2. Include necessary JOIN conditions
3. Use specific column names (no SELECT *)
4. Add appropriate aliases for readability
5. Return ONLY the SQL query without any explanation or markdown

Follow the schema structure exactly as provided."""
                },
                {
                    "role": "user",
                    "content": f"""
Given the following context:
{context}

User Query: {input_text}
Refined Schema: {refined_columns}

Generate only the SQL query without any explanation."""
                }
            ]
        )

        sql_query = sql_response.choices[0].message.content.strip()
        if not sql_query:
            raise ValueError("Generated SQL query is empty")
            
        print("Generated SQL Query:", sql_query)
        return sql_query

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        return None
    except Exception as error:
        print(f"Error generating SQL: {str(error)}")
        return None

def prepare_context(similar_queries, schema_context, docs_context):
    """
    Prepare context string from vector store results with intelligent truncation.
    """
    MAX_CONTEXT_LENGTH = 4000  # Reserve space for messages and other content
    context_parts = []
    
    # Add most relevant similar queries (limit to 3)
    if similar_queries:
        context_parts.append("Similar queries:")
        for i, query in enumerate(similar_queries[:3]):
            if isinstance(query, dict) and 'question' in query and 'sql' in query:
                context_parts.append(f"Question: {query['question']}")
                context_parts.append(f"SQL: {query['sql']}\n")
    
    # Add schema context (truncated if needed)
    if schema_context:
        context_parts.append("Database schema:")
        # Only include relevant table definitions
        schema_text = "\n".join(schema_context[:3])  # Limit to 3 most relevant tables
        if len(schema_text) > MAX_CONTEXT_LENGTH // 2:
            schema_text = schema_text[:MAX_CONTEXT_LENGTH // 2] + "\n... (schema truncated)"
        context_parts.append(schema_text)
    
    # Add documentation context (truncated if needed)
    if docs_context:
        context_parts.append("\nAdditional context:")
        docs_text = "\n".join(docs_context[:2])  # Limit to 2 most relevant docs
        remaining_length = MAX_CONTEXT_LENGTH - len("\n".join(context_parts))
        if len(docs_text) > remaining_length:
            docs_text = docs_text[:remaining_length] + "\n... (documentation truncated)"
        context_parts.append(docs_text)
    
    return "\n".join(context_parts)

def get_schema(connection_params: Dict[str, Any]) -> str:
    """
    Retrieve a detailed database schema from a PostgreSQL database.

    Args:
        connection_params (Dict[str, Any]): The connection parameters for the PostgreSQL database.

    Returns:
        str: The detailed database schema.
    """
    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()

        # Get list of tables
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = cursor.fetchall()

        if not tables:
            return "No tables found in public schema"

        schema = []

        for table in tables:
            table_name = table[0]
            schema.append(f"CREATE TABLE {table_name} (")

            # Get columns with metadata
            cursor.execute("""
                SELECT 
                    column_name, 
                    data_type, 
                    character_maximum_length, 
                    is_nullable, 
                    column_default,
                    CASE 
                        WHEN p.contype = 'p' THEN true
                        ELSE false
                    END AS is_primary_key
                FROM 
                    information_schema.columns c
                LEFT JOIN (
                    SELECT conname, conrelid, conkey, contype
                    FROM pg_constraint
                ) p
                ON c.ordinal_position = ANY(p.conkey)
                WHERE 
                    c.table_schema = 'public'
                    AND c.table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            column_lines = []
            
            for col in columns:
                col_name, data_type, char_max_len, is_nullable, default, is_pk = col
                type_str = f"{data_type}({char_max_len})" if char_max_len else data_type
                nullable_str = "NULL" if is_nullable == "YES" else "NOT NULL"
                default_str = f"DEFAULT {default}" if default else ""
                pk_str = "PRIMARY KEY" if is_pk else ""
                
                column_def = f"    {col_name} {type_str} {nullable_str} {default_str} {pk_str}".strip()
                column_lines.append(column_def)

            # Get foreign keys
            cursor.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = %s;
            """, (table_name,))
            
            foreign_keys = cursor.fetchall()
            for fk_col, ref_table, ref_col in foreign_keys:
                column_lines.append(f"    FOREIGN KEY ({fk_col}) REFERENCES {ref_table}({ref_col})")

            schema.append(",\n".join(column_lines))
            schema.append(");\n")

        return "\n".join(schema)

    except psycopg2.Error as db_error:
        print(f"Database error: {str(db_error)}")
        return "-- Failed to retrieve schema: Database error"
    except Exception as error:
        print(f"Error retrieving schema: {str(error)}")
        return "-- Failed to retrieve schema: Unexpected error"
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Example Usage
if __name__ == "__main__":
    user_query = input("Enter your query: ")
    schema = get_schema(connection_params_example)
    sql = generate_sql_from_text(user_query, schema)
    print("SQL:", sql)
