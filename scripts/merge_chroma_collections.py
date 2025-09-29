#!/usr/bin/env python3
"""Merge PHO and CEP collections from processed dir into main dr_opa_agent dir where CPSO is."""

import chromadb
from chromadb.utils import embedding_functions
import os
from pathlib import Path
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def merge_collections():
    """Merge collections from processed/dr_opa/chroma into dr_opa_agent/chroma."""
    
    # Source and target paths
    source_path = "data/processed/dr_opa/chroma"
    target_path = "data/dr_opa_agent/chroma"
    
    print(f"\n{'='*60}")
    print("Merging Chroma Collections")
    print(f"{'='*60}")
    print(f"Source: {source_path}")
    print(f"Target: {target_path}")
    print()
    
    # Initialize clients
    source_client = chromadb.PersistentClient(path=source_path)
    target_client = chromadb.PersistentClient(path=target_path)
    
    # Set up OpenAI embedding function
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return False
    
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )
    
    # Get source collections
    source_collections = source_client.list_collections()
    
    for source_col in source_collections:
        collection_name = source_col.name
        print(f"\n📦 Processing: {collection_name}")
        
        # Get source collection (without embedding function to avoid conflict)
        source_collection = source_client.get_collection(
            name=collection_name
        )
        
        # Count documents in source
        source_count = source_collection.count()
        print(f"  Source documents: {source_count}")
        
        if source_count == 0:
            print(f"  ⚠️ No documents to migrate")
            continue
        
        # Check if collection exists in target
        target_collections = [c.name for c in target_client.list_collections()]
        
        if collection_name in target_collections:
            print(f"  ⚠️ Collection already exists in target - merging...")
            # Get existing collection without embedding function
            target_collection = target_client.get_collection(
                name=collection_name
            )
        else:
            print(f"  ✅ Creating new collection in target")
            # Create with OpenAI embedding function for consistency
            target_collection = target_client.create_collection(
                name=collection_name,
                embedding_function=embedding_function,
                metadata={"source": "dr_opa", "merged": "true"}
            )
        
        # Get all documents from source
        print(f"  📥 Fetching documents from source...")
        
        # Fetch in batches
        batch_size = 100
        total_migrated = 0
        
        # Get all IDs first
        all_data = source_collection.get()
        total_docs = len(all_data['ids'])
        
        print(f"  📊 Total documents to migrate: {total_docs}")
        
        # Process in batches
        for i in tqdm(range(0, total_docs, batch_size), desc="  Migrating"):
            batch_ids = all_data['ids'][i:i+batch_size]
            batch_docs = all_data['documents'][i:i+batch_size] if all_data.get('documents') else None
            batch_metadatas = all_data['metadatas'][i:i+batch_size] if all_data.get('metadatas') else None
            batch_embeddings = all_data['embeddings'][i:i+batch_size] if all_data.get('embeddings') else None
            
            # Check for duplicates
            existing_ids = []
            try:
                existing = target_collection.get(ids=batch_ids)
                existing_ids = existing['ids'] if existing and existing.get('ids') else []
            except:
                pass
            
            # Filter out existing IDs
            new_ids = []
            new_docs = []
            new_metadatas = []
            new_embeddings = []
            
            for j, doc_id in enumerate(batch_ids):
                if doc_id not in existing_ids:
                    new_ids.append(doc_id)
                    if batch_docs:
                        new_docs.append(batch_docs[j])
                    if batch_metadatas:
                        new_metadatas.append(batch_metadatas[j])
                    if batch_embeddings:
                        new_embeddings.append(batch_embeddings[j])
            
            if new_ids:
                # Add to target collection
                try:
                    if new_embeddings:
                        # Use existing embeddings
                        target_collection.add(
                            ids=new_ids,
                            documents=new_docs if new_docs else None,
                            metadatas=new_metadatas if new_metadatas else None,
                            embeddings=new_embeddings
                        )
                    else:
                        # Let it generate embeddings
                        target_collection.add(
                            ids=new_ids,
                            documents=new_docs if new_docs else None,
                            metadatas=new_metadatas if new_metadatas else None
                        )
                    
                    total_migrated += len(new_ids)
                except Exception as e:
                    print(f"\n  ❌ Error adding batch: {e}")
                    continue
            else:
                print(f"\n  ⚠️ All {len(batch_ids)} documents in this batch already exist")
        
        # Verify migration
        target_count = target_collection.count()
        print(f"\n  ✅ Migration complete!")
        print(f"     Documents migrated: {total_migrated}")
        print(f"     Total in target: {target_count}")
    
    print(f"\n{'='*60}")
    print("Verification")
    print(f"{'='*60}")
    
    # List all collections in target
    final_collections = target_client.list_collections()
    print(f"\nCollections in {target_path}:")
    for col in final_collections:
        collection = target_client.get_collection(col.name)
        count = collection.count()
        print(f"  - {col.name}: {count} documents")
        
        # Get sample metadata
        sample = collection.get(limit=1)
        if sample and sample['metadatas']:
            meta = sample['metadatas'][0]
            print(f"    Sample: source_org={meta.get('source_org', 'N/A')}")
    
    return True


def main():
    """Main entry point."""
    from dotenv import load_dotenv
    
    # Load environment variables
    env_path = '/Users/liammckendry/health_assistant_dr_off_worktree/.env'
    load_dotenv(env_path)
    
    success = merge_collections()
    
    if success:
        print("\n✅ Merge completed successfully!")
        print("\n📝 Next steps:")
        print("  1. Update MCP vector client to use 'data/dr_opa_agent/chroma'")
        print("  2. Test retrieval with merged collections")
        print("  3. Optionally remove old collections from 'data/processed/dr_opa/chroma'")
    else:
        print("\n❌ Merge failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())