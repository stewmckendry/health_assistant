"""Add section_path metadata to existing PHO corpus chunks."""

import chromadb
from datetime import datetime

def add_section_path_to_pho():
    """Add section_path metadata to all PHO chunks."""

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
    collection = client.get_collection("opa_pho_corpus")

    print(f"=== Adding section_path to PHO Corpus ===")
    print(f"Total chunks: {collection.count()}")

    # Get all chunks
    results = collection.get(include=['metadatas'])

    updated_count = 0
    skipped_count = 0

    for chunk_id, metadata in zip(results['ids'], results['metadatas']):
        # Skip if section_path already exists
        if 'section_path' in metadata and metadata['section_path']:
            skipped_count += 1
            continue

        # Build section_path from title and section_heading
        title = metadata.get('title', 'Unknown Document')
        section_heading = metadata.get('section_heading', '')

        if section_heading:
            section_path = f"{title} > {section_heading}"
        else:
            section_path = f"{title} > Full Document"

        # Update metadata
        metadata['section_path'] = section_path

        # Update in ChromaDB
        collection.update(
            ids=[chunk_id],
            metadatas=[metadata]
        )

        updated_count += 1

        if updated_count % 10 == 0:
            print(f"  Updated {updated_count} chunks...")

    print(f"\n=== Update Complete ===")
    print(f"Updated: {updated_count}")
    print(f"Skipped (already had section_path): {skipped_count}")
    print(f"Total: {collection.count()}")

    # Verify updates
    print(f"\n=== Verification ===")
    verify_results = collection.get(limit=3, include=['metadatas'])
    for i, (chunk_id, metadata) in enumerate(zip(verify_results['ids'], verify_results['metadatas'])):
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk_id}")
        print(f"  section_path: {metadata.get('section_path', 'MISSING')}")

    return {
        'updated': updated_count,
        'skipped': skipped_count,
        'total': collection.count(),
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    stats = add_section_path_to_pho()
    print(f"\nFinal stats: {stats}")
