import psycopg2
import openai  # Example: Using OpenAI's GPT API (ensure to install the library)
from typing import Any, Dict
import json
import os
from dotenv import load_dotenv
from generator.sql import SQLGenerator

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
            # schema += f"\n-- Table: {table_name}\n"
            schema += f"CREATE TABLE {table_name} (\n"

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
connection_params_example = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432))
}  # creds should be view only.

# Initialize SQL Generator
generator = SQLGenerator()

# Get schema and add it to the generator
# schema = get_schema(connection_params_example)
# print("Database Schema:", schema)
# generator.add_schema_context(schema)



# Store the documentation in a variable
schema_documentation = """
DATABASE DOCUMENTATION

Table: users
Description: Stores information about users of the system.

Columns:
- id (character varying, PRIMARY KEY): Unique user identifier
- name (character varying): User's full name
- email (character varying): User's email address
- hashed_password (character varying): Hashed password for security
- is_active (boolean): Whether the user is active
- created_at (timestamp): User creation timestamp

Table: documents
Description: Stores documents that are managed in the system.

Columns:
- id (character varying, PRIMARY KEY): Unique document identifier
- title (character varying): Title of the document
- status (character varying): Status (e.g., Draft, Signed)
- file_path (character varying): Path to the uploaded file
- pdf_url (character varying): Public URL for the PDF
- created_at (timestamp): When the document was created
- created_by (character varying, FOREIGN KEY to users): Refers to user who created the document

Table: envelopes
Description: Represents a set of documents sent to one or more signers.

Columns:
- id (character varying, PRIMARY KEY): Unique envelope identifier
- document_id (character varying, FOREIGN KEY to documents): Associated document
- status (character varying): Status (e.g., Sent, Completed, Declined)
- created_at (timestamp): Envelope creation time
- created_by (character varying, FOREIGN KEY to users): Creator of the envelope
- completed_at (timestamp): When signing was completed
- declined_at (timestamp): When envelope was declined
- cancelled_at (timestamp): When envelope was canceled
- message (text): Custom message sent with the envelope
- file_path (character varying(255)): Local path of final envelope file
- pdf_url (character varying(255)): Public PDF URL

Table: signers
Description: Tracks the signers associated with an envelope.

Columns:
- id (character varying, PRIMARY KEY): Unique signer identifier
- name (character varying): Signer name
- email (character varying): Signer email
- status (character varying): Signing status
- order (integer): Signing order
- envelope_id (character varying, FOREIGN KEY to envelopes): Associated envelope
- signed_at (timestamp): When the signer signed
- declined_at (timestamp): When signing was declined
- viewed_at (timestamp): When document was first viewed
- sign_path (character varying(255)): Path to the sign image or record

Table: audit_events
Description: Tracks actions taken by users on documents or envelopes.

Columns:
- id (character varying, PRIMARY KEY): Unique event ID
- type (character varying): Event type (e.g., viewed, signed)
- timestamp (timestamp): When event occurred
- actor_id (character varying): User who performed the action
- document_id (character varying, FOREIGN KEY to documents): Optional related document
- envelope_id (character varying, FOREIGN KEY to envelopes): Optional related envelope
- details (json): Extra metadata about the action

Table: signature_fields
Description: Defines where signatures must appear in a document.

Columns:
- id (character varying, PRIMARY KEY): Field ID
- type (character varying): Field type (e.g., signature, date)
- page (integer): Page number
- x, y (double precision): Coordinates on the page
- width, height (double precision): Size of the field
- envelope_id (character varying, FOREIGN KEY to envelopes): Linked envelope
- signer_id (character varying, FOREIGN KEY to signers): Assigned signer

Table: otps
Description: One-Time Passwords used for email verification or login.

Columns:
- email (character varying(255), PRIMARY KEY): Email address
- otp (character varying(6)): OTP code
- expires_at (timestamp with time zone): When the OTP expires
- created_at (timestamp with time zone): When the OTP was generated
"""

# Add the documentation to the generator
# generator.add_documentation(schema_documentation)
# Add example queries for training (add examples relevant to your database)
example_queries = [
    {
        "question": "Get all active users",
        "sql": "SELECT id, name, email FROM users WHERE is_active = TRUE"
    },
    {
        "question": "List documents created by a specific user",
        "sql": "SELECT id, title, status, created_at FROM documents WHERE created_by = 'user-id-here'"
    },
    {
        "question": "Get all envelopes related to a document",
        "sql": "SELECT * FROM envelopes WHERE document_id = 'document-id-here'"
    },
    {
        "question": "Get signers and their status for a specific envelope",
        "sql": "SELECT name, email, status, signed_at FROM signers WHERE envelope_id = 'envelope-id-here'"
    },
    {
        "question": "Track audit events for a document",
        "sql": "SELECT type, timestamp, actor_id, details FROM audit_events WHERE document_id = 'document-id-here' ORDER BY timestamp DESC"
    },
    {
        "question": "Get signature fields for a signer in an envelope",
        "sql": "SELECT page, x, y, width, height, type FROM signature_fields WHERE envelope_id = 'envelope-id-here' AND signer_id = 'signer-id-here'"
    },
    {
        "question": "Check the latest OTP for a user",
        "sql": "SELECT otp, created_at, expires_at FROM otps WHERE email = 'user@example.com' ORDER BY created_at DESC LIMIT 1"
    }
]
# generator.train_from_examples(example_queries)

