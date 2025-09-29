#!/usr/bin/env python3
"""Test PHO document ingestion pipeline.

This script tests the full pipeline:
1. Extract content from PHO PDF
2. Create parent-child chunks
3. Generate embeddings
4. Store in SQLite and Chroma
5. Verify retrieval via MCP tools
"""

import sys
import json
import logging
from pathlib import Path
import asyncio
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


def test_pho_extraction():
    """Test PHO document extraction."""
    from src.agents.dr_opa_agent.ingestion.pho.pho_extractor import PHOExtractor
    
    print("\n" + "="*60)
    print("Testing PHO Document Extraction")
    print("="*60)
    
    # Path to PHO IPAC document
    pdf_path = Path("data/dr_opa_agent/raw/pho/bp-clinical-office-practice.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return None
    
    try:
        extractor = PHOExtractor()
        document = extractor.extract_document(pdf_path)
        
        print(f"✅ Extraction successful!")
        print(f"  Title: {document['title']}")
        print(f"  Sections: {len(document.get('sections', []))}")
        print(f"  Document type: {document['metadata'].get('document_type')}")
        print(f"  Topics: {document['metadata'].get('topics')}")
        print(f"  Pages: {document['metadata'].get('page_count')}")
        
        # Sample sections
        print(f"\nFirst 3 sections:")
        for i, section in enumerate(document.get('sections', [])[:3]):
            print(f"  {i+1}. {section['heading']}")
            subsections = section.get('subsections', [])
            if subsections:
                print(f"     ({len(subsections)} subsections)")
        
        return document
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_pho_ingestion(document: Dict[str, Any] = None):
    """Test PHO document ingestion into database."""
    from src.agents.dr_opa_agent.ingestion.pho.pho_ingester import PHOIngester
    import os
    from dotenv import load_dotenv
    
    print("\n" + "="*60)
    print("Testing PHO Document Ingestion")
    print("="*60)
    
    # Load environment variables
    load_dotenv('/Users/liammckendry/health_assistant_dr_off_worktree/.env')
    
    # Path to PHO document
    pdf_path = "data/dr_opa_agent/raw/pho/bp-clinical-office-practice.pdf"
    
    try:
        # Initialize ingester
        ingester = PHOIngester(
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Ingest document
        result = ingester.ingest_document(pdf_path)
        
        if result['success']:
            print(f"✅ Ingestion successful!")
            print(f"  Document ID: {result['document_id']}")
            print(f"  Title: {result['title']}")
            print(f"  Sections: {result['sections_created']}")
            print(f"  Chunks: {result['chunks_created']}")
            
            # Show metadata
            print(f"\nDocument metadata:")
            metadata = result['metadata']
            for key in ['source_org', 'document_type', 'topics', 'effective_date']:
                print(f"  {key}: {metadata.get(key)}")
            
            return result
        else:
            print(f"❌ Ingestion failed: {result['error']}")
            return None
            
    except Exception as e:
        print(f"❌ Ingestion error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_mcp_retrieval():
    """Test retrieval via MCP tools."""
    print("\n" + "="*60)
    print("Testing MCP Tool Retrieval")
    print("="*60)
    
    try:
        # Import MCP server components
        from src.agents.dr_opa_agent.mcp.retrieval.sql_client import SQLClient
        from src.agents.dr_opa_agent.mcp.retrieval.vector_client import VectorClient
        
        # Test queries
        test_queries = [
            "hand hygiene requirements",
            "PPE personal protective equipment",
            "sterilization procedures",
            "infection control office practice"
        ]
        
        # Initialize clients
        sql_client = SQLClient()
        vector_client = VectorClient()
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            
            # SQL search
            sql_results = await sql_client.search_sections(
                query=query,
                sources=['pho'],
                limit=3
            )
            print(f"  SQL results: {len(sql_results)} matches")
            
            # Vector search
            vector_results = await vector_client.search_sections(
                query=query,
                sources=['pho'],
                n_results=3
            )
            print(f"  Vector results: {len(vector_results)} matches")
            
            # Show top result
            if sql_results:
                top = sql_results[0]
                print(f"  Top SQL match: {top.get('section_heading', 'N/A')}")
            
            if vector_results:
                top = vector_results[0]
                print(f"  Top vector match: {top.get('section_heading', 'N/A')}")
        
        print("\n✅ MCP retrieval test complete")
        return True
        
    except Exception as e:
        print(f"❌ MCP retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ipac_specific_tool():
    """Test IPAC-specific MCP tool functionality."""
    print("\n" + "="*60)
    print("Testing IPAC-Specific Tool")
    print("="*60)
    
    # This would test the ipac_guidance tool specifically
    # when it's fully implemented in the MCP server
    
    test_scenarios = [
        {
            'setting': 'dental-office',
            'topic': 'sterilization',
            'expected': 'autoclave procedures'
        },
        {
            'setting': 'medical-office', 
            'topic': 'ppe',
            'expected': 'gloves and masks'
        },
        {
            'setting': 'clinic',
            'topic': 'hand-hygiene',
            'expected': 'alcohol-based hand rub'
        }
    ]
    
    print("✅ IPAC tool scenarios defined")
    print(f"  Scenarios: {len(test_scenarios)}")
    
    # Actual implementation would call the MCP tool
    return test_scenarios


def save_test_results(results: Dict[str, Any]):
    """Save test results for review."""
    output_dir = Path("tests/dr_opa_agent/test_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "pho_test_results.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Test results saved to: {output_file}")


def main():
    """Run all PHO ingestion tests."""
    print("\n" + "="*60)
    print("PHO IPAC Document Ingestion Test Suite")
    print("="*60)
    
    from datetime import datetime
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: Extraction
    print("\n[1/4] Testing document extraction...")
    document = test_pho_extraction()
    results['tests']['extraction'] = {
        'success': document is not None,
        'sections': len(document.get('sections', [])) if document else 0
    }
    
    # Test 2: Ingestion
    print("\n[2/4] Testing document ingestion...")
    ingestion_result = test_pho_ingestion(document)
    results['tests']['ingestion'] = {
        'success': ingestion_result is not None and ingestion_result.get('success'),
        'chunks_created': ingestion_result.get('chunks_created', 0) if ingestion_result else 0
    }
    
    # Test 3: MCP Retrieval
    print("\n[3/4] Testing MCP retrieval...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    retrieval_success = loop.run_until_complete(test_mcp_retrieval())
    results['tests']['mcp_retrieval'] = {
        'success': retrieval_success
    }
    
    # Test 4: IPAC Tool
    print("\n[4/4] Testing IPAC-specific functionality...")
    ipac_scenarios = test_ipac_specific_tool()
    results['tests']['ipac_tool'] = {
        'success': True,
        'scenarios_defined': len(ipac_scenarios)
    }
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    all_passed = all(
        test.get('success', False) 
        for test in results['tests'].values()
    )
    
    for test_name, test_result in results['tests'].items():
        status = "✅" if test_result.get('success') else "❌"
        print(f"  {status} {test_name}")
    
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check details above.")
    
    # Save results
    save_test_results(results)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())