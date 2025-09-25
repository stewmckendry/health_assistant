#!/usr/bin/env python3
"""
Migrate ADP collection from adp_v1 to adp_documents in primary Chroma instance.
This fixes the VectorClient to use the correct collection with 610 chunks instead of 199.
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
import logging
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_adp_collection():
    """Migrate ADP chunks from adp_v1 to adp_documents in primary instance."""
    
    # Source: adp_v1 collection (610 chunks with good metadata)
    source_path = "data/processed/dr_off/chroma"
    
    # Target: primary chroma instance (with OHIP and ODB collections)
    target_path = "data/dr_off_agent/processed/dr_off/chroma"
    
    logger.info(f"Migrating ADP collection from {source_path} to {target_path}")
    
    try:
        # Connect to source ChromaDB
        source_client = chromadb.PersistentClient(
            path=source_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get adp_v1 collection
        source_collection = source_client.get_collection("adp_v1")
        source_count = source_collection.count()
        logger.info(f"Source collection adp_v1 has {source_count} chunks")
        
        # Get all data from source collection (skip embeddings for now)
        logger.info("Getting documents and metadata from source collection...")
        all_data = source_collection.get(
            include=["documents", "metadatas"]
        )
        
        # Try to get embeddings separately
        try:
            logger.info("Getting embeddings...")
            embedding_data = source_collection.get(
                include=["embeddings"]
            )
            all_data["embeddings"] = embedding_data["embeddings"]
        except Exception as e:
            logger.warning(f"Could not get embeddings: {e}")
            all_data["embeddings"] = None
        
        logger.info(f"Retrieved {len(all_data['documents'])} documents from source")
        
        # Debug embeddings structure
        embeddings = all_data.get('embeddings')
        if embeddings is not None and len(embeddings) > 0:
            logger.info(f"Embeddings type: {type(embeddings)}")
            logger.info(f"First embedding type: {type(embeddings[0])}")
            logger.info(f"First embedding shape: {len(embeddings[0])}")
        else:
            logger.info("No embeddings found")
        
        # Connect to target ChromaDB 
        target_client = chromadb.PersistentClient(
            path=target_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get adp_documents collection in target
        try:
            # Try to delete existing adp_documents if it exists
            target_client.delete_collection("adp_documents")
            logger.info("Deleted existing adp_documents collection")
        except Exception:
            logger.info("No existing adp_documents collection to delete")
        
        # Create new adp_documents collection
        logger.info("Creating target collection adp_documents")
        
        target_collection = target_client.create_collection(
            name="adp_documents",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity like other collections
        )
        
        # Add all data to target collection in batches
        batch_size = 100
        total_docs = len(all_data['documents'])
        
        for i in range(0, total_docs, batch_size):
            batch_end = min(i + batch_size, total_docs)
            
            batch_ids = [f"adp_chunk_{j}" for j in range(i, batch_end)]
            batch_documents = all_data['documents'][i:batch_end]
            
            # Handle metadatas safely
            batch_metadatas = None
            if all_data.get('metadatas') is not None:
                batch_metadatas = all_data['metadatas'][i:batch_end]
            
            # Handle embeddings safely  
            batch_embeddings = None
            embeddings = all_data.get('embeddings')
            if embeddings is not None:
                batch_embeddings = embeddings[i:batch_end].tolist()  # Convert numpy to list
            
            target_collection.add(
                ids=batch_ids,
                documents=batch_documents,
                metadatas=batch_metadatas,
                embeddings=batch_embeddings
            )
            
            logger.info(f"Added batch {i//batch_size + 1}: documents {i} to {batch_end}")
        
        # Verify migration
        target_count = target_collection.count()
        logger.info(f"Target collection adp_documents now has {target_count} chunks")
        
        if target_count == source_count:
            logger.info("✅ Migration successful!")
            
            # Test a sample query to verify embeddings work
            try:
                test_results = target_collection.query(
                    query_texts=["wheelchair funding"],
                    n_results=3
                )
                logger.info(f"✅ Test query returned {len(test_results['documents'][0])} results")
                
                # Show sample metadata
                if test_results['metadatas'][0]:
                    sample_metadata = test_results['metadatas'][0][0]
                    logger.info(f"Sample metadata: {sample_metadata}")
                
            except Exception as e:
                logger.error(f"❌ Test query failed: {e}")
        else:
            logger.error(f"❌ Migration failed: expected {source_count}, got {target_count}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_adp_collection()
    sys.exit(0 if success else 1)