#!/usr/bin/env python3
"""
Test script for Dr. OFF MCP tools - Session 2B
Tests schedule.get and adp.get with realistic queries
"""
import asyncio
import json
import sys
import os
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the missing Session 2A components for testing
class ConfidenceScorer:
    def calculate(self, has_sql, vector_matches, conflicts):
        score = 0.9 if has_sql else 0.5
        score += min(vector_matches * 0.03, 0.09)
        score -= conflicts * 0.1
        return max(0.0, min(1.0, score))

class ConflictDetector:
    def detect_schedule_conflicts(self, sql_item, vector_item):
        return []

# Create mock utils module
import types
utils = types.ModuleType('utils')
utils.ConfidenceScorer = ConfidenceScorer
utils.ConflictDetector = ConflictDetector
sys.modules['src.agents.ontario_orchestrator.mcp.utils'] = utils

# Now import our tools
from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get

async def test_schedule_tool():
    """Test schedule.get tool with various queries."""
    print("\n" + "="*60)
    print("TESTING SCHEDULE.GET TOOL")
    print("="*60)
    
    test_cases = [
        {
            "name": "Test 1: C124 MRP Discharge Billing",
            "request": {
                "q": "MRP billing day of discharge after 72hr admission",
                "codes": ["C124"],
                "include": ["codes", "fee", "limits", "documentation"],
                "top_k": 5
            }
        },
        {
            "name": "Test 2: Search for discharge codes",
            "request": {
                "q": "discharge",
                "include": ["codes", "fee"],
                "top_k": 3
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 40)
        try:
            start = datetime.now()
            result = await schedule_get(test["request"])
            elapsed = (datetime.now() - start).total_seconds()
            
            print(f"✓ Response received in {elapsed:.2f}s")
            print(f"  Provenance: {result.get('provenance', [])}")
            print(f"  Confidence: {result.get('confidence', 0):.2f}")
            print(f"  Items found: {len(result.get('items', []))}")
            
            if result.get('items'):
                for item in result['items'][:2]:  # Show first 2
                    print(f"    - {item.get('code')}: {item.get('description', 'N/A')[:50]}...")
                    if item.get('fee'):
                        print(f"      Fee: ${item.get('fee'):.2f}")
                        
            print(f"  Citations: {len(result.get('citations', []))}")
            
        except Exception as e:
            print(f"✗ Error: {e}")

async def test_adp_tool():
    """Test adp.get tool with various queries."""
    print("\n" + "="*60)
    print("TESTING ADP.GET TOOL")
    print("="*60)
    
    test_cases = [
        {
            "name": "Test 1: Walker for Elderly",
            "request": {
                "device": {"category": "mobility", "type": "walker"},
                "check": ["eligibility", "funding"],
                "use_case": {"age": 85, "mobility_limited": True}
            }
        },
        {
            "name": "Test 2: Power Wheelchair with CEP Check",
            "request": {
                "device": {"category": "mobility", "type": "power_wheelchair"},
                "check": ["eligibility", "funding", "cep"],
                "patient_income": 19000
            }
        },
        {
            "name": "Test 3: Scooter Batteries (Exclusion)",
            "request": {
                "device": {"category": "mobility", "type": "scooter_batteries"},
                "check": ["exclusions"]
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 40)
        try:
            start = datetime.now()
            result = await adp_get(test["request"])
            elapsed = (datetime.now() - start).total_seconds()
            
            print(f"✓ Response received in {elapsed:.2f}s")
            print(f"  Provenance: {result.get('provenance', [])}")
            print(f"  Confidence: {result.get('confidence', 0):.2f}")
            
            if result.get('eligibility'):
                elig = result['eligibility']
                print(f"  Eligibility:")
                print(f"    - Basic mobility: {elig.get('basic_mobility')}")
                print(f"    - Ontario resident: {elig.get('ontario_resident')}")
                
            if result.get('funding'):
                fund = result['funding']
                print(f"  Funding:")
                print(f"    - ADP: {fund.get('adp_contribution')}%")
                print(f"    - Client: {fund.get('client_share_percent')}%")
                
            if result.get('cep'):
                cep = result['cep']
                print(f"  CEP:")
                print(f"    - Eligible: {cep.get('eligible')}")
                print(f"    - Threshold: ${cep.get('income_threshold'):,.0f}")
                print(f"    - Client share: {cep.get('client_share')}%")
                
            if result.get('exclusions'):
                print(f"  Exclusions: {', '.join(result['exclusions'][:3])}")
                
            print(f"  Citations: {len(result.get('citations', []))}")
            
        except Exception as e:
            print(f"✗ Error: {e}")

async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Dr. OFF MCP TOOLS TEST SUITE")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Test database connectivity
    print("\n📊 Database Check:")
    print("-" * 40)
    
    import sqlite3
    try:
        # Check OHIP database
        conn = sqlite3.connect("data/processed/dr_off/dr_off.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ohip_fee_schedule")
        count = cursor.fetchone()[0]
        print(f"✓ OHIP fee codes: {count}")
        conn.close()
        
        # Check ADP database
        conn = sqlite3.connect("data/ohip.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM adp_funding_rule")
        funding_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM adp_exclusion")
        exclusion_count = cursor.fetchone()[0]
        print(f"✓ ADP funding rules: {funding_count}")
        print(f"✓ ADP exclusions: {exclusion_count}")
        conn.close()
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        return
    
    # Check Chroma
    print("\n🔍 Vector Store Check:")
    print("-" * 40)
    try:
        import chromadb
        client = chromadb.PersistentClient(path=".chroma")
        collections = client.list_collections()
        for col in collections:
            try:
                count = client.get_collection(col.name).count()
                print(f"✓ {col.name}: {count} embeddings")
            except:
                print(f"✗ {col.name}: Could not access")
    except Exception as e:
        print(f"⚠️  Chroma not available: {e}")
        print("   (Vector search will fail but SQL will continue)")
    
    # Run tool tests
    await test_schedule_tool()
    await test_adp_tool()
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())