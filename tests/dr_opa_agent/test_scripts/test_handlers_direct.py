#!/usr/bin/env python3
"""
Direct test of MCP handler functions for Dr. OPA.
Tests the actual handler logic without FastMCP decorators.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Import retrieval clients and utilities directly
from src.agents.dr_opa_agent.mcp.retrieval import SQLClient, VectorClient
from src.agents.dr_opa_agent.mcp.utils.confidence import OPAConfidenceScorer
from src.agents.dr_opa_agent.mcp.utils.conflicts import resolve_conflicts


async def test_sql_client():
    """Test SQL client directly."""
    print("\n" + "="*50)
    print("Testing SQL Client")
    print("="*50)
    
    sql_client = SQLClient()
    
    # Test search
    print("\n1. Testing search_sections...")
    try:
        results = await sql_client.search_sections(
            query="medical records",
            sources=["cpso"],
            limit=5
        )
        print(f"   Found {len(results)} sections")
        if results:
            print(f"   First result: {results[0].get('section_heading', 'No heading')}")
            print(f"   From: {results[0].get('document_title', 'Unknown')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test policy search
    print("\n2. Testing search_policies...")
    try:
        results = await sql_client.search_policies(
            topic="consent",
            policy_level=None,
            include_related=True
        )
        print(f"   Found {len(results)} policies")
        if results:
            print(f"   First policy: {results[0].get('title', 'No title')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test freshness check
    print("\n3. Testing check_freshness...")
    try:
        result = await sql_client.check_freshness(
            topic="telemedicine",
            sources=["cpso"]
        )
        current = result.get('current_guidance')
        if current:
            print(f"   Current guidance: {current.get('title', 'No title')}")
            print(f"   Last updated: {result.get('last_updated', 'Unknown')}")
        else:
            print("   No guidance found")
    except Exception as e:
        print(f"   Error: {e}")
    
    await sql_client.close()


async def test_vector_client():
    """Test vector client directly."""
    print("\n" + "="*50)
    print("Testing Vector Client")
    print("="*50)
    
    vector_client = VectorClient()
    
    # Test search
    print("\n1. Testing search_sections...")
    try:
        results = await vector_client.search_sections(
            query="prescribing opioids chronic pain",
            sources=["cpso"],
            n_results=5
        )
        print(f"   Found {len(results)} vector matches")
        if results:
            print(f"   Top match similarity: {results[0].get('similarity_score', 0):.3f}")
            metadata = results[0].get('metadata', {})
            print(f"   From: {metadata.get('document_title', 'Unknown')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test similarity search
    print("\n2. Testing find_similar...")
    try:
        results = await vector_client.find_similar(
            text="informed consent for surgical procedures",
            n_results=3
        )
        print(f"   Found {len(results)} similar documents")
    except Exception as e:
        print(f"   Error: {e}")
    
    await vector_client.close()


async def test_hybrid_search():
    """Test hybrid SQL + vector search."""
    print("\n" + "="*50)
    print("Testing Hybrid Search (SQL + Vector)")
    print("="*50)
    
    sql_client = SQLClient()
    vector_client = VectorClient()
    
    query = "virtual care telemedicine requirements"
    
    print(f"\nSearching for: '{query}'")
    
    # Run both searches
    sql_task = sql_client.search_sections(query=query, limit=5)
    vector_task = vector_client.search_sections(query=query, n_results=5)
    
    sql_results, vector_results = await asyncio.gather(sql_task, vector_task)
    
    print(f"\nSQL Results: {len(sql_results)} documents")
    print(f"Vector Results: {len(vector_results)} documents")
    
    # Resolve conflicts
    resolved_data, conflicts = resolve_conflicts(sql_results, vector_results)
    
    print(f"Resolved Results: {len(resolved_data)} unique documents")
    print(f"Conflicts: {len(conflicts)}")
    
    # Calculate confidence
    confidence = OPAConfidenceScorer.calculate(
        sql_hits=len(sql_results),
        vector_matches=len(vector_results),
        sources=["cpso"],
        has_conflict=len(conflicts) > 0
    )
    
    print(f"Confidence Score: {confidence:.2f}")
    print(f"Confidence Level: {OPAConfidenceScorer.get_confidence_level(confidence)}")
    
    await sql_client.close()
    await vector_client.close()


async def test_specific_queries():
    """Test specific clinical queries."""
    print("\n" + "="*50)
    print("Testing Specific Clinical Queries")
    print("="*50)
    
    sql_client = SQLClient()
    
    queries = [
        "prescribing controlled substances",
        "informed consent",
        "medical records retention",
        "telemedicine virtual care",
        "mandatory reporting",
        "conflict of interest"
    ]
    
    for query in queries:
        print(f"\n'{query}':")
        try:
            results = await sql_client.search_sections(
                query=query,
                sources=["cpso"],
                limit=3
            )
            print(f"  Found {len(results)} results")
            
            # Show document types found
            doc_types = set(r.get('document_type', 'unknown') for r in results)
            print(f"  Document types: {', '.join(doc_types)}")
            
            # Show topics
            all_topics = set()
            for r in results:
                topics = r.get('topics', [])
                if isinstance(topics, list):
                    all_topics.update(topics)
            if all_topics:
                print(f"  Topics: {', '.join(list(all_topics)[:3])}")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    await sql_client.close()


async def save_test_results(results, filename):
    """Save test results to JSON file."""
    output_dir = Path("tests/dr_opa_agent/test_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"{filename}_{timestamp}.json"
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✓ Results saved to: {filepath}")
    return filepath


async def main():
    """Run all direct handler tests."""
    print("\n" + "="*60)
    print("Dr. OPA MCP Direct Handler Tests")
    print("="*60)
    
    results = {}
    
    # Test SQL client
    print("\nPhase 1: SQL Client Tests")
    await test_sql_client()
    
    # Test vector client
    print("\nPhase 2: Vector Client Tests")
    await test_vector_client()
    
    # Test hybrid search
    print("\nPhase 3: Hybrid Search Test")
    await test_hybrid_search()
    
    # Test specific queries
    print("\nPhase 4: Specific Query Tests")
    await test_specific_queries()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())