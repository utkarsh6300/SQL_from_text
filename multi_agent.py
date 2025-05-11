import csv
import io
from typing import Optional, Dict, Any, Tuple
import psycopg2
from dotenv import load_dotenv
import os
from generator.sql import SQLGenerator
from openai import OpenAI

class MultiAgent:
    def __init__(self, vector_store_path: str = "./chroma_db_new"):
        """
        Initialize the MultiAgent with SQL Generator and database connection.
        
        Args:
            vector_store_path (str): Path to the ChromaDB vector store
        """
        load_dotenv()
        
        # Initialize SQL Generator
        self.sql_generator = SQLGenerator(vector_store_path)
        
        # Database connection parameters
        self.connection_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT", 5432))
        }

    def detect_output_format(self, question: str) -> str:
        """
        Detect desired output format from the question using AI.
        
        Args:
            question (str): The user's question
            
        Returns:
            str: Detected format ('csv', 'excel', 'doc', 'default')
        """
        try:
            # Generate format detection prompt
            format_prompt = f"""
Given this question: "{question}"

Determine if the user wants a specific output format.
Consider these formats:
- 'csv' for CSV file output
- 'excel' for Excel spreadsheet output
- 'doc' for document/report output
- 'default' for standard output

Return only one word: csv, excel, doc, or default.
"""
            # Use OpenAI to detect format
            response = self.sql_generator.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a format detection expert. Respond with exactly one word."},
                    {"role": "user", "content": format_prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            detected_format = response.choices[0].message.content.strip().lower()
            return detected_format if detected_format in ['csv', 'excel', 'doc'] else 'default'
            
        except Exception as e:
            print(f"Error detecting format: {e}")
            return 'default'

    def wants_csv_output(self, question: str) -> bool:
        """
        Determine if the user wants CSV output based on their question.
        
        Args:
            question (str): The user's question
            
        Returns:
            bool: True if CSV output is requested, False otherwise
        """
        csv_keywords = ['csv', 'export', 'download', 'file', 'spreadsheet', 'excel']
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in csv_keywords)

    def train_from_examples(self, examples):
        """Train the SQL generator with example queries"""
        self.sql_generator.train_from_examples(examples)

    def add_schema_context(self, schema: str):
        """Add database schema context"""
        self.sql_generator.add_schema_context(schema)

    def add_documentation(self, documentation: str):
        """Add additional documentation context"""
        self.sql_generator.add_documentation(documentation)

    def execute_query(self, query: str) -> Tuple[Optional[list], Optional[list]]:
        """
        Execute an SQL query and return results with column names.
        
        Args:
            query (str): SQL query to execute
            
        Returns:
            Tuple[Optional[list], Optional[list]]: Tuple of (column names, results)
        """
        connection = None
        cursor = None
        try:
            connection = psycopg2.connect(**self.connection_params)
            cursor = connection.cursor()
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            
            return columns, results
            
        except Exception as e:
            print(f"Error executing query: {e}")
            return None, None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def generate_csv(self, data: list, columns: list) -> str:
        """
        Convert query results to CSV format.
        
        Args:
            data (list): Query results
            columns (list): Column names
            
        Returns:
            str: CSV formatted string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(columns)
        
        # Write data rows
        writer.writerows(data)
        
        return output.getvalue()

    def format_as_excel(self, data: list, columns: list) -> bytes:
        """
        Convert query results to Excel format.
        
        Args:
            data (list): Query results
            columns (list): Column names
            
        Returns:
            bytes: Excel file content
        """
        import pandas as pd
        import io
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=columns)
        
        # Convert to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Query Results', index=False)
        
        return output.getvalue()

    def format_as_document(self, data: list, columns: list, question: str) -> str:
        """
        Convert query results to a formatted document.
        
        Args:
            data (list): Query results
            columns (list): Column names
            question (str): Original question
            
        Returns:
            str: Formatted document content
        """
        from datetime import datetime
        
        # Create document content
        doc = []
        doc.append("Query Results Report")
        doc.append("=" * 50)
        doc.append(f"Question: {question}")
        doc.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.append("-" * 50)
        doc.append("\nResults:")
        
        # Format as table
        # Header
        doc.append(" | ".join(columns))
        doc.append("-" * (sum(len(col) for col in columns) + 3 * (len(columns) - 1)))
        
        # Data rows
        for row in data:
            doc.append(" | ".join(str(val) for val in row))
        
        return "\n".join(doc)

    def process_question(self, question: str) -> dict:
        """
        Process a natural language question to generate and execute SQL query.
        
        Args:
            question (str): Natural language question
            
        Returns:
            dict: Dictionary containing SQL query and results in requested format
        """
        # Generate SQL query
        sql_query = self.sql_generator.generate_sql(question)
        if not sql_query or sql_query.startswith("Error"):
            return {"sql": sql_query, "error": "Failed to generate SQL query"}
            
        # Execute query and get results
        columns, results = self.execute_query(sql_query)
        if not results or not columns:
            return {"sql": sql_query, "error": "No results found"}
            
        # Detect desired output format
        output_format = self.detect_output_format(question)

        print(f"Detected format: {output_format}")
        
        # Prepare response
        response = {
            "sql": sql_query,
            "columns": columns,
            "results": results,
            "format": output_format
        }
        
        # Add formatted output based on detected format
        if output_format == 'csv':
            response["formatted_output"] = self.generate_csv(results, columns)
        elif output_format == 'excel':
            response["formatted_output"] = self.format_as_excel(results, columns)
        elif output_format == 'doc':
            response["formatted_output"] = self.format_as_document(results, columns, question)
            
        return response

def main():
    agent = MultiAgent()
    
    # Add schema and training data as needed
    # schema = """
    # CREATE TABLE users (
    #     id VARCHAR PRIMARY KEY,
    #     name VARCHAR NOT NULL,
    #     email VARCHAR UNIQUE NOT NULL,
    #     is_active BOOLEAN DEFAULT true
    # );
    # """
    # agent.add_schema_context(schema)
    
    # # Example queries for training
    # examples = [
    #     {
    #         "question": "List all active users",
    #         "sql": "SELECT id, name, email FROM users WHERE is_active = true"
    #     }
    # ]
    # agent.train_from_examples(examples)
    
    # Get question from user
    question = input("Enter your question: ")
    
    # Process the question and get results
    response = agent.process_question(question)
    
    # Display SQL query
    print(f"\nGenerated SQL: {response['sql']}")
    
    if "error" in response:
        print(f"Error: {response['error']}")
    else:
        # Display results based on format
        if response["format"] == 'csv':
            print("\nResults (CSV format):")
            print(response["formatted_output"])
            # Save CSV file
            with open("query_results.csv", "w") as f:
                f.write(response["formatted_output"])
            print("Saved as: query_results.csv")
        elif response["format"] == 'excel':
            print("\nResults generated in Excel format")
            # Save Excel file
            with open("query_results.xlsx", "wb") as f:
                f.write(response["formatted_output"])
            print("Saved as: query_results.xlsx")
        elif response["format"] == 'doc':
            print("\nFormatted Report:")
            print(response["formatted_output"])
            # Save document file
            with open("query_results.txt", "w") as f:
                f.write(response["formatted_output"])
            print("Saved as: query_results.txt")
        else:
            print("\nResults (Default format):")
            print(",".join(response["columns"]))
            for row in response["results"]:
                print(",".join(str(val) for val in row))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def reiterate(question: str, sql_queries: [str]) -> str:
    """
    Function to reiterate the query generated for the user and ask user if it is correct and take that if they to again generate.
    
    Args:
        question (str): Original natural language question
        sql_queries (list[str]): List of previously attempted SQL queries that were incorrect
        
    Returns:
        str: New generated SQL query
    """
    # Create a prompt that includes the failed attempts
    prompt = f"""
Given this question: "{question}"

The following SQL queries were previously generated but were incorrect:
{chr(10).join([f"- {query}" for query in sql_queries])}

Please analyze why these queries might have been incorrect and generate a new, more accurate SQL query.
Consider:
1. Table relationships
2. Column names
3. Query logic
4. Filter conditions

Generate only the SQL query without any explanation.
"""
    
    try:
        # Generate new SQL query using the SQL generator with the refined prompt
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert SQL query generator. Provide only the SQL query without explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=200
        )
        
        new_query = response.choices[0].message.content.strip()
        return new_query
        
    except Exception as e:
        print(f"Error regenerating query: {e}")
        return f"Error: Failed to regenerate query - {str(e)}"


if __name__ == "__main__":
    main()