#!/usr/bin/env python3
"""
Test MCP tools using FastMCP client
Tests both SQL and vector paths are working together
"""
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables for OpenAI API key
load_dotenv()

# Import the MCP tools directly
from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
from src.agents.ontario_orchestrator.mcp.tools.odb import odb_get
from src.agents.ontario_orchestrator.mcp.tools.source import source_passages

async def test_schedule_get():
    """Test schedule.get tool with both SQL and vector."""
    print("\n" + "="*60)
    print("TESTING SCHEDULE.GET (SQL + VECTOR)")
    print("="*60)
    
    request = {
        "q": "C124 MRP discharge billing after 72 hours",
        "codes": ["C124"],
        "include": ["codes", "fee", "limits", "documentation"],
        "top_k": 5
    }
    
    print(f"\nRequest: {json.dumps(request, indent=2)}")
    
    try:
        start = datetime.now()
        result = await schedule_get(request)
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"\n✅ Response in {elapsed:.2f}s")
        print(f"Provenance: {result.get('provenance', [])}")
        print(f"Confidence: {result.get('confidence', 0):.3f}")
        
        items = result.get('items', [])
        print(f"Items found: {len(items)}")
        
        for item in items[:2]:
            print(f"\n  Code: {item.get('code')}")
            print(f"  Description: {item.get('description', 'N/A')[:80]}...")
            print(f"  Fee: ${item.get('fee', 0):.2f}")
            if item.get('requirements'):
                print(f"  Requirements: {item.get('requirements')[:100]}...")
        
        citations = result.get('citations', [])
        print(f"\nCitations: {len(citations)}")
        for cite in citations[:3]:
            print(f"  - {cite.get('source')} @ page {cite.get('page')}")
        
        # Check if both SQL and vector worked
        if 'sql' in result.get('provenance', []) and 'vector' in result.get('provenance', []):
            print("\n✅ DUAL-PATH RETRIEVAL CONFIRMED")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_odb_get():
    """Test odb.get tool with both SQL and vector."""
    print("\n" + "="*60)
    print("TESTING ODB.GET (SQL + VECTOR)")
    print("="*60)
    
    request = {
        "q": "metformin coverage and cheaper alternatives",
        "drug": "metformin",
        "check": ["coverage", "interchangeable", "lowest_cost"],
        "top_k": 5
    }
    
    print(f"\nRequest: {json.dumps(request, indent=2)}")
    
    try:
        start = datetime.now()
        result = await odb_get(request)
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"\n✅ Response in {elapsed:.2f}s")
        print(f"Provenance: {result.get('provenance', [])}")
        print(f"Confidence: {result.get('confidence', 0):.3f}")
        
        coverage = result.get('coverage')
        if coverage:
            print(f"\nCoverage:")
            print(f"  - Covered: {coverage.get('covered')}")
            print(f"  - Generic name: {coverage.get('generic_name')}")
            print(f"  - LU Required: {coverage.get('lu_required')}")
        
        interchangeable = result.get('interchangeable')
        if interchangeable:
            members = interchangeable.get('members', [])
            print(f"\nInterchangeable drugs: {len(members)}")
            for drug in members[:3]:
                print(f"  - {drug.get('brand')}: ${drug.get('price', 0):.2f}")
                if drug.get('lowest_cost'):
                    print("    ⭐ LOWEST COST")
        
        lowest = result.get('lowest_cost')
        if lowest:
            print(f"\nLowest Cost Option:")
            print(f"  - {lowest.get('brand')}: ${lowest.get('price', 0):.2f}")
            if lowest.get('savings'):
                print(f"  - Savings: ${lowest.get('savings'):.2f}")
        
        # Check if both SQL and vector worked
        if 'sql' in result.get('provenance', []) and 'vector' in result.get('provenance', []):
            print("\n✅ DUAL-PATH RETRIEVAL CONFIRMED")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_adp_get():
    """Test adp.get tool with both SQL and vector."""
    print("\n" + "="*60)
    print("TESTING ADP.GET (SQL + VECTOR)")
    print("="*60)
    
    request = {
        "device": {"category": "mobility", "type": "power_wheelchair"},
        "check": ["eligibility", "funding", "cep"],
        "patient_income": 19000
    }
    
    print(f"\nRequest: {json.dumps(request, indent=2)}")
    
    try:
        start = datetime.now()
        result = await adp_get(request)
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"\n✅ Response in {elapsed:.2f}s")
        print(f"Provenance: {result.get('provenance', [])}")
        print(f"Confidence: {result.get('confidence', 0):.3f}")
        
        eligibility = result.get('eligibility')
        if eligibility:
            print(f"\nEligibility:")
            print(f"  - Basic mobility need: {eligibility.get('basic_mobility')}")
            print(f"  - Ontario resident: {eligibility.get('ontario_resident')}")
        
        funding = result.get('funding')
        if funding:
            print(f"\nFunding:")
            print(f"  - ADP contribution: {funding.get('adp_contribution')}%")
            print(f"  - Client share: {funding.get('client_share_percent')}%")
        
        cep = result.get('cep')
        if cep:
            print(f"\nCEP (Low Income):")
            print(f"  - Eligible: {cep.get('eligible')}")
            print(f"  - Income threshold: ${cep.get('income_threshold'):,.0f}")
            print(f"  - Final client share: {cep.get('client_share')}%")
        
        # Check if both SQL and vector worked
        if 'sql' in result.get('provenance', []) and 'vector' in result.get('provenance', []):
            print("\n✅ DUAL-PATH RETRIEVAL CONFIRMED")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_source_passages():
    """Test source.passages tool."""
    print("\n" + "="*60)
    print("TESTING SOURCE.PASSAGES")
    print("="*60)
    
    request = {
        "chunk_ids": ["ohip_001", "odb_001"],
        "highlight_terms": ["billing", "coverage"]
    }
    
    print(f"\nRequest: {json.dumps(request, indent=2)}")
    
    try:
        start = datetime.now()
        result = await source_passages(request)
        elapsed = (datetime.now() - start).total_seconds()
        
        print(f"\n✅ Response in {elapsed:.2f}s")
        print(f"Total chunks: {result.get('total_chunks', 0)}")
        
        passages = result.get('passages', [])
        for i, passage in enumerate(passages[:2]):
            print(f"\nPassage {i+1}:")
            print(f"  - Chunk ID: {passage.get('chunk_id')}")
            print(f"  - Source: {passage.get('source')}")
            print(f"  - Text preview: {passage.get('text', '')[:100]}...")
            
            highlights = passage.get('highlights')
            if highlights:
                print(f"  - Highlights: {len(highlights)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all MCP tool tests."""
    print("\n" + "="*60)
    print("MCP TOOLS TEST - DUAL-PATH VERIFICATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    await test_schedule_get()
    await test_odb_get()
    await test_adp_get()
    await test_source_passages()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())