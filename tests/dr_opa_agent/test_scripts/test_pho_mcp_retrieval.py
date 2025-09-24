#!/usr/bin/env python3
"""Test PHO retrieval through MCP tools after fixing issues."""

import sys
import asyncio
import logging
from pathlib import Path
import json
from typing import Dict, Any

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_vector_client_collections():
    """Test that vector client loads PHO collection."""
    print("\n" + "="*60)
    print("Testing Vector Client Collections")
    print("="*60)
    
    from src.agents.dr_opa_agent.mcp.retrieval.vector_client import VectorClient
    
    try:
        # Initialize vector client
        client = VectorClient()
        
        # Check loaded collections
        print(f"\nLoaded collections:")
        for name in client._collections.keys():
            print(f"  - {name}")
        
        # Check if PHO collection exists
        if 'opa_pho_corpus' in client._collections:
            print("\n✅ PHO collection found!")
            
            # Get collection stats
            pho_collection = client._collections['opa_pho_corpus']
            count = pho_collection.count()
            print(f"  Documents in PHO collection: {count}")
        else:
            print("\n❌ PHO collection not found")
            print("  Available collections:", list(client._collections.keys()))
        
        return 'opa_pho_corpus' in client._collections
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_direct_vector_search():
    """Test direct vector search on PHO collection."""
    print("\n" + "="*60)
    print("Testing Direct Vector Search")
    print("="*60)
    
    from src.agents.dr_opa_agent.mcp.retrieval.vector_client import VectorClient
    
    try:
        client = VectorClient()
        
        # Test queries
        queries = [
            "hand hygiene alcohol-based hand rub",
            "personal protective equipment gloves masks",
            "sterilization autoclave procedures",
            "infection prevention control clinical office"
        ]
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            
            # Search with PHO source filter
            results = await client.search_sections(
                query=query,
                sources=['pho'],
                n_results=3
            )
            
            print(f"  Results: {len(results)} found")
            
            if results:
                top_result = results[0]
                print(f"  Top match:")
                print(f"    Collection: {top_result.get('collection', 'N/A')}")
                print(f"    Score: {top_result.get('similarity_score', 0):.3f}")
                metadata = top_result.get('metadata', {})
                print(f"    Section: {metadata.get('section_heading', 'N/A')}")
                print(f"    Text preview: {top_result.get('text', '')[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_search_tool():
    """Test MCP search_sections tool with PHO content."""
    print("\n" + "="*60)
    print("Testing MCP Search Tool")
    print("="*60)
    
    try:
        # Import MCP handlers
        from src.agents.dr_opa_agent.mcp.server import search_sections_handler
        
        # Test search with PHO filter
        result = await search_sections_handler(
            query="hand hygiene requirements clinical office",
            sources=['pho'],
            doc_types=['ipac-guidance'],
            top_k=5
        )
        
        print(f"\nMCP Search Results:")
        print(f"  Total matches: {result.get('total_matches', 0)}")
        print(f"  Sources found: {result.get('sources_searched', [])}")
        
        sections = result.get('sections', [])
        if sections:
            print(f"\nTop 3 sections:")
            for i, section in enumerate(sections[:3]):
                print(f"\n  {i+1}. {section.get('heading', 'N/A')}")
                print(f"     Document: {section.get('document_id', 'N/A')}")
                print(f"     Score: {section.get('relevance_score', 0):.3f}")
                print(f"     Text: {section.get('text', '')[:100]}...")
        
        # Test conflicts detection
        conflicts = result.get('conflicts', [])
        if conflicts:
            print(f"\n  Conflicts detected: {len(conflicts)}")
        
        return len(sections) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ipac_specific_queries():
    """Test IPAC-specific queries that should match PHO content."""
    print("\n" + "="*60)
    print("Testing IPAC-Specific Queries")
    print("="*60)
    
    from src.agents.dr_opa_agent.mcp.retrieval.sql_client import SQLClient
    from src.agents.dr_opa_agent.mcp.retrieval.vector_client import VectorClient
    
    # IPAC-specific test cases
    test_cases = [
        {
            'query': 'autoclave sterilization temperature time',
            'expected_topics': ['sterilization', 'ipac']
        },
        {
            'query': 'N95 respirator fit testing requirements',
            'expected_topics': ['ppe', 'ipac']
        },
        {
            'query': 'hand hygiene moments healthcare',
            'expected_topics': ['hand-hygiene', 'ipac']
        },
        {
            'query': 'sharps disposal biomedical waste',
            'expected_topics': ['ipac', 'clinical-office']
        }
    ]
    
    sql_client = SQLClient()
    vector_client = VectorClient()
    
    results_summary = []
    
    for test in test_cases:
        print(f"\n📋 Query: '{test['query']}'")
        print(f"   Expected topics: {test['expected_topics']}")
        
        # Vector search
        vector_results = await vector_client.search_sections(
            query=test['query'],
            sources=['pho'],
            n_results=3
        )
        
        # SQL search
        sql_results = await sql_client.search_sections(
            query=test['query'],
            sources=['pho'],
            limit=3
        )
        
        print(f"   Vector results: {len(vector_results)}")
        print(f"   SQL results: {len(sql_results)}")
        
        # Check if expected topics are found
        found_topics = set()
        for result in vector_results + sql_results:
            metadata = result.get('metadata', {})
            topics = metadata.get('topics', '')
            if isinstance(topics, str):
                found_topics.update(topics.split(','))
        
        matched_topics = set(test['expected_topics']).intersection(found_topics)
        print(f"   Matched topics: {matched_topics}")
        
        success = len(matched_topics) > 0
        print(f"   {'✅' if success else '❌'} Result: {'PASS' if success else 'FAIL'}")
        
        results_summary.append({
            'query': test['query'],
            'success': success,
            'vector_count': len(vector_results),
            'sql_count': len(sql_results),
            'matched_topics': list(matched_topics)
        })
    
    # Summary
    print("\n" + "="*60)
    print("IPAC Query Test Summary")
    print("="*60)
    
    passed = sum(1 for r in results_summary if r['success'])
    total = len(results_summary)
    
    print(f"\nResults: {passed}/{total} queries passed")
    
    for result in results_summary:
        status = "✅" if result['success'] else "❌"
        print(f"  {status} {result['query'][:40]}... (V:{result['vector_count']} S:{result['sql_count']})")
    
    return passed == total


def save_test_results(results: Dict[str, Any]):
    """Save test results to file."""
    output_dir = Path("tests/dr_opa_agent/test_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "pho_mcp_test_results.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Results saved to: {output_file}")


async def main():
    """Run all PHO MCP retrieval tests."""
    print("\n" + "="*60)
    print("PHO MCP Retrieval Test Suite")
    print("="*60)
    
    from datetime import datetime
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: Check collections
    print("\n[1/4] Testing vector client collections...")
    collection_found = await test_vector_client_collections()
    results['tests']['collections'] = {
        'success': collection_found,
        'pho_collection_found': collection_found
    }
    
    # Test 2: Direct vector search
    print("\n[2/4] Testing direct vector search...")
    vector_success = await test_direct_vector_search()
    results['tests']['vector_search'] = {
        'success': vector_success
    }
    
    # Test 3: MCP search tool
    print("\n[3/4] Testing MCP search tool...")
    mcp_success = await test_mcp_search_tool()
    results['tests']['mcp_tool'] = {
        'success': mcp_success
    }
    
    # Test 4: IPAC-specific queries
    print("\n[4/4] Testing IPAC-specific queries...")
    ipac_success = await test_ipac_specific_queries()
    results['tests']['ipac_queries'] = {
        'success': ipac_success
    }
    
    # Overall summary
    print("\n" + "="*60)
    print("Overall Test Summary")
    print("="*60)
    
    for test_name, test_result in results['tests'].items():
        status = "✅" if test_result.get('success') else "❌"
        print(f"  {status} {test_name}")
    
    all_passed = all(t.get('success') for t in results['tests'].values())
    
    if all_passed:
        print("\n🎉 All tests passed! PHO content is accessible via MCP tools.")
    else:
        print("\n⚠️ Some tests failed. Check details above.")
    
    save_test_results(results)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    load_dotenv('/Users/liammckendry/health_assistant_dr_off_worktree/.env')
    
    # Run async main
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    exit_code = loop.run_until_complete(main())
    sys.exit(exit_code)