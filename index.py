import psycopg2
import openai  # Example: Using OpenAI's GPT API (ensure to install the library)
from typing import Any, Dict
import os
from dotenv import load_dotenv

def generate_prompt(schema: str, user_request: str) -> str:
    """
    Generate a prompt for the language model based on the schema and user request.

    Args:
        schema (str): The database schema.
        user_request (str): The user's request in plain English.

    Returns:
        str: The generated prompt.
    """
    return f"""
You are an expert SQL generator. Given the schema of a database and a user's request in plain English, generate a syntactically correct and optimized SQL query.

Schema:
{schema} 

User Request:
"{user_request}"

Output:
Return only the SQL query without explanation or extra text.
"""
# generate postgres prompt
def generate_postgres_prompt(schema: str, user_request: str) -> str:
    """
    Generate a prompt for the language model based on the schema and user request for PostgreSQL.

    Args:
        schema (str): The database schema.
        user_request (str): The user's request in plain English.

    Returns:
        str: The generated prompt.
    """
#     return f"""
# You are an expert PostgreSQL SQL query generator. Given the schema of a PostgreSQL database and a user’s request in plain English, generate a syntactically correct and optimized SQL query. Ensure compatibility with PostgreSQL features, data types, and best practices.

# Schema:
# {schema}

# User Request:
# "{user_request}"

# Output:
# Return only the SQL query. Do not include any explanations, comments, or additional text.
# """
    return f"""
You are an expert PostgreSQL SQL query generator. Given the schema of a PostgreSQL database and a user’s request in plain English, generate a syntactically correct and optimized SQL query. Ensure compatibility with PostgreSQL features, data types, and best practices.

If the request cannot be translated into a valid SQL query based on the given schema, or if necessary information is missing, clearly deny the request and do not attempt to generate a query.

Schema:
{schema}

User Request:
"{user_request}"

Output:
If the query is possible, return only the SQL query. If not, respond with: "Unable to generate a valid SQL query with the given schema and request."
"""
# TODO : add not to ever genearate any data modification query, update, delete, insert



def generate_sql(prompt: str) -> str:
    """
    Generate an SQL query based on the schema and user request using prompt.

    Args:
        prompt (str): llm prompt.

    Returns:
        str: The generated SQL query.
    """
    try:
        # Example: Using OpenAI's GPT model to generate the SQL query
        response = openai.Completion.create(
            engine="text-davinci-003",  # Replace with the appropriate engine
            prompt=prompt,
            max_tokens=150,  # Adjust based on expected query length
            temperature=0  # Lower temperature for deterministic output
        )
        # Extract the generated SQL query from the response
        sql_query = response.choices[0].text.strip()
        return sql_query
    except Exception as e:
        print(f"Error generating SQL query: {e}")
        return "-- Failed to generate SQL query"
#  for postgres
# def get_schema(connection_params: Dict[str, Any]) -> str:
#     """
#     Retrieve the database schema from a PostgreSQL database.

#     Args:
#         connection_params (Dict[str, Any]): The connection parameters for the PostgreSQL database.

#     Returns:
#         str: The database schema.
#     """
#     try:
#         # Connect to the PostgreSQL database
#         connection = psycopg2.connect(**connection_params)
#         cursor = connection.cursor()

#         # Execute a query to get the schema (customize this based on your needs)
#         cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
#         tables = cursor.fetchall()

#         schema = ""
#         for table in tables:
#             table_name = table[0]
#             schema += f". {table_name} ("
#             cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table_name}';")
#             columns = cursor.fetchall()
#             column_definitions = ", ".join([f"{column[0]} {column[1]}" for column in columns])
#             schema += f"{column_definitions})\n"

#         # Close the connection
#         cursor.close()
#         connection.close()

#         return schema
#     except Exception as e:
#         print(f"Error retrieving schema: {e}")
#         return "-- Failed to retrieve schema"

