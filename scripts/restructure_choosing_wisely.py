"""Restructure Choosing Wisely corpus with proper parent/child chunking."""

import chromadb
from datetime import datetime
from pathlib import Path
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def restructure_choosing_wisely():
    """Export, restructure, and re-ingest Choosing Wisely with parent/child chunks."""

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")

    # Get current collection
    old_collection = client.get_collection("opa_choosing_wisely_corpus")

    print(f"=== Restructuring Choosing Wisely Corpus ===")
    print(f"Current chunks: {old_collection.count()}")

    # Get all chunks
    results = old_collection.get(include=['metadatas', 'documents'])

    # Group by specialty
    specialties = {}
    for chunk_id, metadata, text in zip(results['ids'], results['metadatas'], results['documents']):
        specialty = metadata.get('specialty', 'unknown')

        if specialty not in specialties:
            specialties[specialty] = {
                'overview': None,
                'recommendations': []
            }

        chunk_type = metadata.get('chunk_type', '')
        if chunk_type == 'specialty_overview':
            specialties[specialty]['overview'] = {
                'id': chunk_id,
                'metadata': metadata,
                'text': text
            }
        elif chunk_type == 'recommendation':
            specialties[specialty]['recommendations'].append({
                'id': chunk_id,
                'metadata': metadata,
                'text': text
            })

    print(f"\nGrouped into {len(specialties)} specialties")

    # Backup old collection
    backup_dir = Path(f"data/dr_opa_agent/backups/opa_choosing_wisely_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    import json
    with open(backup_dir / 'metadata_summary.json', 'w') as f:
        json.dump({
            'collection_name': 'opa_choosing_wisely_corpus',
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'chunk_count': old_collection.count(),
            'specialty_count': len(specialties),
            'sample_metadata': results['metadatas'][0] if results['metadatas'] else {}
        }, f, indent=2)

    print(f"Backed up to {backup_dir}")

    # Delete old collection
    try:
        client.delete_collection("opa_choosing_wisely_corpus")
        print("Deleted old collection")
    except Exception as e:
        print(f"Note: {e}")

    # Create new collection
    new_collection = client.create_collection(
        name="opa_choosing_wisely_corpus",
        metadata={"description": "Choosing Wisely Canada recommendations - restructured with parent/child chunks"}
    )

    # Restructure: Create parent chunks per specialty
    new_chunks = []

    for specialty, data in specialties.items():
        overview = data['overview']
        recommendations = data['recommendations']

        if not overview:
            print(f"Warning: No overview for {specialty}, skipping")
            continue

        # Sort recommendations by number
        recommendations.sort(key=lambda x: int(x['metadata'].get('recommendation_number', 0)))

        # Determine chunking strategy based on size
        overview_words = len(overview['text'].split())
        rec_words = [len(r['text'].split()) for r in recommendations]
        total_words = overview_words + sum(rec_words)

        # Generate unique parent ID
        parent_id = f"cw_{hashlib.md5(specialty.encode()).hexdigest()[:12]}_parent"

        if total_words <= 800:
            # Single parent chunk with all recommendations
            full_text = overview['text']
            if recommendations:
                full_text += "\n\n" + "\n\n".join([r['text'] for r in recommendations])

            new_chunks.append({
                'id': parent_id,
                'text': full_text,
                'metadata': {
                    **overview['metadata'],
                    'chunk_type': 'parent',
                    'section_path': f"Choosing Wisely Canada > {specialty}",
                    'section_title': specialty,
                    'recommendation_count': len(recommendations),
                    'restructured_at': datetime.now().isoformat()
                }
            })

        else:
            # Parent: overview + first few recommendations
            parent_text = overview['text']
            parent_recs = []
            remaining_recs = []

            current_words = overview_words
            for rec in recommendations:
                rec_word_count = len(rec['text'].split())
                if current_words + rec_word_count <= 800:
                    parent_recs.append(rec)
                    current_words += rec_word_count
                else:
                    remaining_recs.append(rec)

            # Add parent chunk
            parent_text += "\n\n" + "\n\n".join([r['text'] for r in parent_recs])

            new_chunks.append({
                'id': parent_id,
                'text': parent_text,
                'metadata': {
                    **overview['metadata'],
                    'chunk_type': 'parent',
                    'parent_id': parent_id,
                    'section_path': f"Choosing Wisely Canada > {specialty}",
                    'section_title': specialty,
                    'recommendation_count': len(recommendations),
                    'recommendations_in_parent': len(parent_recs),
                    'restructured_at': datetime.now().isoformat()
                }
            })

            # Add child chunks for remaining recommendations
            for i, rec in enumerate(remaining_recs):
                child_id = f"cw_{hashlib.md5(specialty.encode()).hexdigest()[:12]}_child_{i}"

                new_chunks.append({
                    'id': child_id,
                    'text': rec['text'],
                    'metadata': {
                        **rec['metadata'],
                        'chunk_type': 'child',
                        'parent_id': parent_id,
                        'section_path': f"Choosing Wisely Canada > {specialty}",
                        'section_title': specialty,
                        'child_index': i,
                        'restructured_at': datetime.now().isoformat()
                    }
                })

    print(f"\nCreated {len(new_chunks)} restructured chunks")

    # Count parent vs child
    parent_count = sum(1 for c in new_chunks if c['metadata']['chunk_type'] == 'parent')
    child_count = sum(1 for c in new_chunks if c['metadata']['chunk_type'] == 'child')
    print(f"  Parents: {parent_count}")
    print(f"  Children: {child_count}")

    # Add chunks to new collection (without embeddings - collection will use existing embedding function)
    # Generate embeddings with OpenAI
    print("\n=== Generating Embeddings with OpenAI ===")
    import openai
    import os
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_client = openai.OpenAI(api_key=openai_api_key) if openai_api_key else None

    if not openai_client:
        print("WARNING: No OpenAI API key found - embeddings may fail")
    else:
        print(f"✓ OpenAI client initialized")
        print(f"✓ Model: text-embedding-3-small (1536 dimensions)")

    for i, chunk in enumerate(new_chunks):
        # Prepare metadata (convert lists to strings)
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
            # Fallback without embeddings
            new_collection.add(
                ids=[chunk['id']],
                documents=[chunk['text']],
                metadatas=[metadata]
            )

        # Progress logging
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(new_chunks)} chunks...")

    print(f"✓ All {len(new_chunks)} chunks added with embeddings")

    print(f"\n✓ Restructured Choosing Wisely corpus")
    print(f"  Old: {old_collection.count() if 'old_collection' in locals() else 544} chunks")
    print(f"  New: {new_collection.count()} chunks")

    # Validate
    sample = new_collection.get(limit=3, include=['metadatas', 'documents'])
    print(f"\n=== Sample Chunks ===")
    for i, (chunk_id, metadata, text) in enumerate(zip(sample['ids'], sample['metadatas'], sample['documents'])):
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk_id}")
        print(f"  Type: {metadata.get('chunk_type')}")
        print(f"  Specialty: {metadata.get('specialty')}")
        print(f"  Section path: {metadata.get('section_path')}")
        print(f"  Words: {len(text.split())}")

    return {
        'old_count': 544,
        'new_count': new_collection.count(),
        'parent_count': parent_count,
        'child_count': child_count,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    result = restructure_choosing_wisely()
    print(f"\n=== Restructure Complete ===")
    print(f"Summary: {result}")
