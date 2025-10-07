"""Validate chunk quality after re-ingestion.

Usage:
    python scripts/validate_chunks.py --collection opa_cep_corpus
"""

import argparse
import chromadb
from collections import Counter
import json


def validate_chunks(collection_name: str, chroma_path: str = "data/dr_opa_agent/chroma"):
    """Validate chunk quality metrics.

    Args:
        collection_name: Name of collection to validate
        chroma_path: Path to ChromaDB directory
    """
    print(f"\n=== Validating Collection: {collection_name} ===\n")

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection(collection_name)

    # Get all chunks
    results = collection.get(
        include=["documents", "metadatas"]
    )

    chunk_count = len(results['ids'])
    print(f"Total chunks: {chunk_count}")

    # Analyze word counts
    word_counts = [len(doc.split()) for doc in results['documents']]
    print(f"\nWord Count Statistics:")
    print(f"  Min: {min(word_counts)}")
    print(f"  Max: {max(word_counts)}")
    print(f"  Average: {sum(word_counts)/len(word_counts):.0f}")
    print(f"  Median: {sorted(word_counts)[len(word_counts)//2]}")

    # Distribution
    bins = [0, 50, 100, 150, 200, 300, 500, 800, 1000, float('inf')]
    bin_labels = ['0-50', '50-100', '100-150', '150-200', '200-300', '300-500', '500-800', '800-1000', '1000+']
    distribution = Counter()

    for wc in word_counts:
        for i, (low, high) in enumerate(zip(bins[:-1], bins[1:])):
            if low <= wc < high:
                distribution[bin_labels[i]] += 1
                break

    print(f"\nWord Count Distribution:")
    for label in bin_labels:
        count = distribution[label]
        pct = (count / chunk_count) * 100
        bar = '█' * int(pct / 2)
        print(f"  {label:12s}: {count:4d} ({pct:5.1f}%) {bar}")

    # Analyze chunk types
    if results['metadatas']:
        chunk_types = Counter(m.get('chunk_type', 'unknown') for m in results['metadatas'])
        print(f"\nChunk Types:")
        for ctype, count in chunk_types.items():
            print(f"  {ctype}: {count}")

        # Analyze metadata fields
        metadata_fields = set()
        for m in results['metadatas']:
            metadata_fields.update(m.keys())

        print(f"\nMetadata Fields ({len(metadata_fields)}):")
        for field in sorted(metadata_fields):
            # Count non-empty values
            non_empty = sum(1 for m in results['metadatas'] if m.get(field))
            pct = (non_empty / chunk_count) * 100
            print(f"  {field:30s}: {pct:5.1f}% populated")

    # Sample chunks
    print(f"\n=== Sample Chunks ===\n")

    for i in [0, len(results['ids'])//2, -1]:
        print(f"Chunk {i} ({results['ids'][i]}):")
        print(f"  Words: {len(results['documents'][i].split())}")
        print(f"  Type: {results['metadatas'][i].get('chunk_type', 'unknown')}")
        print(f"  Section: {results['metadatas'][i].get('section_title', 'N/A')}")
        print(f"  Text preview: {results['documents'][i][:150]}...")
        print()

    # Quality checks
    print(f"=== Quality Checks ===\n")

    issues = []

    # Check for very small chunks
    too_small = sum(1 for wc in word_counts if wc < 50)
    if too_small > 0:
        pct = (too_small / chunk_count) * 100
        issues.append(f"⚠️  {too_small} chunks ({pct:.1f}%) are < 50 words")

    # Check for missing metadata
    required_fields = ['chunk_type', 'source_org', 'document_type']
    for field in required_fields:
        missing = sum(1 for m in results['metadatas'] if not m.get(field))
        if missing > 0:
            pct = (missing / chunk_count) * 100
            issues.append(f"⚠️  {missing} chunks ({pct:.1f}%) missing '{field}'")

    # Check parent/child relationships
    if results['metadatas']:
        parents = [m for m in results['metadatas'] if m.get('chunk_type') == 'parent']
        children = [m for m in results['metadatas'] if m.get('chunk_type') == 'child']

        if children:
            orphans = sum(1 for c in children if not c.get('parent_id'))
            if orphans > 0:
                issues.append(f"⚠️  {orphans} child chunks missing parent_id")

    if issues:
        print("Issues Found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✓ No issues found!")

    print("\n" + "="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Validate chunk quality")
    parser.add_argument('--collection', required=True, help='Collection name to validate')
    parser.add_argument('--chroma-path', default='data/dr_opa_agent/chroma', help='Path to ChromaDB')

    args = parser.parse_args()

    validate_chunks(args.collection, args.chroma_path)


if __name__ == "__main__":
    main()
