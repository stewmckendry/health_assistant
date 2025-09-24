#!/usr/bin/env python3
"""
Test vector search without metadata filters to diagnose the issue.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.dr_opa_agent.mcp.retrieval.vector_client import VectorClient


async def test_direct_vector_search():
    """Test vector search without any filters."""
    print("\n" + "="*60)
    print("Testing Direct Vector Search (No Filters)")
    print("="*60)
    
    vector_client = VectorClient()
    
    # Modify search to not use metadata filters
    query = "informed consent medical procedures"
    print(f"\n🔍 Testing query: '{query}'")
    
    # Direct collection search without metadata filters
    collection = vector_client._collections.get('opa_cpso_corpus')
    
    if collection:
        print("✅ Collection loaded successfully")
        print(f"   Collection count: {collection.count()}")
        
        # Search without any where clause
        results = collection.query(
            query_texts=[query],
            n_results=5
        )
        
        if results and results['ids'] and results['ids'][0]:
            print(f"\n✅ Found {len(results['ids'][0])} results!")
            
            for i, (doc_id, doc, meta, dist) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {doc_id}")
                print(f"    Distance: {dist:.3f}")
                print(f"    Similarity: {max(0, 1 - (dist / 2)):.3f}")
                print(f"    Metadata keys: {list(meta.keys())}")
                print(f"    Section: {meta.get('section_heading', 'No heading')}")
                print(f"    Document: {meta.get('document_title', 'Unknown')}")
                print(f"    Source org: {meta.get('source_org', 'Unknown')}")
                print(f"    Text preview: {doc[:100]}...")
        else:
            print("❌ No results found even without filters")
    else:
        print("❌ Collection not loaded")
    
    # Now test the search_sections method
    print("\n" + "-"*60)
    print("Testing search_sections method without source filter:")
    
    results = await vector_client.search_sections(
        query=query,
        sources=None,  # No source filter
        doc_types=None,  # No doc type filter
        topics=None,  # No topic filter
        n_results=3,
        include_superseded=True  # Include everything
    )
    
    print(f"\n{'✅' if results else '❌'} Method returned {len(results)} results")
    
    for i, result in enumerate(results, 1):
        meta = result.get('metadata', {})
        print(f"\n  Result {i}:")
        print(f"    Score: {result.get('similarity_score', 0):.3f}")
        print(f"    Section: {meta.get('section_heading', 'No heading')}")
        print(f"    Source: {meta.get('source_org', 'Unknown')}")
    
    await vector_client.close()


async def test_metadata_values():
    """Check what metadata values are actually stored."""
    print("\n" + "="*60)
    print("Checking Metadata Values in Collection")
    print("="*60)
    
    vector_client = VectorClient()
    collection = vector_client._collections.get('opa_cpso_corpus')
    
    if collection:
        # Get a few documents to inspect metadata
        result = collection.get(limit=5)
        
        print(f"\n📊 Sample metadata from {len(result['ids'])} documents:")
        
        # Collect unique values for key fields
        source_orgs = set()
        doc_types = set()
        is_superseded_values = set()
        
        for i, meta in enumerate(result['metadatas'][:5], 1):
            print(f"\nDocument {i}:")
            for key, value in sorted(meta.items()):
                print(f"  {key}: {value} (type: {type(value).__name__})")
                
                if key == 'source_org':
                    source_orgs.add(value)
                elif key == 'document_type':
                    doc_types.add(value)
                elif key == 'is_superseded':
                    is_superseded_values.add(value)
        
        print("\n📈 Unique values found:")
        print(f"  source_org values: {source_orgs}")
        print(f"  document_type values: {doc_types}")
        print(f"  is_superseded values: {is_superseded_values}")
    
    await vector_client.close()


async def main():
    """Run diagnostic tests."""
    await test_direct_vector_search()
    await test_metadata_values()


if __name__ == "__main__":
    asyncio.run(main())