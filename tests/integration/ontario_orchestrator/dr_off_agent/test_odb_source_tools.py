#!/usr/bin/env python3
"""
Test ODB and Source tools for Session 2C
Tests with mock vector client to avoid Chroma conflicts
"""
import asyncio
import json
from datetime import datetime
import sys
import os

# Add project to path
sys.path.insert(0, os.getcwd())

# Create mock components for testing
class MockVectorClient:
    """Mock vector client to avoid Chroma conflicts during testing."""
    
    async def search_odb(self, query, drug_class=None, n_results=5):
        """Mock ODB vector search results."""
        return [
            {
                'text': 'Metformin is covered under the ODB formulary for Type 2 diabetes. Limited use criteria may apply for certain formulations.',
                'metadata': {'source': 'odb_formulary', 'page': 123, 'section': 'Diabetes Medications'},
                'distance': 0.1
            },
            {
                'text': 'Generic metformin is available as an interchangeable product. Must try metformin before other diabetes medications.',
                'metadata': {'source': 'odb_policy', 'page': 45},
                'distance': 0.2
            }
        ]
    
    async def get_passages_by_ids(self, chunk_ids, collection='ohip_chunks'):
        """Mock passage retrieval."""
        return [
            {
                'id': chunk_ids[0] if chunk_ids else 'test_001',
                'text': 'This is a test passage about billing codes and requirements.',
                'metadata': {'source': 'test_doc', 'page': 1},
                'collection': collection
            }
        ]

class MockSQLClient:
    """Mock SQL client for testing."""
    
    async def query_odb_drugs(self, din=None, ingredient=None, interchangeable_group=None, 
                              lowest_cost_only=False, limit=20):
        """Mock ODB drug query results."""
        if ingredient and 'metformin' in ingredient.lower():
            return [
                {
                    'din': '02229145',
                    'ingredient': 'metformin',
                    'brand': 'Glucophage',
                    'strength': '500mg',
                    'form': 'tablet',
                    'price': 15.50,
                    'lowest_cost': False,
                    'group_id': 'IG_001'
                },
                {
                    'din': '02245788',
                    'ingredient': 'metformin',
                    'brand': 'Apo-Metformin',
                    'strength': '500mg',
                    'form': 'tablet',
                    'price': 8.25,
                    'lowest_cost': True,
                    'group_id': 'IG_001'
                },
                {
                    'din': '02246789',
                    'ingredient': 'metformin',
                    'brand': 'Teva-Metformin',
                    'strength': '500mg',
                    'form': 'tablet',
                    'price': 9.00,
                    'lowest_cost': False,
                    'group_id': 'IG_001'
                }
            ]
        elif ingredient and 'sitagliptin' in ingredient.lower():
            return [
                {
                    'din': '02340001',
                    'ingredient': 'sitagliptin',
                    'brand': 'Januvia',
                    'strength': '100mg',
                    'form': 'tablet',
                    'price': 85.00,
                    'lowest_cost': False,
                    'group_id': 'IG_002'
                },
                {
                    'din': '02340002',
                    'ingredient': 'sitagliptin',
                    'brand': 'Sitagliptin-Generic',
                    'strength': '100mg',
                    'form': 'tablet',
                    'price': 45.00,
                    'lowest_cost': True,
                    'group_id': 'IG_002'
                }
            ]
        return []

# Mock the utils module
class ConfidenceScorer:
    def calculate(self, has_sql, vector_matches, conflicts):
        score = 0.9 if has_sql else 0.5
        score += min(vector_matches * 0.03, 0.09)
        score -= conflicts * 0.1
        return max(0.0, min(1.0, score))

class ConflictDetector:
    def detect_schedule_conflicts(self, sql_item, vector_item):
        return []

import types
utils = types.ModuleType('utils')
utils.ConfidenceScorer = ConfidenceScorer
utils.ConflictDetector = ConflictDetector
sys.modules['src.agents.ontario_orchestrator.mcp.utils'] = utils

# Now import tools
from src.agents.ontario_orchestrator.mcp.tools.odb import odb_get
from src.agents.ontario_orchestrator.mcp.tools.source import source_passages

