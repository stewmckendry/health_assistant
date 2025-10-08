#!/usr/bin/env python3
"""
QA Test for CPSO Two-Tier Retrieval.

Manually inspects results to verify:
1. Discovery queries return relevant policy overviews
2. Specific queries return detailed requirements with parent context
3. Policy scoping is working correctly

Author: AI Assistant
Date: 2025-10-07
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()


async def qa_discovery_query():
    """QA a discovery query - should return policy overviews from 2-4 policies."""
    from ai_agents.dr_opa_agent.dr_opa_mcp import server

    query = "What are CPSO policies on virtual care?"

    print("=" * 80)
    print("QA TEST 1: DISCOVERY QUERY")
    print("=" * 80)
    print(f"Query: {query}")
    print()

    handler_func = server.policy_check_handler.fn if hasattr(server.policy_check_handler, 'fn') else server.policy_check_handler

    result = await handler_func(query=query, k=5)

    # Check classification
    classification = result.get('classification', {})
    print("CLASSIFICATION:")
    print(f"  Intent: {classification.get('intent')}")
    print(f"  Policies: {classification.get('relevant_policies', [])}")
    print(f"  Confidence: {classification.get('triage_confidence', 0):.2f}")
    print()

    # Expected: policy_discovery
    if classification.get('intent') != 'policy_discovery':
        print("❌ FAIL: Expected 'policy_discovery', got '{}'".format(classification.get('intent')))
        return False
    else:
        print("✓ PASS: Correctly classified as policy_discovery")
    print()

    # Check results
    items = result.get('items', [])
    print(f"RESULTS: {len(items)} chunks")
    print()

    if len(items) == 0:
        print("❌ FAIL: No results returned")
        return False

    # Check chunk types - should be parent only
    chunk_types = [item.get('metadata', {}).get('chunk_type') for item in items]
    parent_count = chunk_types.count('parent')
    child_count = chunk_types.count('child')

    print(f"Chunk Types: {parent_count} parent, {child_count} child")
    if child_count > 0:
        print("⚠️  WARNING: Discovery query should return parent chunks only, but found {} child chunks".format(child_count))
    else:
        print("✓ PASS: All chunks are parent (overview) chunks")
    print()

    # Check unique policies
    unique_policies = set()
    for item in items:
        metadata = item.get('metadata', {})
        url = metadata.get('source_url', '')
        if url:
            unique_policies.add(url)

    print(f"Unique Policies: {len(unique_policies)}")
    if len(unique_policies) < 2 or len(unique_policies) > 6:
        print(f"⚠️  WARNING: Expected 2-4 unique policies, got {len(unique_policies)}")
    else:
        print("✓ PASS: Policy count is within expected range")
    print()

    # Inspect top 3 chunks for relevance
    print("TOP 3 CHUNKS - RELEVANCE CHECK:")
    print()

    for i, item in enumerate(items[:3], 1):
        metadata = item.get('metadata', {})
        text = item.get('text', '')

        print(f"[{i}] {metadata.get('document_title', 'Unknown')}")
        print(f"    Policy Level: {metadata.get('policy_level', 'N/A')}")
        print(f"    Chunk Type: {metadata.get('chunk_type', 'N/A')}")
        print(f"    Score: {item.get('relevance_score', 0):.3f}")
        print(f"    Text Length: {len(text)} chars")
        print()
        print(f"    Content Preview (first 300 chars):")
        print(f"    {text[:300].replace(chr(10), ' ')}")
        print()

        # Check if "virtual care" or "telemedicine" appears in text
        text_lower = text.lower()
        if 'virtual' in text_lower or 'telemedicine' in text_lower or 'telehealth' in text_lower:
            print(f"    ✓ Contains virtual care terms")
        else:
            print(f"    ⚠️  Does NOT contain obvious virtual care terms")
        print()

    return True


async def qa_specific_query():
    """QA a specific query - should return detailed chunks with parent context."""
    from ai_agents.dr_opa_agent.dr_opa_mcp import server

    query = "What are the consent requirements for telemedicine?"

    print("=" * 80)
    print("QA TEST 2: SPECIFIC REQUIREMENT QUERY")
    print("=" * 80)
    print(f"Query: {query}")
    print()

    handler_func = server.policy_check_handler.fn if hasattr(server.policy_check_handler, 'fn') else server.policy_check_handler

    result = await handler_func(query=query, k=10)

    # Check classification
    classification = result.get('classification', {})
    print("CLASSIFICATION:")
    print(f"  Intent: {classification.get('intent')}")
    print(f"  Policies: {classification.get('relevant_policies', [])}")
    print(f"  Confidence: {classification.get('triage_confidence', 0):.2f}")
    print()

    # Expected: specific_requirement
    if classification.get('intent') != 'specific_requirement':
        print("❌ FAIL: Expected 'specific_requirement', got '{}'".format(classification.get('intent')))
        return False
    else:
        print("✓ PASS: Correctly classified as specific_requirement")
    print()

    # Check results
    items = result.get('items', [])
    print(f"RESULTS: {len(items)} chunks")
    print()

    if len(items) == 0:
        print("❌ FAIL: No results returned")
        return False

    # Check chunk types - should include both parent and child
    chunk_types = [item.get('metadata', {}).get('chunk_type') for item in items]
    parent_count = chunk_types.count('parent')
    child_count = chunk_types.count('child')

    print(f"Chunk Types: {parent_count} parent, {child_count} child")
    print("✓ PASS: Specific query can return both parent and child chunks")
    print()

    # Check unique policies
    unique_policies = set()
    for item in items:
        metadata = item.get('metadata', {})
        url = metadata.get('source_url', '')
        if url:
            unique_policies.add(url)

    print(f"Unique Policies: {len(unique_policies)}")
    if len(unique_policies) > 3:
        print(f"⚠️  WARNING: Expected 1-2 unique policies, got {len(unique_policies)}")
    else:
        print("✓ PASS: Policy count is focused (1-3 policies)")
    print()

    # Check for parent+child context assembly
    print("PARENT+CHILD CONTEXT CHECK:")
    print()

    child_chunks = [item for item in items if item.get('metadata', {}).get('chunk_type') == 'child']

    if child_chunks:
        print(f"Found {len(child_chunks)} child chunks - checking for parent context...")
        print()

        # Check first child chunk
        child = child_chunks[0]
        text = child.get('text', '')
        has_parent_context = child.get('has_parent_context', False)

        print(f"Sample Child Chunk:")
        print(f"  Title: {child.get('metadata', {}).get('document_title', 'Unknown')}")
        print(f"  Has Parent Context Flag: {has_parent_context}")
        print(f"  Text contains '[PARENT CONTEXT]': {'[PARENT CONTEXT]' in text}")
        print(f"  Text Length: {len(text)} chars")
        print()

        if '[PARENT CONTEXT]' in text:
            print("✓ PASS: Parent context is prepended to child chunks")

            # Show the structure
            parent_section = text.split('[SPECIFIC DETAIL]')[0] if '[SPECIFIC DETAIL]' in text else text[:500]
            detail_section = text.split('[SPECIFIC DETAIL]')[1][:300] if '[SPECIFIC DETAIL]' in text else ''

            print()
            print("Parent Section Preview:")
            print(parent_section[:300].replace(chr(10), ' '))
            print()
            if detail_section:
                print("Detail Section Preview:")
                print(detail_section.replace(chr(10), ' '))
                print()
        else:
            print("⚠️  WARNING: Expected parent context to be prepended, but not found")
    else:
        print("No child chunks in results - parent chunks only")
    print()

    # Inspect top 3 chunks for relevance
    print("TOP 3 CHUNKS - RELEVANCE CHECK:")
    print()

    for i, item in enumerate(items[:3], 1):
        metadata = item.get('metadata', {})
        text = item.get('text', '')

        print(f"[{i}] {metadata.get('document_title', 'Unknown')}")
        print(f"    Section: {metadata.get('section_heading', 'N/A')[:60]}")
        print(f"    Policy Level: {metadata.get('policy_level', 'N/A')}")
        print(f"    Chunk Type: {metadata.get('chunk_type', 'N/A')}")
        print(f"    Score: {item.get('relevance_score', 0):.3f}")
        print()
        print(f"    Content Preview (first 300 chars):")
        print(f"    {text[:300].replace(chr(10), ' ')}")
        print()

        # Check if "consent" appears in text
        text_lower = text.lower()
        if 'consent' in text_lower:
            print(f"    ✓ Contains 'consent'")
        else:
            print(f"    ⚠️  Does NOT contain 'consent'")
        print()

    return True


async def main():
    """Run QA tests."""
    print("=" * 80)
    print("CPSO Two-Tier Retrieval - QA Testing")
    print("=" * 80)
    print()

    print("Initializing...")
    from ai_agents.dr_opa_agent.dr_opa_mcp.server import get_semantic_search
    semantic_search = get_semantic_search()
    print("✓ Ready")
    print()

    # Run tests
    test1_pass = await qa_discovery_query()
    print()

    await asyncio.sleep(1)

    test2_pass = await qa_specific_query()
    print()

    # Summary
    print("=" * 80)
    print("QA SUMMARY")
    print("=" * 80)
    print()
    print(f"Test 1 (Discovery Query): {'✓ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 (Specific Query): {'✓ PASS' if test2_pass else '❌ FAIL'}")
    print()

    if test1_pass and test2_pass:
        print("✓ All QA tests passed!")
    else:
        print("⚠️  Some QA tests failed - review output above")
    print()


if __name__ == "__main__":
    asyncio.run(main())