queries =[
  {
    "question": "Get all documents with the status 'Signed'",
    "sql": "SELECT id, title, created_at FROM documents WHERE status = 'Signed';"
  },
  {
    "question": "Find envelopes that were completed in the last 7 days",
    "sql": "SELECT id, document_id, completed_at FROM envelopes WHERE completed_at >= NOW() - INTERVAL '7 days';"
  },
  {
    "question": "List all signers who have not yet signed a document",
    "sql": "SELECT name, email, status FROM signers WHERE status IS NULL OR status != 'signed';"
  },
  {
    "question": "Count the number of documents created by each user",
    "sql": "SELECT created_by, COUNT(*) AS document_count FROM documents GROUP BY created_by;"
  },
  {
    "question": "Get the list of users who created envelopes but are currently inactive",
    "sql": "SELECT u.id, u.name, u.email FROM users u JOIN envelopes e ON u.id = e.created_by WHERE u.is_active = FALSE;"
  },
  {
    "question": "Find the most recent audit event for a given envelope",
    "sql": "SELECT * FROM audit_events WHERE envelope_id = 'your-envelope-id' ORDER BY timestamp DESC LIMIT 1;"
  },
  {
    "question": "Get all envelopes that were declined",
    "sql": "SELECT id, document_id, declined_at FROM envelopes WHERE declined_at IS NOT NULL;"
  },
  {
    "question": "Retrieve OTPs that are still valid (not expired)",
    "sql": "SELECT email, otp, expires_at FROM otps WHERE expires_at > NOW();"
  },
  {
    "question": "List all signers who viewed but did not sign the envelope",
    "sql": "SELECT name, email FROM signers WHERE viewed_at IS NOT NULL AND signed_at IS NULL;"
  },
  {
    "question": "Find all documents that have never been included in an envelope",
    "sql": "SELECT d.id, d.title FROM documents d LEFT JOIN envelopes e ON d.id = e.document_id WHERE e.id IS NULL;"
  },
  {
    "question": "Get the number of signature fields per envelope",
    "sql": "SELECT envelope_id, COUNT(*) AS total_signature_fields FROM signature_fields GROUP BY envelope_id;"
  },
  {
    "question": "Retrieve all audit events of type 'signed' for a document",
    "sql": "SELECT * FROM audit_events WHERE type = 'signed' AND document_id = 'your-document-id';"
  },
  {
    "question": "List the top 5 users who created the most envelopes",
    "sql": "SELECT created_by, COUNT(*) AS envelope_count FROM envelopes GROUP BY created_by ORDER BY envelope_count DESC LIMIT 5;"
  },
  {
    "question": "Get signers who declined to sign a document",
    "sql": "SELECT s.name, s.email, s.declined_at FROM signers s JOIN envelopes e ON s.envelope_id = e.id WHERE e.document_id = 'your-document-id' AND s.declined_at IS NOT NULL;"
  },
  {
    "question": "Fetch all signature fields on page 1 of a specific envelope",
    "sql": "SELECT * FROM signature_fields WHERE envelope_id = 'your-envelope-id' AND page = 1;"
  }
]


def test_sql_generation():
    """
    Test the SQL generation process using actual database connection and queries.
    """
    results = []
    for query in queries:
        question = query["question"]
        actual_sql = query["sql"]
        generated_sql = generator.generate_sql(question)
        
        print(f"Question: {question}")
        print(f"Actual SQL: {actual_sql}")
        print(f"Generated SQL: {generated_sql}")

        # Store the results
        results.append({
            "question": question,
            "actual_sql": actual_sql,
            "generated_sql": generated_sql
        })
        print("-" * 50)
    
    # Write all results as a single JSON array
    with open("sql_generation_results.json", "w") as json_file:
        json.dump(results, json_file, indent=4)

# test_sql_generation()


def execute_sql_queries():
    """
    Execute the generated SQL queries on the actual database and print the results.
    """
    try:
        # Import JSON file sql_generation_results as a single JSON array
        with open("sql_generation_results.json", "r") as json_file:
            data = json.load(json_file)  # Changed from json.loads(line) to json.load()

        if not data:
            print("No queries found in sql_generation_results.json")
            return
        results = []
        for query in data:
            try:
                question = query["question"]
                actual_sql = query["actual_sql"]
                generated_sql = query["generated_sql"]
                
                print(f"\nQuestion: {question}")
                print(f"Actual SQL: {actual_sql}")
                print(f"Generated SQL: {generated_sql}")

                actual_sql_result = run_query(connection_params_example, actual_sql)
                print(f"Actual Query Result: {actual_sql_result}")
                
                # Execute the generated SQL query
                result = run_query(connection_params_example, generated_sql)
                
                print(f"generated Query Result: {result}")
                results.append({
                    "question": question,
                    "actual_sql": actual_sql,
                    "generated_sql": generated_sql,
                    "actual_result": actual_sql_result,
                    "generated_result": result
                })
                print("-" * 50)
            except KeyError as ke:
                print(f"Missing key in query data: {ke}")
            except Exception as e:
                print(f"Error processing query: {e}")
                continue
        # Write all results as a single JSON array
        with open("sql_query_data.json", "w") as json_file:
            json.dump(results, json_file, indent=4)       
    except FileNotFoundError:
        print("sql_generation_results.json file not found")
    except json.JSONDecodeError:
        print("Error parsing JSON data from sql_generation_results.json")
    except Exception as e:
        print(f"Unexpected error: {e}")

execute_sql_queries()