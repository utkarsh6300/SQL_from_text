import psycopg2
import openai
from typing import Any, Dict
import os
from dotenv import load_dotenv
load_dotenv()

def get_snowflake_connection() -> Any:
    """
    Establishes a connection to the Snowflake database.
    """
    try:
        conn = psycopg2.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            host=os.getenv("SNOWFLAKE_HOST"),
            port=os.getenv("SNOWFLAKE_PORT"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA")
        )
        return conn
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        return None
def execute_query(query: str) -> Dict[str, Any]:
    """
    Executes a SQL query on the Snowflake database and returns the result.
    """
    conn = get_snowflake_connection()
    if conn is None:
        return {"error": "Failed to connect to Snowflake"}

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in result]
            return {"data": data}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
def generate_sql_query(prompt: str) -> str:
    """
    Generates a SQL query using OpenAI's GPT-3.5 model based on the provided prompt.
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.5,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error generating SQL query: {e}")
        return ""
def generate_prompt() -> str:
    """
    Generates a prompt for the SQL query generation.
    """
    return "Generate a SQL query to select all columns from the 'employees' table."
def main():
    """
    Main function to execute the SQL query generation and execution.
    """
    prompt = "Generate a SQL query to select all columns from the 'employees' table."
    sql_query = generate_sql_query(prompt)
    print(f"Generated SQL Query: {sql_query}")

    result = execute_query(sql_query)
    if "error" in result:
        print(f"Error executing query: {result['error']}")
    else:
        print("Query Result:")
        for row in result["data"]:
            print(row)
if __name__ == "__main__":
    main()
# This script connects to a Snowflake database, generates a SQL query using OpenAI's GPT-3.5 model, and executes the query.
