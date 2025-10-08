"""Restructure Quality Standards corpus - add section_path and extract condition."""

import chromadb
from datetime import datetime
from pathlib import Path
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def restructure_quality_standards():
    """Add missing metadata (section_path, condition) to Quality Standards."""

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")

    # Get current collection
    collection = client.get_collection("opa_quality_standards_corpus")

    print(f"=== Restructuring Quality Standards Corpus ===")
    print(f"Current chunks: {collection.count()}")

    # Get all chunks
    results = collection.get(include=['metadatas', 'documents'])

    print(f"\nProcessing {len(results['ids'])} chunks...")

    # Backup
    backup_dir = Path(f"data/dr_opa_agent/backups/opa_quality_standards_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    import json
    with open(backup_dir / 'metadata_summary.json', 'w') as f:
        json.dump({
            'collection_name': 'opa_quality_standards_corpus',
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'chunk_count': collection.count(),
            'sample_metadata': results['metadatas'][0] if results['metadatas'] else {}
        }, f, indent=2)

    print(f"Backed up to {backup_dir}")

    # Update each chunk's metadata
    updated_count = 0

    for chunk_id, metadata, text in zip(results['ids'], results['metadatas'], results['documents']):
        # Extract condition from title
        title = metadata.get('title', '')

        # Title format: "Ontario Health Quality Standard: <Condition>"
        condition_match = re.search(r'Quality Standard:\s*(.+?)(?:\s*$|\s*Quality Statement)', title)
        if condition_match:
            condition = condition_match.group(1).strip()
        else:
            # Fallback: try to extract from title
            condition = title.replace('Ontario Health Quality Standard:', '').strip()
            if not condition:
                condition = 'Unknown'

        # Build section_path
        chunk_type = metadata.get('chunk_type', '')
        statement_title = metadata.get('statement_title', '')

        if chunk_type == 'document':
            section_path = f"Ontario Health Quality Standards > {condition}"
        elif chunk_type == 'statement' and statement_title:
            section_path = f"Ontario Health Quality Standards > {condition} > {statement_title}"
        else:
            section_path = f"Ontario Health Quality Standards > {condition}"

        # Update metadata
        metadata['condition'] = condition
        metadata['section_path'] = section_path
        metadata['section_title'] = statement_title if statement_title else condition
        metadata['restructured_at'] = datetime.now().isoformat()

        # Update in ChromaDB
        collection.update(
            ids=[chunk_id],
            metadatas=[metadata]
        )

        updated_count += 1

        if updated_count % 50 == 0:
            print(f"  Updated {updated_count} chunks...")

    print(f"\n✓ Updated {updated_count} chunks")

    # Verify
    sample = collection.get(limit=3, include=['metadatas'])
    print(f"\n=== Sample Metadata ===")
    for i, (chunk_id, metadata) in enumerate(zip(sample['ids'], sample['metadatas'])):
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk_id}")
        print(f"  Condition: {metadata.get('condition')}")
        print(f"  Section path: {metadata.get('section_path')}")
        print(f"  Chunk type: {metadata.get('chunk_type')}")

    return {
        'total_chunks': collection.count(),
        'updated_count': updated_count,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    result = restructure_quality_standards()
    print(f"\n=== Restructure Complete ===")
    print(f"Summary: {result}")
