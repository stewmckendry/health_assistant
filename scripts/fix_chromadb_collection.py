#!/usr/bin/env python3
"""
Fix ChromaDB collection by recreating it with cosine similarity metric
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings

def fix_collection():
    """Recreate ChromaDB collection with cosine similarity"""
    
    print("🔧 Fixing ChromaDB Collection...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    
    # Get existing collection
    old_collection = client.get_collection('ohip_documents')
    total_docs = old_collection.count()
    print(f"📊 Current collection has {total_docs} documents")
    
    # Create new collection with cosine similarity
    new_collection_name = 'ohip_documents_fixed'
    
    # Delete if exists
    try:
        client.delete_collection(new_collection_name)
        print(f"🗑️ Deleted existing {new_collection_name}")
    except:
        pass
    
    # Create with cosine metric
    new_collection = client.create_collection(
        name=new_collection_name,
        metadata={
            "hnsw:space": "cosine",  # Use cosine similarity
            "source": "ohip",
            "description": "OHIP fee codes with cosine similarity"
        }
    )
    print(f"✅ Created new collection with cosine similarity")
    
    # Migrate data in batches
    batch_size = 500
    print(f"\n📦 Migrating {total_docs} documents in batches of {batch_size}...")
    
    # Get all document IDs first
    all_ids = []
    offset = 0
    while offset < total_docs:
        batch = old_collection.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas"]
        )
        all_ids.extend(batch['ids'])
        offset += len(batch['ids'])
    
    print(f"📋 Retrieved {len(all_ids)} document IDs")
    
    # Process in batches
    with tqdm(total=len(all_ids), desc="Migrating documents") as pbar:
        for i in range(0, len(all_ids), batch_size):
            batch_ids = all_ids[i:i+batch_size]
            
            # Get batch data
            batch_data = old_collection.get(
                ids=batch_ids,
                include=["documents", "embeddings", "metadatas"]
            )
            
            # Add to new collection
            if batch_data['documents']:
                new_collection.add(
                    ids=batch_data['ids'],
                    embeddings=batch_data['embeddings'],
                    documents=batch_data['documents'],
                    metadatas=batch_data['metadatas']
                )
            
            pbar.update(len(batch_ids))
    
    # Verify migration
    new_count = new_collection.count()
    print(f"\n✅ Migration complete!")
    print(f"📊 New collection has {new_count} documents (original: {total_docs})")
    
    # Test the new collection
    print("\n🧪 Testing new collection...")
    
    # Test query
    import openai
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    test_queries = [
        "hospital admission assessment",
        "day following hospital admission",
        "subsequent visit by physician"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Generate embedding
        query_embedding = openai_client.embeddings.create(
            input=[query],
            model="text-embedding-3-small"
        ).data[0].embedding
        
        # Query new collection
        results = new_collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            where={"source_type": "ohip"}
        )
        
        if results['documents'][0]:
            print(f"Top 5 results (with cosine similarity):")
            for j, doc in enumerate(results['documents'][0][:5]):
                distance = results['distances'][0][j]
                similarity = 1 - distance
                metadata = results['metadatas'][0][j]
                fee_code = metadata.get('fee_code', 'Unknown')
                print(f"  {j+1}. Code: {fee_code} | Similarity: {similarity:.4f}")
                print(f"     {doc[:80]}...")
        else:
            print("  No results found")
    
    print("\n🎯 Next Steps:")
    print("1. Update schedule.py to use 'ohip_documents_fixed' collection")
    print("2. Or rename collections to replace the original")
    
    # Ask user if they want to replace the original
    response = input("\n❓ Replace original collection with fixed one? (y/n): ")
    if response.lower() == 'y':
        # Delete original
        client.delete_collection('ohip_documents')
        print("🗑️ Deleted original collection")
        
        # Can't rename in ChromaDB, so we need to copy again with the original name
        final_collection = client.create_collection(
            name='ohip_documents',
            metadata={
                "hnsw:space": "cosine",
                "source": "ohip",
                "description": "OHIP fee codes with cosine similarity (fixed)"
            }
        )
        
        # Copy from fixed to final
        print("📦 Creating final collection with original name...")
        with tqdm(total=new_count, desc="Final migration") as pbar:
            for i in range(0, len(all_ids), batch_size):
                batch_ids = all_ids[i:i+batch_size]
                
                batch_data = new_collection.get(
                    ids=batch_ids,
                    include=["documents", "embeddings", "metadatas"]
                )
                
                if batch_data['documents']:
                    final_collection.add(
                        ids=batch_data['ids'],
                        embeddings=batch_data['embeddings'],
                        documents=batch_data['documents'],
                        metadatas=batch_data['metadatas']
                    )
                
                pbar.update(len(batch_ids))
        
        # Delete the temporary fixed collection
        client.delete_collection(new_collection_name)
        print(f"🗑️ Deleted temporary {new_collection_name}")
        print("✅ Original collection replaced with fixed version!")
    else:
        print("ℹ️ Kept both collections. Update code to use 'ohip_documents_fixed'")

if __name__ == "__main__":
    fix_collection()