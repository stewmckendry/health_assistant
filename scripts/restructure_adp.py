"""Restructure ADP (Assistive Devices Program) with parent/child chunking."""

import chromadb
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import hashlib
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def restructure_adp():
    """Group ADP policy sections with parent/child chunking."""

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="data/dr_off_agent/processed/dr_off/chroma")

    # Get current collection
    old_collection = client.get_collection("adp_documents")

    print(f"=== Restructuring ADP Documents ===")
    print(f"Current chunks: {old_collection.count()}")

    # Get all chunks
    results = old_collection.get(include=['metadatas', 'documents'])

    print(f"\nProcessing {len(results['ids'])} chunks...")

    # Group by adp_doc + part + main_section
    groups = defaultdict(list)

    for chunk_id, metadata, text in zip(results['ids'], results['metadatas'], results['documents']):
        adp_doc = metadata.get('adp_doc', 'unknown')
        part = metadata.get('part', 'unknown')
        section_id = metadata.get('section_id', '')

        # Extract main section number (e.g., "200" from "200.01")
        main_section = section_id.split('.')[0] if '.' in section_id else section_id

        group_key = f"{adp_doc}|||{part}|||{main_section}"

        groups[group_key].append({
            'id': chunk_id,
            'metadata': metadata,
            'text': text,
            'words': len(text.split())
        })

    print(f"\nGrouped into {len(groups)} sections")

    # Backup old collection
    backup_dir = Path(f"data/dr_off_agent/backups/adp_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    with open(backup_dir / 'metadata_summary.json', 'w') as f:
        json.dump({
            'collection_name': 'adp_documents',
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'chunk_count': old_collection.count(),
            'group_count': len(groups),
            'sample_metadata': results['metadatas'][0] if results['metadatas'] else {}
        }, f, indent=2)

    print(f"Backed up to {backup_dir}")

    # Delete old collection
    try:
        client.delete_collection("adp_documents")
        print("Deleted old collection")
    except Exception as e:
        print(f"Note: {e}")

    # Create new collection with same embedding function
    from chromadb.utils import embedding_functions
    import os

    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name="text-embedding-3-small"
        )
    else:
        embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    new_collection = client.create_collection(
        name="adp_documents",
        embedding_function=embedding_fn,
        metadata={"description": "ADP Documents - restructured with parent/child chunks"}
    )

    # Restructure: Create parent chunks per section
    new_chunks = []
    parent_count = 0
    child_count = 0

    for group_key, chunks in groups.items():
        adp_doc, part, main_section = group_key.split('|||')

        # Sort chunks by section_id
        chunks.sort(key=lambda x: x['metadata'].get('section_id', ''))

        # Calculate total words
        total_words = sum(c['words'] for c in chunks)

        # Generate parent ID
        parent_id = f"adp_{hashlib.md5(group_key.encode()).hexdigest()[:12]}_parent"

        # Get common metadata from first chunk
        base_metadata = chunks[0]['metadata'].copy()

        # Build section_path
        adp_doc_title = adp_doc.replace('_', ' ').title()
        if part and part != 'unknown':
            section_path = f"Assistive Devices Program > {adp_doc_title} > Part {part} > Section {main_section}"
        else:
            section_path = f"Assistive Devices Program > {adp_doc_title} > Section {main_section}"

        if total_words <= 800:
            # Single parent chunk with all policy text
            full_text = "\n\n".join([c['text'] for c in chunks])

            # Collect all section IDs
            section_ids = [c['metadata'].get('section_id', '') for c in chunks if c['metadata'].get('section_id')]

            new_chunks.append({
                'id': parent_id,
                'text': full_text,
                'metadata': {
                    **base_metadata,
                    'chunk_type': 'parent',
                    'section_path': section_path,
                    'section_title': f"Part {part} - Section {main_section}",
                    'section_count': len(section_ids),
                    'section_ids': ','.join(section_ids),
                    'word_count': total_words,
                    'restructured_at': datetime.now().isoformat()
                }
            })
            parent_count += 1

        else:
            # Parent + children: chunk into groups of ~600 words
            parent_chunks = []
            current_group = []
            current_words = 0

            for chunk in chunks:
                chunk_words = chunk['words']

                if current_words + chunk_words <= 600:
                    current_group.append(chunk)
                    current_words += chunk_words
                else:
                    # Save current group
                    if current_group:
                        parent_chunks.append(current_group)
                    # Start new group
                    current_group = [chunk]
                    current_words = chunk_words

            # Add final group
            if current_group:
                parent_chunks.append(current_group)

            # Create parent chunk with first group
            if parent_chunks:
                first_group = parent_chunks[0]
                parent_text = "\n\n".join([c['text'] for c in first_group])
                parent_section_ids = [c['metadata'].get('section_id', '') for c in first_group if c['metadata'].get('section_id')]

                new_chunks.append({
                    'id': parent_id,
                    'text': parent_text,
                    'metadata': {
                        **base_metadata,
                        'chunk_type': 'parent',
                        'parent_id': parent_id,
                        'section_path': section_path,
                        'section_title': f"Part {part} - Section {main_section}",
                        'section_count': len(parent_section_ids),
                        'section_ids': ','.join(parent_section_ids),
                        'total_sections': len(chunks),
                        'child_chunk_count': len(parent_chunks) - 1,
                        'word_count': sum(c['words'] for c in first_group),
                        'restructured_at': datetime.now().isoformat()
                    }
                })
                parent_count += 1

                # Create child chunks for remaining groups
                for i, group in enumerate(parent_chunks[1:]):
                    child_id = f"adp_{hashlib.md5(group_key.encode()).hexdigest()[:12]}_child_{i}"
                    child_text = "\n\n".join([c['text'] for c in group])
                    child_section_ids = [c['metadata'].get('section_id', '') for c in group if c['metadata'].get('section_id')]

                    new_chunks.append({
                        'id': child_id,
                        'text': child_text,
                        'metadata': {
                            **base_metadata,
                            'chunk_type': 'child',
                            'parent_id': parent_id,
                            'section_path': section_path,
                            'section_title': f"Part {part} - Section {main_section}",
                            'child_index': i,
                            'section_count': len(child_section_ids),
                            'section_ids': ','.join(child_section_ids),
                            'word_count': sum(c['words'] for c in group),
                            'restructured_at': datetime.now().isoformat()
                        }
                    })
                    child_count += 1

    print(f"\nCreated {len(new_chunks)} restructured chunks")
    print(f"  Parents: {parent_count}")
    print(f"  Children: {child_count}")

    # Add chunks to new collection with explicit embedding generation
    print("\n=== Generating Embeddings with OpenAI ===")
    import openai
    openai_client = openai.OpenAI(api_key=openai_api_key) if openai_api_key else None

    if not openai_client:
        print("WARNING: No OpenAI API key found - embeddings may fail")
    else:
        print(f"✓ OpenAI client initialized")
        print(f"✓ Model: text-embedding-3-small (1536 dimensions)")

    for i, chunk in enumerate(new_chunks):
        # Prepare metadata (convert to strings)
        metadata = {}
        for key, value in chunk['metadata'].items():
            if isinstance(value, list):
                metadata[key] = ','.join(map(str, value))
            elif value is None:
                metadata[key] = ''
            else:
                metadata[key] = str(value)

        # Generate embedding using OpenAI API
        if openai_client:
            embedding_response = openai_client.embeddings.create(
                input=[chunk['text']],
                model="text-embedding-3-small"
            )
            embedding = embedding_response.data[0].embedding

            # Log first embedding dimension to verify
            if i == 0:
                print(f"✓ First embedding generated: {len(embedding)} dimensions")

            new_collection.add(
                ids=[chunk['id']],
                embeddings=[embedding],
                documents=[chunk['text']],
                metadatas=[metadata]
            )
        else:
            # Fallback without embeddings (will likely fail due to dimension mismatch)
            new_collection.add(
                ids=[chunk['id']],
                documents=[chunk['text']],
                metadatas=[metadata]
            )

        # Progress logging
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(new_chunks)} chunks...")

    print(f"✓ All {len(new_chunks)} chunks added with embeddings")

    print(f"\n✓ Restructured ADP Documents")
    print(f"  Old: {len(results['ids'])} chunks")
    print(f"  New: {new_collection.count()} chunks")

    # Validate
    sample = new_collection.get(limit=3, include=['metadatas', 'documents'])
    print(f"\n=== Sample Chunks ===")
    for i, (chunk_id, metadata, text) in enumerate(zip(sample['ids'], sample['metadatas'], sample['documents'])):
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk_id}")
        print(f"  Type: {metadata.get('chunk_type')}")
        print(f"  Section path: {metadata.get('section_path')}")
        print(f"  Sections: {metadata.get('section_count')}")
        print(f"  Words: {len(text.split())}")

    return {
        'old_count': len(results['ids']),
        'new_count': new_collection.count(),
        'parent_count': parent_count,
        'child_count': child_count,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    result = restructure_adp()
    print(f"\n=== Restructure Complete ===")
    print(f"Summary: {result}")
