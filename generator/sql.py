import os
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
from vectorStore.chroma import ChromaDB_VectorStore
from chromadb.utils import embedding_functions

class SQLGenerator:
    def __init__(self, vector_store_path: str = "./chroma_db_new"):
        """
        Initialize the SQL Generator with vector store and OpenAI integration.
        
        Args:
            vector_store_path (str): Path to the ChromaDB vector store
        """
        load_dotenv()
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize OpenAI embedding function
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-ada-002"
        )
        
        # Initialize vector store
        self.vector_store = ChromaDB_VectorStore(config={
            "path": vector_store_path,
            "client": "persistent",
            "n_results": 5,
            "embedding_function": self.openai_ef
        })
    
    def train_from_examples(self, examples: List[dict]) -> None:
        """
        Train the vector store with SQL query examples.
        
        Args:
            examples (List[dict]): List of dictionaries containing 'question' and 'sql' keys
        """
        for example in examples:
            self.vector_store.add_question_sql(
                question=example["question"],
                sql=example["sql"]
            )
    
    def add_schema_context(self, schema: str) -> None:
        """
        Add database schema to the vector store for context.
        
        Args:
            schema (str): Database schema DDL
        """
        self.vector_store.add_ddl(schema)
    
    def add_documentation(self, documentation: str) -> None:
        """
        Add documentation to provide additional context for SQL generation.
        
        Args:
            documentation (str): Documentation string
        """
        self.vector_store.add_documentation(documentation)
    
    def generate_sql(self, question: str) -> str:
        """
        Generate SQL query based on the question using vector store context and OpenAI.
        
        Args:
            question (str): Natural language question to generate SQL for
            
        Returns:
            str: Generated SQL query
        """
        # Get similar questions and their SQL queries
        similar_queries = self.vector_store.get_similar_question_sql(question)
        
        # Get related schema information
        schema_context = self.vector_store.get_related_ddl(question)
        
        # Get related documentation
        docs_context = self.vector_store.get_related_documentation(question)
        
        # Prepare context for OpenAI
        context = self._prepare_context(similar_queries, schema_context, docs_context)
        
        # Generate SQL using OpenAI
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert SQL query generator. Generate only the SQL query without any explanation."},
                    {"role": "user", "content": f"""
Given the following context:
{context}

Generate a SQL query for this question: {question}

Return only the SQL query without any explanation."""}
                ],
                temperature=0.1,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating SQL: {str(e)}"
    
    def _prepare_context(self, similar_queries: Optional[List[dict]], 
                        schema_context: Optional[List[str]], 
                        docs_context: Optional[List[str]]) -> str:
        """
        Prepare context string from vector store results.
        
        Args:
            similar_queries (Optional[List[dict]]): Similar SQL queries from vector store
            schema_context (Optional[List[str]]): Related schema information
            docs_context (Optional[List[str]]): Related documentation
            
        Returns:
            str: Formatted context string
        """
        context = []
        
        if similar_queries:
            context.append("Similar queries:")
            for query in similar_queries:
                if isinstance(query, dict) and 'question' in query and 'sql' in query:
                    context.append(f"Question: {query['question']}")
                    context.append(f"SQL: {query['sql']}\n")
        
        if schema_context:
            context.append("Database schema:")
            context.extend(schema_context)
        
        if docs_context:
            context.append("\nAdditional context:")
            context.extend(docs_context)
        
        return "\n".join(context)