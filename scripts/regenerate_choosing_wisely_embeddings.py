#!/usr/bin/env python3
"""Regenerate embeddings for Choosing Wisely corpus (384 -> 1536 dimensions).

Preserves all existing chunk structure and metadata, only updates embeddings.
"""

import chromadb
from chromadb.config import Settings
from datetime import datetime
from dotenv import load_dotenv
import os
import openai

# Load environment variables
load_dotenv()

def regenerate_embeddings():
    """Regenerate embeddings for Choosing Wisely corpus with 1536 dimensions."""

    print("=== Regenerating Choosing Wisely Embeddings ===")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Connect to ChromaDB
    client = chromadb.PersistentClient(
        path="data/dr_opa_agent/chroma",
        settings=Settings(anonymized_telemetry=False)
    )

    # Get existing collection
    collection_name = "opa_choosing_wisely_corpus"
    old_collection = client.get_collection(collection_name)

    print(f"Collection: {collection_name}")
    print(f"Current chunks: {old_collection.count()}")

    # Get all chunks (without embeddings)
    print("\nFetching all chunks...")
    results = old_collection.get(include=['metadatas', 'documents'])

    chunk_count = len(results['ids'])
    print(f"Retrieved {chunk_count} chunks")

    # Check current embedding dimension
    sample = old_collection.get(limit=1, include=['embeddings'])
    old_dim = len(sample['embeddings'][0])
    print(f"Current embedding dimension: {old_dim}")

    # Delete old collection
    print("\nDeleting old collection...")
    client.delete_collection(collection_name)
    print("✓ Deleted")

    # Create new collection (no embedding function - we'll provide embeddings manually)
    print("\nCreating new collection...")
    new_collection = client.create_collection(
        name=collection_name,
        metadata={"description": "Choosing Wisely Canada - regenerated with 1536-dim embeddings"}
    )
    print("✓ Created")

    # Initialize OpenAI client for embeddings
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    openai_client = openai.OpenAI(api_key=openai_api_key)
    embedding_model = "text-embedding-3-small"

    print(f"\n=== Generating New Embeddings ===")
    print(f"Model: {embedding_model} (1536 dimensions)")
    print(f"Total chunks to process: {chunk_count}\n")

    # Process in batches
    batch_size = 100
    total_processed = 0

    for i in range(0, chunk_count, batch_size):
        batch_end = min(i + batch_size, chunk_count)
        batch_ids = results['ids'][i:batch_end]
        batch_docs = results['documents'][i:batch_end]
        batch_metas = results['metadatas'][i:batch_end]

        # Generate embeddings for batch
        embedding_response = openai_client.embeddings.create(
            input=batch_docs,
            model=embedding_model
        )

        batch_embeddings = [item.embedding for item in embedding_response.data]

        # Verify dimension on first batch
        if i == 0:
            print(f"✓ First batch embedding dimension: {len(batch_embeddings[0])}")

        # Add to new collection
        new_collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=batch_metas
        )

        total_processed += len(batch_ids)
        print(f"  Processed {total_processed}/{chunk_count} chunks...")

    print(f"\n✓ All {chunk_count} chunks regenerated with new embeddings")

    # Verify
    print("\n=== Verification ===")
    verify_count = new_collection.count()
    verify_sample = new_collection.get(limit=1, include=['embeddings', 'metadatas'])
    new_dim = len(verify_sample['embeddings'][0])

    print(f"Final chunk count: {verify_count}")
    print(f"New embedding dimension: {new_dim}")

    # Sample metadata to confirm structure preserved
    print(f"\nSample metadata keys: {list(verify_sample['metadatas'][0].keys())[:10]}")

    success = (verify_count == chunk_count) and (new_dim == 1536)

    if success:
        print(f"\n✅ SUCCESS - Embeddings regenerated successfully!")
        print(f"   {old_dim} dim -> {new_dim} dim")
        print(f"   {verify_count} chunks preserved")
    else:
        print(f"\n⚠️  WARNING - Verification failed!")
        print(f"   Expected: {chunk_count} chunks, {1536} dim")
        print(f"   Got: {verify_count} chunks, {new_dim} dim")

    return {
        'success': success,
        'old_dimension': old_dim,
        'new_dimension': new_dim,
        'chunk_count': verify_count,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == "__main__":
    result = regenerate_embeddings()
    print(f"\nFinal result: {result}")
