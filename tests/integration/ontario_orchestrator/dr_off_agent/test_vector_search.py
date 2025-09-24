#!/usr/bin/env python3
"""
Test vector search functionality with corrected paths
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add project to path
sys.path.insert(0, os.getcwd())

async def test_vector_search():
    """Test vector search is working with correct paths."""
    print("\n" + "="*60)
    print("TESTING VECTOR SEARCH WITH CORRECTED PATHS")
    print("="*60)
    
    # Import the vector client
    from src.agents.ontario_orchestrator.mcp.retrieval.vector_client import VectorClient
    
    # Initialize with correct path
    vector_client = VectorClient(persist_directory="data/processed/dr_off/chroma")
    
    # Test OHIP search
    print("\n1. Testing OHIP document search:")
    print("-" * 40)
    try:
        results = await vector_client.search(
            query="MRP discharge billing C124",
            collection="ohip_documents",
            n_results=3
        )
        print(f"✅ Found {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"   Result {i}:")
            print(f"     - Text: {result['text'][:100]}...")
            print(f"     - Metadata: {result.get('metadata', {})}")
            print(f"     - Distance: {result.get('distance', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test ODB search
    print("\n2. Testing ODB document search:")
    print("-" * 40)
    try:
        results = await vector_client.search(
            query="metformin diabetes coverage",
            collection="odb_documents",
            n_results=3
        )
        print(f"✅ Found {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"   Result {i}:")
            print(f"     - Text: {result['text'][:100]}...")
            print(f"     - Metadata: {result.get('metadata', {})}")
            print(f"     - Distance: {result.get('distance', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test ADP search (may not exist)
    print("\n3. Testing ADP document search:")
    print("-" * 40)
    try:
        # First try ADP collection, then fallback to OHIP
        try:
            results = await vector_client.search(
                query="walker mobility assistive device funding",
                collection="adp_documents",
                n_results=3
            )
        except:
            print("   ADP collection not found, searching OHIP for ADP content...")
            results = await vector_client.search(
                query="assistive devices program ADP mobility walker wheelchair funding",
                collection="ohip_documents",
                n_results=3
            )
        
        print(f"✅ Found {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"   Result {i}:")
            print(f"     - Text: {result['text'][:100]}...")
            print(f"     - Metadata: {result.get('metadata', {})}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Cleanup
    await vector_client.close()
    
    print("\n" + "="*60)
    print("VECTOR SEARCH TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_vector_search())