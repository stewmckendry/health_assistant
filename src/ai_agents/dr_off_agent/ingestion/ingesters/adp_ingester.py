#!/usr/bin/env python3
"""
Enhanced ADP (Assistive Devices Program) Ingestion Pipeline
Ingests extracted ADP sections into SQLite/Postgres and Chroma vector database
"""

import os
import sys
import json
import sqlite3
import hashlib
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("Installing chromadb...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'chromadb'])
    import chromadb
    from chromadb.utils import embedding_functions

from ..extractors.adp_extractor import EnhancedADPExtractor, ADPSection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedADPIngester:
    """Ingest ADP sections into SQL database and Chroma vector store"""
    
    def __init__(self, 
                 db_path: str = "data/ohip.db",
                 chroma_path: str = ".chroma",
                 collection_name: str = "adp_v1"):
        """Initialize ingester with database and Chroma connections"""
        
        # Setup SQLite database
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Initialize schema if needed
        self._init_schema()
        
        # Setup Chroma
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        
        # Use OpenAI embeddings if available, else default
        try:
            import openai
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if openai_api_key:
                embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=openai_api_key,
                    model_name="text-embedding-3-small"
                )
                logger.info("Using OpenAI embeddings")
            else:
                embedding_fn = embedding_functions.DefaultEmbeddingFunction()
                logger.info("Using default embeddings (OpenAI key not found)")
        except Exception as e:
            embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            logger.info(f"Using default embeddings: {e}")
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(
                name=collection_name,
                embedding_function=embedding_fn
            )
            logger.info(f"Using existing collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {collection_name}")
    
    def _init_schema(self):
        """Initialize database schema from migration file"""
        migration_file = Path(__file__).parent / "migrate_adp.sql"
        
        if migration_file.exists():
            logger.info(f"Running migration from {migration_file}")
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
                self.cursor.executescript(migration_sql)
        else:
            logger.warning(f"Migration file not found: {migration_file}")
            # Create tables directly
            self._create_tables_directly()
        
        self.conn.commit()
    
    def _create_tables_directly(self):
        """Create tables directly if migration file not found"""
        # Client share & CEP leasing table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS adp_funding_rule (
              rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
              adp_doc TEXT NOT NULL,
              section_ref TEXT,
              scenario TEXT NOT NULL,
              client_share_percent DECIMAL(5,2),
              details TEXT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(adp_doc, section_ref, scenario)
            )
        """)
        
        # Exclusions table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS adp_exclusion (
              exclusion_id INTEGER PRIMARY KEY AUTOINCREMENT,
              adp_doc TEXT NOT NULL,
              section_ref TEXT,
              phrase TEXT NOT NULL,
              applies_to TEXT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(adp_doc, phrase, COALESCE(section_ref, ''))
            )
        """)
        
        # Create indexes
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_adp_funding_rule_doc 
            ON adp_funding_rule(adp_doc, scenario)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_adp_exclusion_phrase 
            ON adp_exclusion(phrase)
        """)
        
        logger.info("Created ADP tables directly")
    
    def hash_text(self, text: str) -> str:
        """Generate stable hash for text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
    
    def upsert_funding_rules(self, section: ADPSection):
        """Upsert funding rules to database"""
        for rule in section.funding:
            try:
                self.cursor.execute("""
                    INSERT OR REPLACE INTO adp_funding_rule 
                    (adp_doc, section_ref, scenario, client_share_percent, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    section.adp_doc,
                    section.section_id,
                    rule['scenario'],
                    rule.get('client_share_percent'),
                    rule.get('details', '')
                ))
            except sqlite3.IntegrityError as e:
                logger.warning(f"Duplicate funding rule skipped: {e}")
            except Exception as e:
                logger.error(f"Error inserting funding rule: {e}")
    
    def upsert_exclusions(self, section: ADPSection):
        """Upsert exclusions to database"""
        for exclusion in section.exclusions:
            try:
                self.cursor.execute("""
                    INSERT OR REPLACE INTO adp_exclusion
                    (adp_doc, section_ref, phrase, applies_to)
                    VALUES (?, ?, ?, ?)
                """, (
                    section.adp_doc,
                    section.section_id,
                    exclusion['phrase'],
                    exclusion.get('applies_to')
                ))
            except sqlite3.IntegrityError as e:
                logger.warning(f"Duplicate exclusion skipped: {e}")
            except Exception as e:
                logger.error(f"Error inserting exclusion: {e}")
    
    def upsert_embedding(self, section: ADPSection):
        """Upsert section to Chroma vector store"""
        # Create unique ID
        doc_id = f"{section.policy_uid}::{self.hash_text(section.raw_text)}"
        
        # Prepare metadata
        metadata = {
            "adp_doc": section.adp_doc,
            "part": section.part or "",
            "section_id": section.section_id,
            "title": section.title,
            "policy_uid": section.policy_uid,
            "topics": json.dumps(section.topics),  # Store as JSON string
            "page_num": section.page_num or 0,
            "funding_count": len(section.funding),
            "exclusion_count": len(section.exclusions)
        }
        
        # Upsert to Chroma
        try:
            self.collection.upsert(
                ids=[doc_id],
                documents=[section.raw_text],
                metadatas=[metadata]
            )
        except Exception as e:
            logger.error(f"Error upserting to Chroma: {e}")
    
    def ingest_section(self, section: ADPSection):
        """Ingest a single section to both SQL and Chroma"""
        # SQL ingestion
        self.upsert_funding_rules(section)
        self.upsert_exclusions(section)
        
        # Vector store ingestion
        self.upsert_embedding(section)
    
    def ingest_json(self, json_path: str) -> int:
        """Ingest ADP sections from extracted JSON file"""
        logger.info(f"Loading extracted data from {json_path}")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        sections_data = data.get('sections', [])
        
        # Convert JSON data back to ADPSection objects
        for i, section_dict in enumerate(sections_data):
            # Create ADPSection from dictionary
            from ..extractors.adp_extractor import ADPSection
            section = ADPSection(
                adp_doc=section_dict['adp_doc'],
                part=section_dict.get('part'),
                section_id=section_dict['section_id'],
                title=section_dict['title'],
                raw_text=section_dict.get('raw_text', ''),
                policy_uid=section_dict['policy_uid'],
                topics=section_dict.get('topics', []),
                funding=section_dict.get('funding', []),
                exclusions=section_dict.get('exclusions', []),
                page_num=section_dict.get('page_num')
            )
            
            self.ingest_section(section)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Ingested {i + 1}/{len(sections_data)} sections")
                self.conn.commit()  # Commit periodically
        
        # Final commit
        self.conn.commit()
        
        logger.info(f"Successfully ingested {len(sections_data)} sections from JSON")
        return len(sections_data)
    
    def ingest_file(self, pdf_path: str, doc_type: Optional[str] = None) -> int:
        """Extract and ingest a single ADP PDF"""
        logger.info(f"Processing {pdf_path}")
        
        # Extract sections
        extractor = EnhancedADPExtractor()
        sections = extractor.extract(pdf_path, doc_type)
        
        # Ingest each section
        for i, section in enumerate(sections):
            self.ingest_section(section)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Ingested {i + 1}/{len(sections)} sections")
                self.conn.commit()  # Commit periodically
        
        # Final commit
        self.conn.commit()
        
        logger.info(f"Successfully ingested {len(sections)} sections from {pdf_path}")
        return len(sections)
    
    def ingest_multiple(self, pdf_paths: List[str]) -> Dict[str, int]:
        """Ingest multiple ADP PDFs"""
        results = {}
        
        for path in pdf_paths:
            try:
                count = self.ingest_file(path)
                results[path] = count
            except Exception as e:
                logger.error(f"Failed to ingest {path}: {e}")
                results[path] = -1
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        stats = {}
        
        # SQL stats
        self.cursor.execute("SELECT COUNT(*) FROM adp_funding_rule")
        stats['funding_rules'] = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM adp_exclusion")
        stats['exclusions'] = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(DISTINCT adp_doc) FROM adp_funding_rule")
        stats['unique_docs'] = self.cursor.fetchone()[0]
        
        # Chroma stats
        try:
            stats['embeddings'] = self.collection.count()
        except:
            stats['embeddings'] = 0
        
        return stats
    
    def search_embeddings(self, query: str, n_results: int = 5) -> List[Dict]:
        """Test search functionality"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results['metadatas'] else {}
                formatted_results.append({
                    'text': doc[:200] + '...',
                    'section': meta.get('section_id'),
                    'title': meta.get('title'),
                    'topics': json.loads(meta.get('topics', '[]')),
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
        
        return formatted_results
    
    def close(self):
        """Close database connections"""
        self.conn.close()

def main():
    parser = argparse.ArgumentParser(description='Ingest ADP PDFs to database and vector store')
    parser.add_argument('docs', nargs='+', help='PDF files to ingest')
    parser.add_argument('--db', default='data/ohip.db', help='Database path')
    parser.add_argument('--chroma', default='.chroma', help='Chroma persist directory')
    parser.add_argument('--collection', default='adp_v1', help='Chroma collection name')
    parser.add_argument('--test-search', type=str, help='Test search query after ingestion')
    parser.add_argument('--stats', action='store_true', help='Show statistics after ingestion')
    
    args = parser.parse_args()
    
    # Initialize ingester
    ingester = EnhancedADPIngester(
        db_path=args.db,
        chroma_path=args.chroma,
        collection_name=args.collection
    )
    
    # Process files
    results = ingester.ingest_multiple(args.docs)
    
    # Show results
    print("\nIngestion Results:")
    for path, count in results.items():
        status = "✓" if count >= 0 else "✗"
        print(f"  {status} {Path(path).name}: {count} sections")
    
    # Show stats if requested
    if args.stats:
        stats = ingester.get_stats()
        print("\nDatabase Statistics:")
        print(f"  Funding rules: {stats['funding_rules']}")
        print(f"  Exclusions: {stats['exclusions']}")
        print(f"  Unique documents: {stats['unique_docs']}")
        print(f"  Embeddings: {stats['embeddings']}")
    
    # Test search if requested
    if args.test_search:
        print(f"\nSearch results for '{args.test_search}':")
        results = ingester.search_embeddings(args.test_search)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Section {result['section']}: {result['title']}")
            print(f"   Topics: {', '.join(result['topics'])}")
            print(f"   Distance: {result['distance']:.3f}" if result['distance'] else "")
            print(f"   Text: {result['text']}")
    
    # Clean up
    ingester.close()

if __name__ == "__main__":
    main()