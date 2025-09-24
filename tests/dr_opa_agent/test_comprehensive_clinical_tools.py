#!/usr/bin/env python3
"""Comprehensive test of CEP clinical tools MCP functionality."""

import sys
import asyncio
import json
import sqlite3
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the actual handler function
from src.agents.dr_opa_agent.mcp.server import clinical_tools_handler


async def test_comprehensive_clinical_tools():
    """Comprehensive test of clinical tools MCP functionality."""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE CEP CLINICAL TOOLS MCP TEST")
    print("="*80 + "\n")
    
    # Test 1: Get all tools overview
    print("Test 1: Get all CEP tools overview")
    print("-" * 50)
    result = await clinical_tools_handler()
    print(f"Total tools found: {result['total_tools']}")
    
    # Group by category
    categories = {}
    for tool in result['tools']:
        cat = tool.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool['name'])
    
    print("\nTools by category:")
    for cat, tools in sorted(categories.items()):
        print(f"  {cat}: {len(tools)} tools")
        for tool in sorted(tools)[:3]:  # Show first 3 of each category
            print(f"    - {tool}")
        if len(tools) > 3:
            print(f"    ... and {len(tools) - 3} more")
    
    # Test 2: Search by specific conditions
    print("\n\nTest 2: Search by medical conditions")
    print("-" * 50)
    
    conditions_to_test = [
        "dementia", 
        "diabetes", 
        "pain", 
        "depression", 
        "opioid", 
        "heart failure",
        "obesity"
    ]
    
    for condition in conditions_to_test:
        result = await clinical_tools_handler(condition=condition)
        print(f"'{condition}': {result['total_tools']} tools found")
        for tool in result['tools'][:2]:  # Show first 2 results
            print(f"  - {tool['name']}")
    
    # Test 3: Search by categories
    print("\n\nTest 3: Search by categories")
    print("-" * 50)
    
    # First get a tool to see what categories are available
    result = await clinical_tools_handler()
    available_categories = set()
    for tool in result['tools']:
        # Check metadata for category info
        if 'metadata' in tool and 'category' in tool['metadata']:
            available_categories.add(tool['metadata']['category'])
    
    print(f"Available categories: {sorted(available_categories)}")
    
    # Test mental health category specifically
    result = await clinical_tools_handler(category="mental_health")
    print(f"\nMental health tools: {result['total_tools']} found")
    for tool in result['tools'][:3]:
        print(f"  - {tool['name']}")
    
    # Test 4: Search by feature types
    print("\n\nTest 4: Search by feature types")
    print("-" * 50)
    
    feature_types = ["algorithm", "checklist", "forms", "assessment"]
    
    for feature in feature_types:
        result = await clinical_tools_handler(feature_type=feature)
        print(f"Tools with '{feature}': {result['total_tools']} found")
        for tool in result['tools'][:2]:
            print(f"  - {tool['name']}")
            if 'key_features' in tool:
                features = [k for k, v in tool['key_features'].items() if v and feature in k]
                if features:
                    print(f"    Features: {', '.join(features)}")
    
    # Test 5: Search for specific tool with sections
    print("\n\nTest 5: Get specific tool with sections")
    print("-" * 50)
    
    result = await clinical_tools_handler(
        tool_name="dementia", 
        include_sections=True
    )
    
    if result['tools']:
        tool = result['tools'][0]
        print(f"Tool: {tool['name']}")
        print(f"URL: {tool['url']}")
        print(f"Category: {tool.get('category', 'N/A')}")
        
        if 'key_features' in tool:
            active_features = [k for k, v in tool['key_features'].items() if v]
            print(f"Features: {', '.join(active_features)}")
        
        if tool.get('sections'):
            print(f"\nSections ({len(tool['sections'])}):")
            for i, section in enumerate(tool['sections'][:5], 1):
                print(f"  {i}. {section.get('title', 'Untitled')}")
                if section.get('summary'):
                    print(f"     Summary: {section['summary'][:80]}...")
            if len(tool['sections']) > 5:
                print(f"     ... and {len(tool['sections']) - 5} more sections")
    
    # Test 6: Complex searches
    print("\n\nTest 6: Complex search scenarios")
    print("-" * 50)
    
    # Search for substance use tools
    result = await clinical_tools_handler(condition="substance use")
    print(f"Substance use tools: {result['total_tools']} found")
    
    # Search for women's health
    result = await clinical_tools_handler(condition="women")
    print(f"Women's health tools: {result['total_tools']} found")
    
    # Search for chronic disease management
    result = await clinical_tools_handler(condition="chronic")
    print(f"Chronic disease tools: {result['total_tools']} found")
    
    # Test 7: Database verification
    print("\n\nTest 7: Database verification")
    print("-" * 50)
    
    # Check database directly
    db_path = "data/processed/dr_opa/opa.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get total counts
    cursor.execute("SELECT COUNT(*) FROM opa_documents WHERE source_org='cep'")
    doc_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM opa_sections WHERE document_id IN (SELECT document_id FROM opa_documents WHERE source_org='cep')")
    section_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM opa_sections WHERE embedding_id IS NOT NULL AND document_id IN (SELECT document_id FROM opa_documents WHERE source_org='cep')")
    embedding_count = cursor.fetchone()[0]
    
    print(f"Database verification:")
    print(f"  Documents in DB: {doc_count}")
    print(f"  Sections in DB: {section_count}")
    print(f"  Sections with embeddings: {embedding_count}")
    print(f"  Embedding coverage: {embedding_count/section_count*100:.1f}%")
    
    # Check for variety in document types
    cursor.execute("""
        SELECT DISTINCT document_type, COUNT(*) 
        FROM opa_documents 
        WHERE source_org='cep' 
        GROUP BY document_type
    """)
    doc_types = cursor.fetchall()
    
    print(f"  Document types:")
    for doc_type, count in doc_types:
        print(f"    {doc_type}: {count}")
    
    conn.close()
    
    # Test 8: Performance test
    print("\n\nTest 8: Performance test")
    print("-" * 50)
    
    import time
    
    # Time multiple searches
    search_queries = [
        ("diabetes", None, None),
        ("mental health", None, None),
        (None, "pain", None),
        (None, None, "algorithm")
    ]
    
    total_time = 0
    for i, (condition, category, feature) in enumerate(search_queries, 1):
        start_time = time.time()
        result = await clinical_tools_handler(
            condition=condition,
            category=category, 
            feature_type=feature
        )
        elapsed = time.time() - start_time
        total_time += elapsed
        
        query_desc = condition or category or feature
        print(f"  Query {i} ('{query_desc}'): {elapsed:.3f}s - {result['total_tools']} results")
    
    print(f"  Average query time: {total_time/len(search_queries):.3f}s")
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED SUCCESSFULLY! ✅")
    print("="*80 + "\n")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_clinical_tools())
    sys.exit(0 if success else 1)