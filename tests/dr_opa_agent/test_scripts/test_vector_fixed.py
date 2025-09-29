#!/usr/bin/env python3
"""
Test vector search after fixing embedding dimensions.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.dr_opa_agent.mcp.retrieval import SQLClient, VectorClient
from src.agents.dr_opa_agent.mcp.utils.confidence import OPAConfidenceScorer
from src.agents.dr_opa_agent.mcp.utils.conflicts import resolve_conflicts


async def test_vector_search():
    """Test vector search functionality after fix."""
    print("\n" + "="*60)
    print("Testing Vector Search After Embedding Fix")
    print("="*60)
    
    vector_client = VectorClient()
    
    test_queries = [
        "informed consent for medical procedures",
        "prescribing controlled substances opioids",
        "telemedicine virtual care requirements",
        "medical records retention and privacy",
        "mandatory reporting obligations",
        "conflict of interest disclosure"
    ]
    
    for query in test_queries:
        print(f"\n📍 Query: '{query}'")
        print("-" * 50)
        
        try:
            results = await vector_client.search_sections(
                query=query,
                sources=["cpso"],
                n_results=3
            )
            
            print(f"✅ Found {len(results)} results")
            
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                similarity = result.get('similarity_score', 0)
                heading = metadata.get('section_heading', 'No heading')
                doc_title = metadata.get('document_title', 'Unknown document')
                doc_type = metadata.get('document_type', 'unknown')
                
                print(f"\n  {i}. Score: {similarity:.3f}")
                print(f"     Section: {heading}")
                print(f"     Document: {doc_title}")
                print(f"     Type: {doc_type}")
                print(f"     Text preview: {result.get('text', '')[:100]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    await vector_client.close()


async def test_hybrid_search():
    """Test combined SQL and vector search."""
    print("\n" + "="*60)
    print("Testing Hybrid Search (SQL + Vector)")
    print("="*60)
    
    sql_client = SQLClient()
    vector_client = VectorClient()
    
    query = "informed consent documentation requirements"
    print(f"\n🔍 Query: '{query}'")
    
    # Run both searches in parallel
    sql_task = sql_client.search_sections(query=query, limit=5)
    vector_task = vector_client.search_sections(query=query, n_results=5)
    
    sql_results, vector_results = await asyncio.gather(sql_task, vector_task)
    
    print(f"\n📊 Results:")
    print(f"  SQL: {len(sql_results)} documents")
    print(f"  Vector: {len(vector_results)} documents")
    
    # Show SQL results
    if sql_results:
        print("\n  SQL Top Results:")
        for i, r in enumerate(sql_results[:3], 1):
            print(f"    {i}. {r.get('section_heading', 'No heading')} - {r.get('document_title', 'Unknown')}")
    
    # Show vector results
    if vector_results:
        print("\n  Vector Top Results:")
        for i, r in enumerate(vector_results[:3], 1):
            meta = r.get('metadata', {})
            print(f"    {i}. {meta.get('section_heading', 'No heading')} - {meta.get('document_title', 'Unknown')} (score: {r.get('similarity_score', 0):.3f})")
    
    # Resolve conflicts and merge
    resolved_data, conflicts = resolve_conflicts(sql_results, vector_results)
    
    print(f"\n🔄 Merged Results:")
    print(f"  Unique documents: {len(resolved_data)}")
    print(f"  Conflicts detected: {len(conflicts)}")
    
    # Calculate confidence
    confidence = OPAConfidenceScorer.calculate(
        sql_hits=len(sql_results),
        vector_matches=len(vector_results),
        sources=["cpso"],
        has_conflict=len(conflicts) > 0
    )
    
    print(f"\n📈 Confidence:")
    print(f"  Score: {confidence:.2f}")
    print(f"  Level: {OPAConfidenceScorer.get_confidence_level(confidence)}")
    print(f"  Explanation: {OPAConfidenceScorer.explain_score(len(sql_results), len(vector_results), ['cpso'], len(conflicts) > 0)}")
    
    await sql_client.close()
    await vector_client.close()


async def test_specific_sections():
    """Test retrieval of specific known sections."""
    print("\n" + "="*60)
    print("Testing Specific Section Retrieval")
    print("="*60)
    
    vector_client = VectorClient()
    
    # Test getting passages by ID (if we have any IDs from previous results)
    print("\n📦 Testing passage retrieval by ID...")
    
    # First get some IDs
    results = await vector_client.search_sections(
        query="medical records",
        n_results=2
    )
    
    if results:
        chunk_ids = [r.get('chunk_id') for r in results if r.get('chunk_id')]
        
        if chunk_ids:
            print(f"  Found {len(chunk_ids)} chunk IDs to retrieve")
            
            passages = await vector_client.get_passages_by_ids(
                chunk_ids=chunk_ids,
                collection="opa_cpso_corpus"
            )
            
            print(f"  ✅ Retrieved {len(passages)} passages")
            
            for passage in passages:
                meta = passage.get('metadata', {})
                print(f"\n  ID: {passage.get('id')}")
                print(f"  Section: {meta.get('section_heading', 'No heading')}")
                print(f"  Text length: {len(passage.get('text', ''))}")
    
    await vector_client.close()


async def main():
    """Run all vector tests."""
    print("\n" + "="*70)
    print(" Vector Search Test Suite - Post-Fix Verification")
    print("="*70)
    
    # Test 1: Basic vector search
    await test_vector_search()
    
    # Test 2: Hybrid search
    await test_hybrid_search()
    
    # Test 3: Specific section retrieval
    await test_specific_sections()
    
    print("\n" + "="*70)
    print(" ✅ All Vector Tests Complete!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())