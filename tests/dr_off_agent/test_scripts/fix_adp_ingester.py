#!/usr/bin/env python3
"""
Modified ADP ingester to:
1. Use correct collection name (adp_documents)
2. Use same embedding model as other collections (text-embedding-ada-002)
3. Store in the correct ChromaDB location
"""

import os
import sys
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedADPIngester:
    """Fixed ADP ingester with correct collection name and embeddings"""
    
    def __init__(self):
        """Initialize with correct paths and embedding model"""
        
        # Use the same ChromaDB path as other collections
        self.chroma_path = "data/processed/dr_off/chroma"
        self.collection_name = "adp_documents"  # Match what tools expect
        
        # Setup Chroma client
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        
        # Use same embedding model as other collections (text-embedding-ada-002)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-ada-002"  # Same as other collections
            )
            logger.info("Using OpenAI text-embedding-ada-002 embeddings")
        else:
            raise ValueError("OPENAI_API_KEY required for embeddings")
        
        # Create or get collection
        try:
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name
            )
            # Clear existing if any
            self.chroma_client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted existing collection: {self.collection_name}")
        except:
            pass
        
        # Create fresh collection
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Created collection: {self.collection_name}")
    
    def ingest_adp_sections(self):
        """Ingest ADP sections from extracted JSON files"""
        
        # Load extracted ADP data
        comm_aids_file = "data/processed/adp_comm_aids_extracted.json"
        mobility_file = "data/processed/adp_mobility_extracted.json"
        
        all_sections = []
        
        # Load Communication Aids
        if os.path.exists(comm_aids_file):
            with open(comm_aids_file, 'r') as f:
                data = json.load(f)
                sections = data.get('sections', [])
                for section in sections:
                    section['source_doc'] = 'ADP Communication Aids Manual'
                    all_sections.append(section)
                logger.info(f"Loaded {len(sections)} Communication Aids sections")
        
        # Load Mobility Devices
        if os.path.exists(mobility_file):
            with open(mobility_file, 'r') as f:
                data = json.load(f)
                sections = data.get('sections', [])
                for section in sections:
                    section['source_doc'] = 'ADP Mobility Devices Manual'
                    all_sections.append(section)
                logger.info(f"Loaded {len(sections)} Mobility Devices sections")
        
        # Prepare documents for Chroma
        documents = []
        metadatas = []
        ids = []
        
        for i, section in enumerate(all_sections):
            # Create document text
            doc_text = f"Section: {section.get('section', '')}\n"
            doc_text += f"Subsection: {section.get('subsection', '')}\n"
            
            if section.get('title'):
                doc_text += f"Title: {section['title']}\n"
            
            doc_text += f"\n{section.get('content', '')}"
            
            # Create metadata
            metadata = {
                'section': section.get('section', ''),
                'subsection': section.get('subsection', ''),
                'title': section.get('title', ''),
                'source_document': section.get('source_doc', ''),
                'page_start': section.get('page_start', 0),
                'page_end': section.get('page_end', 0),
                'source_type': 'adp',
                'chunk_index': i
            }
            
            # Filter out None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(f"adp_chunk_{i}")
        
        # Add to Chroma in batches
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))
            batch_docs = documents[i:batch_end]
            batch_meta = metadatas[i:batch_end]
            batch_ids = ids[i:batch_end]
            
            self.collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
            logger.info(f"Added batch {i//batch_size + 1}: {len(batch_docs)} documents")
        
        logger.info(f"Successfully ingested {len(documents)} ADP sections into {self.collection_name}")
        
        # Verify
        count = self.collection.count()
        logger.info(f"Collection {self.collection_name} now has {count} documents")
        
        # Show sample
        sample = self.collection.peek(1)
        if sample['documents']:
            logger.info(f"Sample document: {sample['documents'][0][:200]}...")
            logger.info(f"Sample metadata: {sample['metadatas'][0]}")

def main():
    """Run the fixed ADP ingestion"""
    print("=" * 60)
    print("FIXED ADP VECTOR INGESTION")
    print("=" * 60)
    
    try:
        ingester = FixedADPIngester()
        ingester.ingest_adp_sections()
        print("\n✅ ADP vector ingestion complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())