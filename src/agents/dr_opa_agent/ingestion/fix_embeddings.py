#!/usr/bin/env python3
"""
Fix vector embedding dimension mismatch by recreating collection with correct OpenAI model.
This script:
1. Backs up existing data
2. Deletes the old collection
3. Creates new collection with text-embedding-3-small
4. Re-embeds all documents
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from tqdm import tqdm
import hashlib

# Load environment variables
load_dotenv()

class EmbeddingFixer:
    """Fix Chroma embedding dimension issues."""
    
    def __init__(
        self,
        db_path: str = "data/dr_opa_agent/opa.db",
        chroma_path: str = "data/dr_opa_agent/chroma",
        collection_name: str = "opa_cpso_corpus"
    ):
        self.db_path = Path(db_path)
        self.chroma_path = Path(chroma_path)
        self.collection_name = collection_name
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(str(self.chroma_path))
        
        # Get OpenAI API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        # Create OpenAI embedding function with correct model
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.api_key,
            model_name="text-embedding-3-small"  # This gives 1536 dimensions
        )
        
        print(f"Using OpenAI text-embedding-3-small (1536 dimensions)")
    
    def backup_existing_collection(self):
        """Backup existing collection data."""
        print("\n1. Backing up existing collection...")
        
        try:
            # Get existing collection (without embedding function to avoid error)
            old_collection = self.client.get_collection(self.collection_name)
            
            # Get all data
            data = old_collection.get()
            
            # Save to backup file
            backup_file = self.chroma_path / f"{self.collection_name}_backup.json"
            with open(backup_file, 'w') as f:
                json.dump({
                    'ids': data.get('ids', []),
                    'documents': data.get('documents', []),
                    'metadatas': data.get('metadatas', []),
                    'count': old_collection.count()
                }, f, indent=2)
            
            print(f"  ✓ Backed up {old_collection.count()} documents to {backup_file}")
            return data
            
        except Exception as e:
            print(f"  ⚠ No existing collection to backup: {e}")
            return None
    
    def get_documents_from_db(self) -> List[Dict[str, Any]]:
        """Get all documents from SQLite for re-embedding."""
        print("\n2. Fetching documents from SQLite...")
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT 
                s.section_id,
                s.document_id,
                s.chunk_type,
                s.parent_id,
                s.section_heading,
                s.section_text,
                s.section_idx,
                s.chunk_idx,
                d.source_org,
                d.document_type,
                d.title as document_title,
                d.effective_date,
                d.topics,
                d.policy_level,
                d.source_url
            FROM opa_sections s
            JOIN opa_documents d ON s.document_id = d.document_id
            WHERE d.is_superseded = 0
            ORDER BY s.document_id, s.section_idx, s.chunk_idx
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        
        documents = []
        for row in rows:
            doc = dict(row)
            
            # Parse topics if JSON
            if doc.get('topics'):
                try:
                    doc['topics'] = json.loads(doc['topics'])
                except:
                    doc['topics'] = []
            
            documents.append(doc)
        
        conn.close()
        print(f"  ✓ Retrieved {len(documents)} sections from database")
        return documents
    
    def create_new_collection(self):
        """Create new collection with correct embedding function."""
        print("\n3. Creating new collection with correct embeddings...")
        
        # Delete old collection if it exists
        try:
            self.client.delete_collection(self.collection_name)
            print(f"  ✓ Deleted old collection")
        except:
            print(f"  ⚠ No old collection to delete")
        
        # Create new collection with OpenAI embedding function
        collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={
                "source": "dr_opa",
                "organization": "cpso",
                "embedding_model": "text-embedding-3-small",
                "dimensions": "1536"
            }
        )
        
        print(f"  ✓ Created new collection with text-embedding-3-small")
        return collection
    
    def embed_documents(self, collection, documents: List[Dict[str, Any]]):
        """Embed documents into the new collection."""
        print(f"\n4. Embedding {len(documents)} documents...")
        
        # Process in batches to avoid API limits
        batch_size = 20
        embedded_count = 0
        
        for i in tqdm(range(0, len(documents), batch_size), desc="Embedding batches"):
            batch = documents[i:i+batch_size]
            
            ids = []
            texts = []
            metadatas = []
            
            for doc in batch:
                # Create unique ID
                doc_id = doc.get('section_id', '')
                if not doc_id:
                    # Generate ID from content hash
                    content = doc.get('section_text', '')
                    doc_id = hashlib.md5(content.encode()).hexdigest()[:16]
                
                # Prepare text with control tokens
                control_tokens = (
                    f"[ORG={doc.get('source_org', '')}] "
                    f"[TYPE={doc.get('document_type', '')}] "
                    f"[TOPIC={','.join(doc.get('topics', [])[:2])}] "
                )
                
                text = control_tokens + doc.get('section_text', '')
                
                # Prepare metadata (convert lists to strings for Chroma)
                metadata = {
                    'section_id': doc.get('section_id', ''),
                    'document_id': doc.get('document_id', ''),
                    'chunk_type': doc.get('chunk_type', ''),
                    'parent_id': doc.get('parent_id', '') or '',
                    'section_heading': doc.get('section_heading', ''),
                    'section_idx': str(doc.get('section_idx', 0)),
                    'chunk_idx': str(doc.get('chunk_idx', 0)),
                    'source_org': doc.get('source_org', ''),
                    'document_type': doc.get('document_type', ''),
                    'document_title': doc.get('document_title', ''),
                    'effective_date': doc.get('effective_date', '') or '',
                    'policy_level': doc.get('policy_level', '') or '',
                    'source_url': doc.get('source_url', '') or ''
                }
                
                # Convert topics list to string
                topics = doc.get('topics', [])
                if isinstance(topics, list):
                    metadata['topics'] = ','.join(topics)
                else:
                    metadata['topics'] = str(topics)
                
                # Remove None values and convert to strings
                metadata = {k: str(v) if v is not None else '' for k, v in metadata.items()}
                
                ids.append(doc_id)
                texts.append(text)
                metadatas.append(metadata)
            
            # Add to collection
            try:
                collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas
                )
                embedded_count += len(ids)
            except Exception as e:
                print(f"\n  ⚠ Error embedding batch: {e}")
                # Try individual documents if batch fails
                for j, (id_, text, meta) in enumerate(zip(ids, texts, metadatas)):
                    try:
                        collection.add(
                            ids=[id_],
                            documents=[text],
                            metadatas=[meta]
                        )
                        embedded_count += 1
                    except Exception as e2:
                        print(f"    ✗ Failed to embed document {id_}: {e2}")
        
        print(f"\n  ✓ Successfully embedded {embedded_count} documents")
        return embedded_count
    
    def verify_collection(self, collection):
        """Verify the new collection works correctly."""
        print("\n5. Verifying new collection...")
        
        # Test a query
        test_query = "informed consent medical records"
        
        try:
            results = collection.query(
                query_texts=[test_query],
                n_results=3
            )
            
            print(f"  ✓ Test query successful")
            print(f"    Query: '{test_query}'")
            print(f"    Results: {len(results['ids'][0])} documents found")
            
            if results['ids'][0]:
                print(f"    Top result: {results['metadatas'][0][0].get('section_heading', 'No heading')}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Test query failed: {e}")
            return False
    
    def run(self):
        """Run the complete fix process."""
        print("="*60)
        print("Fixing Vector Embedding Dimensions")
        print("="*60)
        
        # Backup existing data
        backup_data = self.backup_existing_collection()
        
        # Get documents from database
        documents = self.get_documents_from_db()
        
        if not documents:
            print("\n⚠ No documents found in database. Run ingestion first.")
            return False
        
        # Create new collection
        collection = self.create_new_collection()
        
        # Embed documents
        embedded_count = self.embed_documents(collection, documents)
        
        # Verify
        success = self.verify_collection(collection)
        
        # Summary
        print("\n" + "="*60)
        print("Summary")
        print("="*60)
        print(f"Total documents in DB: {len(documents)}")
        print(f"Successfully embedded: {embedded_count}")
        print(f"Collection verified: {'✓' if success else '✗'}")
        print(f"Final collection count: {collection.count()}")
        
        return success


def main():
    """Main entry point."""
    fixer = EmbeddingFixer()
    success = fixer.run()
    
    if success:
        print("\n✅ Embedding fix completed successfully!")
    else:
        print("\n⚠ Embedding fix completed with warnings. Please review.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()