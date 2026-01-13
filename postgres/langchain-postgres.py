import os
import sys
import uuid
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text
from langchain_postgres import PGVectorStore, PGEngine
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

# Add parent directory to path to import from POC/helper.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from POC.helper import get_chunk_embedding

# Search for .env file
load_dotenv()

POSTGRES_USER = os.environ.get("DB_USER")
POSTGRES_PASSWORD = os.environ.get("DB_PASSWORD")
POSTGRES_HOST = os.environ.get("DB_HOST", "localhost")
POSTGRES_PORT = os.environ.get("DB_PORT", "5432")
POSTGRES_DB = os.environ.get("DB_NAME")

TABLE_NAME = "hc_ai_table"
# mxbai-embed-large:latest produces 1024-dimensional embeddings
VECTOR_SIZE = 1024
SCHEMA_NAME = "hc_ai_schema"

# Global variables for connection pooling
_engine: Optional[AsyncEngine] = None
_pg_engine: Optional[PGEngine] = None
_vector_store: Optional[PGVectorStore] = None


class CustomEmbeddings(Embeddings):
    """
    Custom LangChain embeddings wrapper that uses get_chunk_embedding from POC/main.py.
    This ensures we use the same embedding provider and configuration as process_and_store.
    """
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        embeddings = []
        for text in texts:
            embedding = get_chunk_embedding(text)
            if embedding is None:
                raise ValueError(f"Failed to generate embedding for text: {text[:50]}...")
            embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        embedding = get_chunk_embedding(text)
        if embedding is None:
            raise ValueError(f"Failed to generate embedding for query: {text[:50]}...")
        return embedding


async def verify_table_exists(engine: AsyncEngine, schema_name: str, table_name: str) -> bool:
    """Check if table exists in the database"""
    async with engine.begin() as conn:
        res = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE  table_schema = :schema_name
                    AND    table_name   = :table_name
                )
            """),
            {"schema_name": schema_name, "table_name": table_name}
        )
        return res.scalar_one()


async def get_table_info(engine: AsyncEngine, schema_name: str, table_name: str):
    """Get table structure information"""
    async with engine.begin() as conn:
        res = await conn.execute(
            text("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = :schema_name
                AND table_name = :table_name
                ORDER BY ordinal_position
            """),
            {"schema_name": schema_name, "table_name": table_name}
        )
        return res.fetchall()


async def initialize_vector_store() -> PGVectorStore:
    """
    Initialize and return the PostgreSQL vector store.
    Creates schema and table if they don't exist.
    Uses connection pooling for efficiency.
    """
    global _engine, _pg_engine, _vector_store
    
    # Reuse existing connection if available
    if _vector_store is not None:
        return _vector_store
    
    # Validate required environment variables
    required_vars = {
        "DB_USER": POSTGRES_USER,
        "DB_PASSWORD": POSTGRES_PASSWORD,
        "DB_NAME": POSTGRES_DB,
    }
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Create engine if not exists
    if _engine is None:
        connection_string = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        _engine = create_async_engine(connection_string)
        _pg_engine = PGEngine.from_engine(engine=_engine)
    
    # Create schema if it doesn't exist
    async with _engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_NAME}"'))
    
    # Create table if it doesn't exist
    already_exists = await verify_table_exists(_engine, SCHEMA_NAME, TABLE_NAME)
    if not already_exists:
        await _pg_engine.ainit_vectorstore_table(
            table_name=TABLE_NAME,
            vector_size=VECTOR_SIZE,
            schema_name=SCHEMA_NAME,
        )
    
    # Verify table exists
    table_exists = await verify_table_exists(_engine, SCHEMA_NAME, TABLE_NAME)
    if not table_exists:
        raise Exception("Table was not created successfully!")
    
    # Create embeddings instance
    embedding = CustomEmbeddings()
    
    # Create vector store
    _vector_store = await PGVectorStore.create(
        engine=_pg_engine,
        table_name=TABLE_NAME,
        schema_name=SCHEMA_NAME,
        embedding_service=embedding,
    )
    
    return _vector_store


async def store_chunk(
    chunk_text: str,
    chunk_id: str,
    metadata: Dict[str, Any]
) -> bool:
    """
    Store a single chunk in the PostgreSQL vector store.
    
    Args:
        chunk_text: The text content of the chunk
        chunk_id: Unique identifier for the chunk
        metadata: Dictionary of metadata to store with the chunk
    
    Returns:
        True if successful, False otherwise
    """
    try:
        vector_store = await initialize_vector_store()
        
        # Create a Document with the chunk
        doc = Document(
            id=chunk_id,
            page_content=chunk_text,
            metadata=metadata
        )
        
        # Add document to vector store
        await vector_store.aadd_documents([doc])
        
        return True
    except Exception as e:
        print(f"Error storing chunk {chunk_id}: {e}")
        return False


async def store_chunks_batch(
    chunks: List[Dict[str, Any]]
) -> int:
    """
    Store multiple chunks in a batch operation.
    
    Args:
        chunks: List of dictionaries, each containing:
            - 'text': chunk text content
            - 'id': chunk ID
            - 'metadata': metadata dictionary
    
    Returns:
        Number of successfully stored chunks
    """
    try:
        vector_store = await initialize_vector_store()
        
        documents = []
        for chunk in chunks:
            doc = Document(
                id=chunk['id'],
                page_content=chunk['text'],
                metadata=chunk.get('metadata', {})
            )
            documents.append(doc)
        
        if documents:
            await vector_store.aadd_documents(documents)
        
        return len(documents)
    except Exception as e:
        print(f"Error storing chunks batch: {e}")
        return 0


async def search_similar_chunks(
    query: str,
    k: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    Search for similar chunks using semantic similarity.
    
    Args:
        query: Search query text
        k: Number of results to return
        filter_metadata: Optional metadata filters
    
    Returns:
        List of similar Document objects
    """
    try:
        vector_store = await initialize_vector_store()
        
        # Perform similarity search
        results = await vector_store.asimilarity_search(
            query=query,
            k=k,
            filter=filter_metadata
        )
        
        return results
    except Exception as e:
        print(f"Error searching chunks: {e}")
        return []


async def close_connections():
    """Close database connections and cleanup."""
    global _engine, _vector_store
    if _engine:
        await _engine.dispose()
        _engine = None
        _vector_store = None


# For testing/standalone use
async def main():
    """Test function for standalone execution."""
    print_section("PostgreSQL Vector Store Initialization")
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Database: {POSTGRES_DB} @ {POSTGRES_HOST}:{POSTGRES_PORT}")
    print(f"  Schema: {SCHEMA_NAME}")
    print(f"  Table: {TABLE_NAME}")
    
    try:
        vector_store = await initialize_vector_store()
        print("✓ Vector store initialized successfully")
        
        # Test: Store a sample chunk
        test_chunk_id = str(uuid.uuid4())
        test_metadata = {
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
        
        success = await store_chunk(
            chunk_text="This is a test chunk",
            chunk_id=test_chunk_id,
            metadata=test_metadata
        )
        
        if success:
            print("✓ Test chunk stored successfully")
        else:
            print("✗ Failed to store test chunk")
        
        # Test: Search
        results = await search_similar_chunks("test chunk", k=1)
        print(f"✓ Search test returned {len(results)} results")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        await close_connections()
    
    print(f"  Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