async def test_odb_tool():
    """Test ODB tool with various scenarios."""
    print("\n" + "="*60)
    print("TESTING ODB.GET TOOL")
    print("="*60)
    
    test_cases = [
        {
            "name": "Test 1: Metformin Coverage and Alternatives",
            "request": {
                "q": "metformin coverage and cheaper alternatives",
                "drug": "metformin",
                "check": ["coverage", "interchangeable", "lowest_cost"],
                "top_k": 5
            }
        },
        {
            "name": "Test 2: Sitagliptin Generic vs Brand Pricing",
            "request": {
                "q": "Januvia vs sitagliptin generic pricing",
                "ingredient": "sitagliptin",
                "check": ["interchangeable_group", "price_comparison"],
                "include_brand": True
            }
        },
        {
            "name": "Test 3: Non-existent Drug",
            "request": {
                "q": "XYZ123 coverage",
                "drug": "XYZ123",
                "check": ["coverage"]
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 40)
        
        try:
            # Use mock clients
            sql_client = MockSQLClient()
            vector_client = MockVectorClient()
            
            start = datetime.now()
            result = await odb_get(test["request"], sql_client=sql_client, vector_client=vector_client)
            elapsed = (datetime.now() - start).total_seconds()
            
            print(f"✅ Response in {elapsed:.2f}s")
            print(f"  Provenance: {result.get('provenance', [])}")
            print(f"  Confidence: {result.get('confidence', 0):.3f}")
            
            # Coverage
            coverage = result.get('coverage')
            if coverage:
                print(f"  Coverage:")
                print(f"    - Covered: {coverage.get('covered')}")
                print(f"    - DIN: {coverage.get('din')}")
                print(f"    - Brand: {coverage.get('brand_name')}")
                print(f"    - Generic: {coverage.get('generic_name')}")
                print(f"    - LU Required: {coverage.get('lu_required')}")
            
            # Interchangeable
            interchangeable = result.get('interchangeable', [])
            if interchangeable:
                print(f"  Interchangeable drugs: {len(interchangeable)}")
                for drug in interchangeable[:3]:
                    print(f"    - {drug.get('brand')}: ${drug.get('price'):.2f}", end="")
                    if drug.get('lowest_cost'):
                        print(" ⭐ LOWEST")
                    else:
                        print()
            
            # Lowest cost
            lowest = result.get('lowest_cost')
            if lowest:
                print(f"  Lowest Cost:")
                print(f"    - {lowest.get('brand')}: ${lowest.get('price'):.2f}")
                print(f"    - Savings: ${lowest.get('savings'):.2f}")
            
            # Citations
            citations = result.get('citations', [])
            if citations:
                print(f"  Citations: {len(citations)} sources")
                for cite in citations[:2]:
                    print(f"    - {cite.get('source')} @ page {cite.get('page')}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

async def test_source_tool():
    """Test Source Passages tool."""
    print("\n" + "="*60)
    print("TESTING SOURCE.PASSAGES TOOL")
    print("="*60)
    
    test_cases = [
        {
            "name": "Test 1: Retrieve Test Chunks",
            "request": {
                "chunk_ids": ["test_001", "test_002"],
                "highlight_terms": ["billing", "coverage"]
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 40)
        
        try:
            # Use mock vector client
            vector_client = MockVectorClient()
            
            start = datetime.now()
            result = await source_passages(test["request"], vector_client=vector_client)
            elapsed = (datetime.now() - start).total_seconds()
            
            print(f"✅ Response in {elapsed:.2f}s")
            print(f"  Total chunks: {result.get('total_chunks', 0)}")
            
            passages = result.get('passages', [])
            for i, passage in enumerate(passages):
                print(f"  Passage {i+1}:")
                print(f"    - ID: {passage.get('chunk_id')}")
                print(f"    - Source: {passage.get('source')}")
                print(f"    - Text preview: {passage.get('text', '')[:80]}...")
                
                highlights = passage.get('highlights')
                if highlights:
                    print(f"    - Highlights: {len(highlights)}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Dr. OFF MCP TOOLS TEST - SESSION 2C")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Using MOCK clients to avoid Chroma conflicts")
    print("="*60)
    
    await test_odb_tool()
    await test_source_tool()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())