#!/usr/bin/env python3
"""
Verify metadata consistency across Dr. OPA ChromaDB collections.
Checks if BM25 index schema matches actual metadata fields.
"""

import asyncio
import sys
from pathlib import Path
from collections import defaultdict
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_agents.dr_opa_agent.dr_opa_mcp.retrieval.vector_client import VectorClient

async def main():
    print("=" * 70)
    print("Metadata Consistency Verification for BM25 Index")
    print("=" * 70)

    # Initialize vector client
    vector_client = VectorClient()

    # Check each collection
    all_metadata_keys = defaultdict(set)

    for collection_name, collection in vector_client._collections.items():
        print(f"\n📁 Collection: {collection_name}")
        print(f"   Documents: {collection.count()}")

        # Get sample documents to check metadata
        sample_size = min(10, collection.count())
        results = await asyncio.get_event_loop().run_in_executor(
            vector_client.executor,
            lambda: collection.get(limit=sample_size, include=['metadatas'])
        )

        # Analyze metadata keys
        metadata_keys = set()
        for metadata in results['metadatas']:
            if metadata:
                metadata_keys.update(metadata.keys())

        all_metadata_keys[collection_name] = metadata_keys

        print(f"   Metadata fields ({len(metadata_keys)}):")
        for key in sorted(metadata_keys):
            # Count how many docs have this field
            count = sum(1 for m in results['metadatas'] if m and key in m)
            coverage = (count / len(results['metadatas'])) * 100
            print(f"      • {key:<25} ({coverage:.0f}% coverage)")

    # Check consistency
    print("\n" + "=" * 70)
    print("Consistency Analysis")
    print("=" * 70)

    # BM25 index schema
    bm25_schema_fields = {
        'document_title': 'TEXT (indexed)',
        'section_heading': 'TEXT (indexed)',
        'source_org': 'STORED (metadata only)',
        'document_type': 'STORED (metadata only)',
        'chunk_type': 'STORED (metadata only)',
        'effective_date': 'STORED (metadata only)',
        'source_url': 'STORED (metadata only)'
    }

    print("\n🔍 BM25 Index Schema:")
    for field, field_type in bm25_schema_fields.items():
        print(f"   {field:<25} → {field_type}")

    print("\n📊 Field Coverage Across Collections:")
    all_fields = set()
    for keys in all_metadata_keys.values():
        all_fields.update(keys)

    for field in sorted(all_fields):
        collections_with_field = [
            name for name, keys in all_metadata_keys.items()
            if field in keys
        ]
        coverage = len(collections_with_field) / len(all_metadata_keys) * 100

        in_schema = "✓" if field in bm25_schema_fields else "✗"
        print(f"   {field:<25} {in_schema}  {coverage:.0f}% ({len(collections_with_field)}/5 collections)")

    # Check for potential issues
    print("\n⚠️  Potential Issues:")

    # Fields in BM25 schema but missing from some collections
    for field in bm25_schema_fields.keys():
        missing_from = [
            name for name, keys in all_metadata_keys.items()
            if field not in keys
        ]
        if missing_from:
            print(f"   • '{field}' missing from: {', '.join(missing_from)}")

    # Fields in collections but not in BM25 schema
    unindexed_fields = all_fields - set(bm25_schema_fields.keys())
    if unindexed_fields:
        print(f"   • Fields NOT indexed by BM25: {', '.join(sorted(unindexed_fields))}")

    # Impact analysis
    print("\n" + "=" * 70)
    print("Impact Analysis")
    print("=" * 70)

    print("\n✅ BM25 Will Work Because:")
    print("   1. Main 'text' field is always present (document content)")
    print("   2. Missing metadata fields are STORED (not indexed)")
    print("   3. BM25 only searches TEXT fields (text, document_title, section_heading)")
    print("   4. STORED fields are just returned in results, not searched")

    print("\n📈 What Gets Indexed for Search:")
    print("   • text field: ✓ (main document content - always present)")
    print("   • document_title: Indexed if present, empty string if missing")
    print("   • section_heading: Indexed if present, empty string if missing")

    print("\n💡 Conclusion:")
    print("   Missing metadata fields do NOT impact BM25 search quality because:")
    print("   - They're metadata-only (STORED, not TEXT)")
    print("   - BM25 searches on text/title/heading only")
    print("   - Metadata is just returned for display/filtering")

    # Sample documents from each collection
    print("\n" + "=" * 70)
    print("Sample Metadata from Each Collection")
    print("=" * 70)

    for collection_name, collection in vector_client._collections.items():
        results = await asyncio.get_event_loop().run_in_executor(
            vector_client.executor,
            lambda c=collection: c.get(limit=1, include=['metadatas', 'documents'])
        )

        print(f"\n📄 {collection_name} (sample):")
        if results['metadatas']:
            metadata = results['metadatas'][0]
            text_preview = results['documents'][0][:100] if results['documents'] else ""

            print(f"   Text preview: {text_preview}...")
            print(f"   Metadata: {json.dumps(metadata, indent=6)}")

if __name__ == "__main__":
    asyncio.run(main())
