#!/usr/bin/env python3
"""
Debug ODB vector search to see what's being returned.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.dr_off_agent.mcp.retrieval.vector_client import VectorClient

async def test_vector_search():
    """Test vector search for ODB."""
    
    # Initialize vector client
    vector_client = VectorClient(
        persist_directory="data/dr_off_agent/processed/dr_off/chroma",
        timeout_ms=5000
    )
    
    # Test queries
    queries = [
        "Is Ozempic covered for type 2 diabetes?",
        "Ozempic",
        "semaglutide"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        try:
            # Test ODB search
            results = await vector_client.search_odb(
                query=query,
                drug_class=None,
                n_results=3
            )
            
            print(f"Found {len(results)} results")
            
            for i, result in enumerate(results[:2]):
                print(f"\n--- Result {i+1} ---")
                print(f"Text preview: {result.get('text', '')[:200]}...")
                
                metadata = result.get('metadata', {})
                print(f"Metadata:")
                for key, value in metadata.items():
                    print(f"  {key}: {value}")
                
                print(f"Distance: {result.get('distance', 'N/A')}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_search())