def get_schema(connection_params: Dict[str, Any]) -> str:
    """
    Retrieve a detailed database schema from a PostgreSQL database.

    Args:
        connection_params (Dict[str, Any]): The connection parameters for the PostgreSQL database.

    Returns:
        str: The detailed database schema.
    """
    try:
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()

        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = cursor.fetchall()

        schema = ""

        for table in tables:
            table_name = table[0]
            schema += f"\n-- Table: {table_name}\n"
            schema += f"{table_name} (\n"

            # Get columns with data types, nullability, default values, and max length
            cursor.execute(f"""
                SELECT 
                    column_name, 
                    data_type, 
                    character_maximum_length, 
                    is_nullable, 
                    column_default
                FROM 
                    information_schema.columns
                WHERE 
                    table_schema = 'public'
                    AND table_name = %s;
            """, (table_name,))
            columns = cursor.fetchall()

            column_lines = []
            for col in columns:
                col_name, data_type, char_max_len, is_nullable, default = col
                type_str = f"{data_type}({char_max_len})" if char_max_len else data_type
                nullable_str = "NULL" if is_nullable == "YES" else "NOT NULL"
                default_str = f"DEFAULT {default}" if default else ""
                column_lines.append(f"    {col_name} {type_str} {nullable_str} {default_str}".strip())

            # Get primary keys
            cursor.execute(f"""
                SELECT 
                    kcu.column_name
                FROM 
                    information_schema.table_constraints tc
                JOIN 
                    information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE 
                    tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = 'public'
                    AND tc.table_name = %s;
            """, (table_name,))
            pk_columns = [row[0] for row in cursor.fetchall()]
            if pk_columns:
                column_lines.append(f"    PRIMARY KEY ({', '.join(pk_columns)})")

            # Get unique constraints
            cursor.execute(f"""
                SELECT 
                    kcu.column_name
                FROM 
                    information_schema.table_constraints tc
                JOIN 
                    information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE 
                    tc.constraint_type = 'UNIQUE'
                    AND tc.table_schema = 'public'
                    AND tc.table_name = %s;
            """, (table_name,))
            unique_columns = [row[0] for row in cursor.fetchall()]
            for uc in unique_columns:
                column_lines.append(f"    UNIQUE ({uc})")

            # Get foreign keys
            cursor.execute(f"""
                SELECT 
                    kcu.column_name AS fk_column,
                    ccu.table_name AS referenced_table,
                    ccu.column_name AS referenced_column
                FROM 
                    information_schema.table_constraints tc
                JOIN 
                    information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN 
                    information_schema.constraint_column_usage ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE 
                    tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                    AND tc.table_name = %s;
            """, (table_name,))
            foreign_keys = cursor.fetchall()
            for fk_col, ref_table, ref_col in foreign_keys:
                column_lines.append(f"    FOREIGN KEY ({fk_col}) REFERENCES {ref_table}({ref_col})")

            schema += ",\n".join(column_lines)
            schema += "\n);\n"

        cursor.close()
        connection.close()

        return schema

    except Exception as e:
        print(f"Error retrieving schema: {e}")
        return "-- Failed to retrieve schema"

def run_query(connection_params: Dict[str, Any], query: str) -> Any:
    """
    Execute an SQL query on a PostgreSQL database and return the results.

    Args:
        connection_params (Dict[str, Any]): The connection parameters for the PostgreSQL database.
        query (str): The SQL query to execute.

    Returns:
        Any: The query result.
    """
    try:
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()

        # Execute the query
        cursor.execute(query)

        # Fetch all results (customize this based on your query needs)
        result = cursor.fetchall()

        # Close the connection
        cursor.close()
        connection.close()

        return result
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

# Load environment variables from .env file
load_dotenv()

# Example usage (ensure to replace with actual schema, request, and connection params):
schema_example = """
table_name (
    id SERIAL PRIMARY KEY,
    name TEXT,
    age INT,
    condition TEXT
)
"""
user_request_example = "Show names of the books whose author is utk."
connection_params_example = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432))
}  # creds should be view only.
# get schema
schema = get_schema(connection_params_example)
print("Database Schema:", schema)
# Generate prompt
# prompt = generate_prompt(schema, user_request_example)
# print("Generated Prompt:", prompt)
# Generate PostgreSQL prompt
prompt = generate_postgres_prompt(schema, user_request_example)
print("Generated Prompt:", prompt)
#  verify prompt manually along with llm that it is not generating any data modification query.

# Generate SQL query
# query = generate_sql(schema_example, user_request_example)
# print("Generated SQL Query:", query)

# # Run SQL query
# results = run_query(connection_params_example, query)
# print("Query Results:", results)
