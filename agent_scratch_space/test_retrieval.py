#!/usr/bin/env python3
"""
Diagnostic script to test the retrieval pipeline.
Identifies issues with semantic search, patient filtering, and embedding quality.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, rely on environment


async def test_database_connection():
    """Test 1: Verify database connection works."""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    from api.database.postgres import initialize_vector_store
    try:
        store = await initialize_vector_store()
        print("✓ Vector store initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize vector store: {e}")
        return False


async def test_basic_search():
    """Test 2: Basic semantic search without patient filter."""
    print("\n" + "="*60)
    print("TEST 2: Basic Semantic Search (no patient filter)")
    print("="*60)
    
    from api.database.postgres import search_similar_chunks
    
    test_queries = [
        "diabetes mellitus",
        "blood pressure",
        "medication history",
        "Observation",
    ]
    
    for query in test_queries:
        results = await search_similar_chunks(query, k=5)
        print(f"\nQuery: '{query}'")
        print(f"  Results: {len(results)} chunks")
        if results:
            first = results[0]
            print(f"  First chunk preview: {first.page_content[:100]}...")
            print(f"  Metadata keys: {list(first.metadata.keys())}")
        else:
            print("  ⚠️ NO RESULTS - This is unexpected!")


async def test_patient_filtered_search():
    """Test 3: Search with patient_id filter - compare semantic vs hybrid."""
    print("\n" + "="*60)
    print("TEST 3: Patient-Filtered Search (Semantic vs Hybrid)")
    print("="*60)
    
    from api.database.postgres import search_similar_chunks, hybrid_search
    import asyncpg
    
    # First, get a real patient ID from the database
    conn = await asyncpg.connect(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
    )
    
    try:
        row = await conn.fetchrow("""
            SELECT langchain_metadata->>'patient_id' as patient_id,
                   COUNT(*) as chunk_count
            FROM hc_ai_schema.hc_ai_table
            GROUP BY langchain_metadata->>'patient_id'
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """)
        
        if not row:
            print("✗ No patients found in database!")
            return
        
        patient_id = row['patient_id']
        chunk_count = row['chunk_count']
        print(f"Testing with patient: {patient_id}")
        print(f"  This patient has {chunk_count} chunks in database")
        
        # Test 3a: Semantic-only search
        print("\n  [3a] Semantic-only search:")
        semantic_results = await search_similar_chunks(
            "medications prescribed",
            k=10,
            filter_metadata={"patient_id": patient_id}
        )
        print(f"       Results: {len(semantic_results)} chunks")
        if len(semantic_results) == 0:
            print("       ⚠️ NO RESULTS with semantic-only!")
        
        # Test 3b: Hybrid search (BM25 + semantic)
        print("\n  [3b] Hybrid search (BM25 + semantic):")
        hybrid_results = await hybrid_search(
            "medications prescribed",
            k=10,
            filter_metadata={"patient_id": patient_id}
        )
        print(f"       Results: {len(hybrid_results)} chunks")
        if len(hybrid_results) > 0:
            print("       ✓ Hybrid search found results!")
            for i, doc in enumerate(hybrid_results[:3]):
                print(f"       Result {i+1}: {doc.page_content[:80]}...")
                hybrid_score = doc.metadata.get('_hybrid_score', 'N/A')
                bm25_comp = doc.metadata.get('_bm25_component', 0)
                sem_comp = doc.metadata.get('_semantic_component', 0)
                print(f"         Score: {hybrid_score:.3f} (BM25: {bm25_comp:.2f}, Semantic: {sem_comp:.2f})")
        else:
            print("       ⚠️ NO RESULTS even with hybrid!")
            
        # Summary
        print(f"\n  COMPARISON:")
        print(f"    Semantic-only: {len(semantic_results)} results")
        print(f"    Hybrid (BM25+Semantic): {len(hybrid_results)} results")
        if len(hybrid_results) > len(semantic_results):
            print("    ✓ Hybrid search improved results!")
                
    finally:
        await conn.close()


async def test_reranker_service():
    """Test 4: Test the HTTP reranker service."""
    print("\n" + "="*60)
    print("TEST 4: Reranker HTTP Service")
    print("="*60)
    
    import httpx
    
    reranker_url = os.getenv("RERANKER_SERVICE_URL", "http://localhost:8000/retrieval")
    url = f"{reranker_url}/rerank"
    
    payload = {
        "query": "blood pressure readings",
        "k_retrieve": 20,
        "k_return": 5,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            print(f"✓ Reranker returned {len(results)} results")
            
            if results:
                first = results[0]
                print(f"  First result preview: {first.get('content', '')[:100]}...")
                print(f"  Score: {first.get('score', 'N/A')}")
            else:
                print("  ⚠️ No results from reranker")
                
    except httpx.ConnectError:
        print(f"✗ Cannot connect to {url}")
        print("  Is the API server running on port 8000?")
    except Exception as e:
        print(f"✗ Reranker request failed: {e}")


async def test_embedding_quality():
    """Test 5: Check embedding quality."""
    print("\n" + "="*60)
    print("TEST 5: Embedding Quality Check")
    print("="*60)
    
    from api.embeddings.utils.helper import get_chunk_embedding
    
    test_texts = [
        "The patient has type 2 diabetes mellitus",
        "Blood pressure: 120/80 mmHg",
        "Hello world test",
    ]
    
    for text in test_texts:
        embedding = get_chunk_embedding(text)
        if embedding:
            print(f"\nText: '{text[:50]}...'")
            print(f"  Embedding dim: {len(embedding)}")
            print(f"  First 5 values: {embedding[:5]}")
            
            # Check for zero/nan embeddings
            non_zero = sum(1 for x in embedding if x != 0)
            print(f"  Non-zero values: {non_zero}/{len(embedding)}")
        else:
            print(f"\n✗ Failed to get embedding for: '{text[:50]}'")


async def analyze_retrieval_problem():
    """Main analysis: compare semantic vs hybrid for finding specific patient data."""
    print("\n" + "="*60)
    print("ANALYSIS: Semantic vs Hybrid Search Comparison")
    print("="*60)
    
    from api.database.postgres import search_similar_chunks, hybrid_search
    import asyncpg
    
    conn = await asyncpg.connect(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
    )
    
    try:
        # Get a sample chunk content to search for
        sample = await conn.fetchrow("""
            SELECT content, langchain_metadata->>'patient_id' as patient_id
            FROM hc_ai_schema.hc_ai_table
            WHERE content ILIKE '%diabetes%'
            LIMIT 1
        """)
        
        if not sample:
            print("No chunks containing 'diabetes' found in database")
            return
        
        print(f"Target: Find diabetes chunk for patient: {sample['patient_id']}")
        print(f"Content preview: {sample['content'][:150]}...")
        
        # Test 1: Semantic-only search
        print("\n[Semantic-only search for 'diabetes']")
        semantic_results = await search_similar_chunks("diabetes", k=20)
        
        semantic_found = False
        for doc in semantic_results:
            if doc.metadata.get('patient_id') == sample['patient_id']:
                semantic_found = True
                break
        print(f"  Results: {len(semantic_results)} chunks")
        print(f"  Target patient found: {'✓ Yes' if semantic_found else '✗ No'}")
        
        # Test 2: Hybrid search
        print("\n[Hybrid search for 'diabetes']")
        hybrid_results = await hybrid_search("diabetes", k=20)
        
        hybrid_found = False
        for doc in hybrid_results:
            if doc.metadata.get('patient_id') == sample['patient_id']:
                hybrid_found = True
                break
        print(f"  Results: {len(hybrid_results)} chunks")
        print(f"  Target patient found: {'✓ Yes' if hybrid_found else '✗ No'}")
        
        # Summary
        print("\n" + "-"*40)
        if hybrid_found and not semantic_found:
            print("✓ Hybrid search found target patient that semantic-only missed!")
        elif hybrid_found and semantic_found:
            print("✓ Both methods found the target patient")
        elif not hybrid_found and not semantic_found:
            print("⚠️ Neither method found the target patient - may need more candidates")
        else:
            print("Semantic found it but hybrid didn't - unexpected")
            
    finally:
        await conn.close()


async def main():
    print("="*60)
    print("RETRIEVAL PIPELINE DIAGNOSTIC")
    print("="*60)
    
    await test_database_connection()
    await test_basic_search()
    await test_patient_filtered_search()
    await test_reranker_service()
    await test_embedding_quality()
    await analyze_retrieval_problem()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
