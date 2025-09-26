#!/usr/bin/env python3
"""
Replace original collection with fixed one
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings

def replace_collection():
    """Replace original collection with the fixed one"""
    
    print("🔄 Replacing original collection with fixed version...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    
    # Get the fixed collection
    fixed_collection = client.get_collection('ohip_documents_fixed')
    total_docs = fixed_collection.count()
    print(f"📊 Fixed collection has {total_docs} documents")
    
    # Delete original
    try:
        client.delete_collection('ohip_documents')
        print("🗑️ Deleted original collection")
    except:
        print("⚠️ Original collection doesn't exist")
    
    # Create new collection with original name
    final_collection = client.create_collection(
        name='ohip_documents',
        metadata={
            "hnsw:space": "cosine",
            "source": "ohip",
            "description": "OHIP fee codes with cosine similarity (fixed)"
        }
    )
    print("✅ Created new collection with cosine similarity")
    
    # Copy all data
    batch_size = 500
    
    # Get all IDs
    all_ids = []
    offset = 0
    while offset < total_docs:
        batch = fixed_collection.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas"]
        )
        all_ids.extend(batch['ids'])
        offset += len(batch['ids'])
    
    print(f"📋 Copying {len(all_ids)} documents...")
    
    # Copy in batches
    with tqdm(total=len(all_ids), desc="Copying documents") as pbar:
        for i in range(0, len(all_ids), batch_size):
            batch_ids = all_ids[i:i+batch_size]
            
            batch_data = fixed_collection.get(
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
    client.delete_collection('ohip_documents_fixed')
    print("🗑️ Deleted temporary fixed collection")
    
    # Verify
    final_count = final_collection.count()
    print(f"\n✅ Success! Original collection replaced with fixed version")
    print(f"📊 Final collection has {final_count} documents")
    print(f"📐 Using cosine similarity metric for better search results")

if __name__ == "__main__":
    replace_collection()