#!/usr/bin/env python3
"""Populate SQLite database with PHO documents that are already in Chroma."""

import sqlite3
import json
import chromadb
from pathlib import Path
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_pho_sqlite():
    """Populate SQLite with PHO documents from Chroma collection."""
    
    print("\n" + "="*60)
    print("Populating SQLite with PHO Documents")
    print("="*60)
    
    # Load environment
    load_dotenv('/Users/liammckendry/health_assistant_dr_off_worktree/.env')
    
    # Connect to databases
    sqlite_path = "data/processed/dr_opa/opa.db"
    chroma_path = "data/dr_opa_agent/chroma"
    
    # SQLite connection
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()
    
    # Chroma client
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    
    # Get PHO collection
    try:
        pho_collection = chroma_client.get_collection("opa_pho_corpus")
        print(f"✅ Found PHO collection with {pho_collection.count()} documents")
    except Exception as e:
        print(f"❌ Error getting PHO collection: {e}")
        return False
    
    # Get all PHO documents from Chroma
    all_data = pho_collection.get()
    
    if not all_data or not all_data.get('ids'):
        print("❌ No documents found in PHO collection")
        return False
    
    # Track unique documents
    documents_added = set()
    sections_added = 0
    
    # Process each chunk
    for i, chunk_id in enumerate(all_data['ids']):
        metadata = all_data['metadatas'][i] if all_data.get('metadatas') else {}
        text = all_data['documents'][i] if all_data.get('documents') else ""
        
        # Extract document info from metadata - use the actual document_id from Chroma
        doc_id = metadata.get('document_id', f"pho_doc_{i}")
        
        # Add document if not already added
        if doc_id not in documents_added:
            try:
                # Prepare document data
                doc_data = {
                    'document_id': doc_id,
                    'source_url': metadata.get('source_url', 'https://www.publichealthontario.ca'),
                    'source_org': 'pho',
                    'document_type': metadata.get('document_type', 'ipac-guidance'),
                    'title': metadata.get('title', 'PHO IPAC Guidance'),
                    'effective_date': metadata.get('effective_date'),
                    'updated_date': metadata.get('revision_date'),
                    'published_date': metadata.get('published_date'),
                    'topics': metadata.get('topics', 'ipac,clinical-office'),
                    'policy_level': metadata.get('policy_level', 'guidance'),
                    'content_hash': metadata.get('content_hash', ''),
                    'metadata_json': json.dumps(metadata),
                    'is_superseded': 0,
                    'ingested_at': datetime.now().isoformat()
                }
                
                # Insert document
                cursor.execute("""
                    INSERT OR IGNORE INTO opa_documents (
                        document_id, source_url, source_org, document_type,
                        title, effective_date, updated_date, published_date,
                        topics, policy_level, content_hash, metadata_json,
                        is_superseded, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_data['document_id'],
                    doc_data['source_url'],
                    doc_data['source_org'],
                    doc_data['document_type'],
                    doc_data['title'],
                    doc_data['effective_date'],
                    doc_data['updated_date'],
                    doc_data['published_date'],
                    doc_data['topics'],
                    doc_data['policy_level'],
                    doc_data['content_hash'],
                    doc_data['metadata_json'],
                    doc_data['is_superseded'],
                    doc_data['ingested_at']
                ))
                
                documents_added.add(doc_id)
                
                if cursor.rowcount > 0:
                    print(f"  ✅ Added document: {doc_data['title'][:50]}...")
                
            except sqlite3.IntegrityError as e:
                # Document already exists
                pass
            except Exception as e:
                print(f"  ❌ Error adding document {doc_id}: {e}")
        
        # Add section
        try:
            section_data = {
                'section_id': chunk_id,
                'document_id': doc_id,
                'chunk_type': metadata.get('chunk_type', 'unknown'),
                'parent_id': metadata.get('parent_id'),
                'section_heading': metadata.get('section_heading', ''),
                'section_text': text,
                'section_idx': metadata.get('section_idx', 0),
                'chunk_idx': metadata.get('chunk_idx', 0),
                'embedding_model': 'text-embedding-3-small',
                'embedding_id': chunk_id,
                'metadata_json': json.dumps(metadata)
            }
            
            # Insert section
            cursor.execute("""
                INSERT OR REPLACE INTO opa_sections (
                    section_id, document_id, chunk_type, parent_id,
                    section_heading, section_text, section_idx, chunk_idx,
                    embedding_model, embedding_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                section_data['section_id'],
                section_data['document_id'],
                section_data['chunk_type'],
                section_data['parent_id'],
                section_data['section_heading'],
                section_data['section_text'],
                section_data['section_idx'],
                section_data['chunk_idx'],
                section_data['embedding_model'],
                section_data['embedding_id'],
                section_data['metadata_json']
            ))
            
            if cursor.rowcount > 0:
                sections_added += 1
            
        except Exception as e:
            print(f"  ❌ Error adding section {chunk_id}: {e}")
    
    # Commit changes
    conn.commit()
    
    # Verify results
    cursor.execute("SELECT COUNT(*) FROM opa_documents WHERE source_org = 'pho'")
    doc_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM opa_sections WHERE document_id IN (SELECT document_id FROM opa_documents WHERE source_org = 'pho')")
    section_count = cursor.fetchone()[0]
    
    print("\n" + "="*60)
    print("Results Summary")
    print("="*60)
    print(f"✅ Documents in SQLite: {doc_count}")
    print(f"✅ Sections in SQLite: {section_count}")
    print(f"✅ New documents added: {len(documents_added)}")
    print(f"✅ New sections added: {sections_added}")
    
    # Test SQL search
    print("\n" + "="*60)
    print("Testing SQL Full-Text Search")
    print("="*60)
    
    test_queries = [
        "hand hygiene",
        "sterilization",
        "PPE personal protective equipment"
    ]
    
    for query in test_queries:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM opa_sections 
            WHERE section_text LIKE ? 
            AND document_id IN (
                SELECT document_id FROM opa_documents WHERE source_org = 'pho'
            )
        """, (f"%{query}%",))
        
        count = cursor.fetchone()[0]
        print(f"  Query: '{query}' - Found {count} sections")
    
    conn.close()
    
    print("\n✅ PHO SQLite population complete!")
    return True


def verify_database_schema():
    """Verify the database has the required tables."""
    conn = sqlite3.connect("data/processed/dr_opa/opa.db")
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('opa_documents', 'opa_sections')
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    if 'opa_documents' not in tables or 'opa_sections' not in tables:
        print("❌ Required tables not found. Creating...")
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opa_documents (
                document_id TEXT PRIMARY KEY,
                source_url TEXT,
                source_org TEXT,
                document_type TEXT,
                title TEXT,
                effective_date TEXT,
                updated_date TEXT,
                published_date TEXT,
                topics TEXT,
                policy_level TEXT,
                content_hash TEXT,
                metadata_json TEXT,
                is_superseded INTEGER DEFAULT 0,
                ingested_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opa_sections (
                section_id TEXT PRIMARY KEY,
                document_id TEXT,
                chunk_type TEXT,
                parent_id TEXT,
                section_heading TEXT,
                section_text TEXT,
                section_idx INTEGER,
                chunk_idx INTEGER,
                embedding_model TEXT,
                embedding_id TEXT,
                metadata_json TEXT,
                FOREIGN KEY (document_id) REFERENCES opa_documents(document_id)
            )
        """)
        
        conn.commit()
        print("✅ Tables created")
    else:
        print("✅ Database schema verified")
    
    conn.close()


def main():
    """Main entry point."""
    print("Starting PHO SQLite population...")
    
    # Verify schema first
    verify_database_schema()
    
    # Populate database
    success = populate_pho_sqlite()
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())