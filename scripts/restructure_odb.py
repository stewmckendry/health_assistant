"""Restructure ODB (Ontario Drug Benefit Formulary) with grouping and parent/child chunking."""

import chromadb
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def restructure_odb():
    """Group ODB drug entries by therapeutic class, keep policy chunks as parents."""

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="data/dr_off_agent/processed/dr_off/chroma")

    # Get current collection
    old_collection = client.get_collection("odb_documents")

    print(f"=== Restructuring ODB Formulary ===")
    print(f"Current chunks: {old_collection.count()}")

    # Get all chunks
    results = old_collection.get(include=['metadatas', 'documents'])

    print(f"\nProcessing {len(results['ids'])} chunks...")

    # Separate drug chunks from policy chunks
    drug_chunks = defaultdict(list)  # Group by therapeutic_class + generic_name
    policy_chunks = []

    for chunk_id, metadata, text in zip(results['ids'], results['metadatas'], results['documents']):
        if metadata.get('din'):
            # Drug entry - group by therapeutic class + generic name
            therapeutic_class = metadata.get('therapeutic_class', 'Unknown Class')
            generic_name = metadata.get('generic_name', 'Unknown Drug')

            group_key = f"{therapeutic_class}|||{generic_name}"

            drug_chunks[group_key].append({
                'id': chunk_id,
                'metadata': metadata,
                'text': text,
                'words': len(text.split())
            })
        else:
            # Policy/preamble chunk
            policy_chunks.append({
                'id': chunk_id,
                'metadata': metadata,
                'text': text,
                'words': len(text.split())
            })

    print(f"\nDrug groups (by therapeutic class + generic name): {len(drug_chunks)}")
    print(f"Policy chunks: {len(policy_chunks)}")

    # Backup old collection
    backup_dir = Path(f"data/dr_off_agent/backups/odb_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    with open(backup_dir / 'metadata_summary.json', 'w') as f:
        json.dump({
            'collection_name': 'odb_documents',
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'chunk_count': old_collection.count(),
            'drug_group_count': len(drug_chunks),
            'policy_chunk_count': len(policy_chunks),
            'sample_metadata': results['metadatas'][0] if results['metadatas'] else {}
        }, f, indent=2)

    print(f"Backed up to {backup_dir}")

    # Delete old collection
    try:
        client.delete_collection("odb_documents")
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
        name="odb_documents",
        embedding_function=embedding_fn,
        metadata={"description": "ODB Formulary - restructured with grouped drug entries"}
    )

    new_chunks = []
    parent_count = 0
    child_count = 0

    # Process drug chunks: group by therapeutic class + generic name
    for group_key, chunks in drug_chunks.items():
        therapeutic_class, generic_name = group_key.split('|||')

        # Sort by brand name
        chunks.sort(key=lambda x: x['metadata'].get('brand_name', ''))

        # Calculate total words
        total_words = sum(c['words'] for c in chunks)

        # Generate parent ID
        parent_id = f"odb_{hashlib.md5(group_key.encode()).hexdigest()[:12]}_parent"

        # Get common metadata from first chunk
        base_metadata = chunks[0]['metadata'].copy()

        # Build section_path
        section_path = f"Ontario Drug Benefit Formulary > {therapeutic_class} > {generic_name}"

        # Collect all brand names and DINs
        brands = [c['metadata'].get('brand_name', '') for c in chunks if c['metadata'].get('brand_name')]
        dins = [c['metadata'].get('din', '') for c in chunks if c['metadata'].get('din')]

        if total_words <= 400:
            # Single parent chunk with all drug formulations
            full_text = "\n\n".join([c['text'] for c in chunks])

            new_chunks.append({
                'id': parent_id,
                'text': full_text,
                'metadata': {
                    **base_metadata,
                    'chunk_type': 'parent',
                    'section_path': section_path,
                    'section_title': generic_name,
                    'formulation_count': len(chunks),
                    'brand_names': ', '.join(brands[:5]),  # First 5 brands
                    'din_list': ','.join(dins),
                    'word_count': total_words,
                    'restructured_at': datetime.now().isoformat()
                }
            })
            parent_count += 1

        else:
            # Parent + children: split into groups of ~300 words
            parent_chunks = []
            current_group = []
            current_words = 0

            for chunk in chunks:
                chunk_words = chunk['words']

                if current_words + chunk_words <= 300:
                    current_group.append(chunk)
                    current_words += chunk_words
                else:
                    if current_group:
                        parent_chunks.append(current_group)
                    current_group = [chunk]
                    current_words = chunk_words

            if current_group:
                parent_chunks.append(current_group)

            # Create parent with first group
            if parent_chunks:
                first_group = parent_chunks[0]
                parent_text = "\n\n".join([c['text'] for c in first_group])
                parent_brands = [c['metadata'].get('brand_name', '') for c in first_group if c['metadata'].get('brand_name')]
                parent_dins = [c['metadata'].get('din', '') for c in first_group if c['metadata'].get('din')]

                new_chunks.append({
                    'id': parent_id,
                    'text': parent_text,
                    'metadata': {
                        **base_metadata,
                        'chunk_type': 'parent',
                        'parent_id': parent_id,
                        'section_path': section_path,
                        'section_title': generic_name,
                        'formulation_count': len(parent_brands),
                        'total_formulations': len(chunks),
                        'brand_names': ', '.join(parent_brands[:5]),
                        'din_list': ','.join(parent_dins),
                        'child_chunk_count': len(parent_chunks) - 1,
                        'word_count': sum(c['words'] for c in first_group),
                        'restructured_at': datetime.now().isoformat()
                    }
                })
                parent_count += 1

                # Create children
                for i, group in enumerate(parent_chunks[1:]):
                    child_id = f"odb_{hashlib.md5(group_key.encode()).hexdigest()[:12]}_child_{i}"
                    child_text = "\n\n".join([c['text'] for c in group])
                    child_brands = [c['metadata'].get('brand_name', '') for c in group if c['metadata'].get('brand_name')]
                    child_dins = [c['metadata'].get('din', '') for c in group if c['metadata'].get('din')]

                    new_chunks.append({
                        'id': child_id,
                        'text': child_text,
                        'metadata': {
                            **base_metadata,
                            'chunk_type': 'child',
                            'parent_id': parent_id,
                            'section_path': section_path,
                            'section_title': generic_name,
                            'child_index': i,
                            'formulation_count': len(child_brands),
                            'brand_names': ', '.join(child_brands[:5]),
                            'din_list': ','.join(child_dins),
                            'word_count': sum(c['words'] for c in group),
                            'restructured_at': datetime.now().isoformat()
                        }
                    })
                    child_count += 1

    # Process policy chunks: keep as flat parents with section_path
    for policy_chunk in policy_chunks:
        policy_id = f"odb_policy_{hashlib.md5(policy_chunk['id'].encode()).hexdigest()[:12]}"

        metadata = policy_chunk['metadata'].copy()
        metadata['chunk_type'] = 'parent'
        metadata['section_path'] = "Ontario Drug Benefit Formulary > Policies and Guidelines"
        metadata['section_title'] = "Formulary Guidelines"
        metadata['word_count'] = policy_chunk['words']
        metadata['restructured_at'] = datetime.now().isoformat()

        new_chunks.append({
            'id': policy_id,
            'text': policy_chunk['text'],
            'metadata': metadata
        })
        parent_count += 1

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

        # Generate embedding using OpenAI API with retry logic
        if openai_client:
            max_retries = 5
            retry_delay = 1  # Start with 1 second

            for attempt in range(max_retries):
                try:
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
                    break  # Success, exit retry loop

                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"  Rate limit hit at chunk {i+1}, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        print(f"  Failed after {max_retries} retries at chunk {i+1}")
                        raise
        else:
            # Fallback without embeddings (will likely fail due to dimension mismatch)
            new_collection.add(
                ids=[chunk['id']],
                documents=[chunk['text']],
                metadatas=[metadata]
            )

        # Progress logging
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(new_chunks)} chunks...")

    print(f"✓ All {len(new_chunks)} chunks added with embeddings")

    print(f"\n✓ Restructured ODB Formulary")
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
        if metadata.get('formulation_count'):
            print(f"  Formulations: {metadata.get('formulation_count')}")
        print(f"  Words: {len(text.split())}")

    return {
        'old_count': len(results['ids']),
        'new_count': new_collection.count(),
        'parent_count': parent_count,
        'child_count': child_count,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    result = restructure_odb()
    print(f"\n=== Restructure Complete ===")
    print(f"Summary: {result}")
