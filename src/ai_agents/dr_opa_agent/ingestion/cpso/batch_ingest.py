#!/usr/bin/env python3
"""
Batch ingestion script for CPSO documents into SQL and vector databases.

This script reads all extracted JSON documents and ingests them into:
1. SQLite database with proper document and section tracking
2. Chroma vector database with embeddings (if OpenAI API key available)
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import hashlib

from ..database import Database
from ..base_ingester import BaseOPAIngester

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BatchIngester(BaseOPAIngester):
    """Batch ingests multiple CPSO documents."""
    
    def __init__(self, db_path: str, chroma_path: str, openai_api_key: str = None):
        """Initialize batch ingester with database connections."""
        super().__init__(
            source_org='cpso',  # Default to CPSO for now
            db_path=db_path, 
            chroma_path=chroma_path, 
            openai_api_key=openai_api_key
        )
        self.db = Database(db_path)
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    def fetch_document(self, source_url: str) -> Dict[str, Any]:
        """Not used in batch mode - we read from files."""
        raise NotImplementedError("Batch ingester reads from files, not URLs")
    
    def ingest_document_file(self, json_path: str) -> bool:
        """
        Ingest a single document from its JSON file.
        
        Args:
            json_path: Path to the extracted document JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Skip chunk files
            if '_chunks' in json_path:
                return True
                
            logger.info(f"Ingesting: {os.path.basename(json_path)}")
            
            # Load document
            with open(json_path, 'r', encoding='utf-8') as f:
                document = json.load(f)
            
            # Convert extracted document to metadata format expected by BaseOPAIngester
            metadata = {
                'source_url': document.get('source_url', ''),
                'source_org': 'cpso',
                'title': document.get('title', 'Untitled'),
                'content_hash': document.get('content_hash', hashlib.md5(document['content'].encode()).hexdigest()),
                'effective_date': None,  # Extract from content if needed
                'updated_date': None,
                'published_date': document.get('extracted_at', datetime.now().isoformat()),
                'topics': self._extract_topics_from_document(document),
                'policy_level': 'expectation',  # Default for CPSO docs
                'document_type': document.get('document_type', 'policy'),
                'ingested_at': datetime.now().isoformat()
            }
            
            # Check if document already exists by content hash
            existing = self.db.execute_query(
                "SELECT document_id FROM opa_documents WHERE content_hash = ? LIMIT 1",
                (metadata['content_hash'],)
            )
            
            if existing:
                logger.debug(f"Document already exists: {metadata['title']}")
                self.stats['skipped'] += 1
                return True
            
            # Store document record using parent class method
            doc_id = self._store_document(metadata)
            
            # Use parent-child chunking from BaseOPAIngester
            full_content = document.get('content', '')
            if full_content.strip():
                # Create parent and child chunks using the base class method
                parent_chunks, child_chunks = self.create_parent_child_chunks(full_content, metadata)
                
                # Store chunks with embeddings using base class method
                all_chunks = parent_chunks + child_chunks
                stored_count = self.store_chunks_with_embeddings(all_chunks, doc_id)
                
                logger.info(f"✓ Ingested: {metadata['title']} ({stored_count} chunks, {len(parent_chunks)} parents, {len(child_chunks)} children)")
            else:
                logger.warning(f"No content found in document: {metadata['title']}")
            
            # Log ingestion
            self.db.execute_update("""
                INSERT INTO ingestion_log (
                    source_type, source_file, status, started_at,
                    completed_at, records_processed
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                'cpso_batch',
                json_path,
                'success',
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                1
            ))
            
            self.stats['success'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest {json_path}: {e}")
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'file': json_path,
                'error': str(e)
            })
            return False
    
    def _extract_topics_from_document(self, document: Dict[str, Any]) -> List[str]:
        """Extract topics from document content and metadata."""
        topics = []
        
        # Get content to analyze
        content = document.get('content', '')
        title = document.get('title', '')
        url = document.get('source_url', '')
        
        # Use the parent class method to extract topics
        full_text = f"{title}\n{content}"
        extracted_topics = self._extract_topics(full_text, url)
        
        return extracted_topics
    
    def ingest_directory(self, directory: str) -> Dict[str, Any]:
        """
        Ingest all JSON documents in a directory.
        
        Args:
            directory: Path to directory containing extracted JSON files
            
        Returns:
            Statistics about the ingestion
        """
        json_files = list(Path(directory).glob("*.json"))
        
        # Filter out chunk files and metadata files
        doc_files = [
            f for f in json_files 
            if not ('_chunks' in f.name or '_metadata' in f.name)
        ]
        
        logger.info(f"Found {len(doc_files)} documents to ingest")
        self.stats['total'] = len(doc_files)
        
        for json_file in doc_files:
            self.ingest_document_file(str(json_file))
        
        # Print summary
        logger.info("="*60)
        logger.info("INGESTION COMPLETE")
        logger.info(f"  Total documents: {self.stats['total']}")
        logger.info(f"  Successfully ingested: {self.stats['success']}")
        logger.info(f"  Failed: {self.stats['failed']}")
        logger.info(f"  Skipped (already exists): {self.stats['skipped']}")
        
        if self.stats['errors']:
            logger.info("\nErrors encountered:")
            for err in self.stats['errors'][:5]:
                logger.info(f"  - {err['file']}: {err['error']}")
            if len(self.stats['errors']) > 5:
                logger.info(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        return self.stats


def main():
    """Run batch ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch ingest CPSO documents')
    parser.add_argument('--input-dir', 
                       default='data/dr_opa_agent/processed/cpso',
                       help='Directory containing extracted JSON documents')
    parser.add_argument('--db-path',
                       default='data/dr_opa_agent/opa.db',
                       help='Path to SQLite database')
    parser.add_argument('--chroma-path',
                       default='data/dr_opa_agent/chroma',
                       help='Path to Chroma vector database')
    parser.add_argument('--openai-key',
                       help='OpenAI API key for embeddings (optional)')
    
    args = parser.parse_args()
    
    # Load OpenAI key from environment if not provided
    if not args.openai_key:
        args.openai_key = os.getenv('OPENAI_API_KEY')
    
    # Create ingester
    ingester = BatchIngester(
        db_path=args.db_path,
        chroma_path=args.chroma_path,
        openai_api_key=args.openai_key
    )
    
    # Run ingestion
    stats = ingester.ingest_directory(args.input_dir)
    
    # Save report
    report_path = os.path.join(
        os.path.dirname(args.input_dir),
        f"ingestion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(report_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()