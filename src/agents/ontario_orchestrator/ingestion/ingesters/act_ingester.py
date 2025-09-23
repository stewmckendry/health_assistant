#!/usr/bin/env python3
"""
Enhanced ingestion module for Health Insurance Act (Reg. 552) with text chunking.
Handles large sections by splitting them into smaller chunks for embeddings.
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import tiktoken

from extract_act_enhanced import EnhancedActExtractor

# Try to import from existing base ingester
try:
    from src.ingestion.base_ingester import BaseIngester
except ImportError:
    # Standalone version without base class
    BaseIngester = None
    
import chromadb
from chromadb.utils import embedding_functions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextChunker:
    """Utility class for chunking text for embeddings."""
    
    def __init__(self, max_tokens: int = 6000, overlap_tokens: int = 200):
        """
        Initialize text chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk (default 6000, leaving room for system tokens)
            overlap_tokens: Number of overlapping tokens between chunks
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.encoding_for_model("text-embedding-3-small")
    
    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Split text into chunks with metadata.
        
        Args:
            text: Text to chunk
            metadata: Base metadata to include with each chunk
            
        Returns:
            List of (chunk_text, chunk_metadata) tuples
        """
        # Tokenize the entire text
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        # If text fits in one chunk, return as-is
        if total_tokens <= self.max_tokens:
            return [(text, metadata)]
        
        chunks = []
        chunk_num = 1
        total_chunks = (total_tokens - self.overlap_tokens) // (self.max_tokens - self.overlap_tokens) + 1
        
        # Create chunks with overlap
        start = 0
        while start < total_tokens:
            end = min(start + self.max_tokens, total_tokens)
            
            # Get chunk tokens and decode
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk metadata
            chunk_metadata = metadata.copy()
            chunk_metadata['chunk_num'] = chunk_num
            chunk_metadata['total_chunks'] = total_chunks
            chunk_metadata['chunk_tokens'] = len(chunk_tokens)
            chunk_metadata['original_tokens'] = total_tokens
            
            chunks.append((chunk_text, chunk_metadata))
            
            # Move start position with overlap
            start += self.max_tokens - self.overlap_tokens
            chunk_num += 1
            
            # Prevent infinite loop
            if start > 0 and start >= total_tokens:
                break
        
        logger.info(f"Split {total_tokens} tokens into {len(chunks)} chunks")
        return chunks


class EnhancedActIngester:
    """Ingest Health Insurance Act sections into SQL and Chroma with chunking support."""
    
    def __init__(self, 
                 db_path: Optional[str] = None, 
                 chroma_path: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        """
        Initialize ingester with database connections.
        
        Args:
            db_path: Path to SQLite database
            chroma_path: Path to Chroma persistent storage
            openai_api_key: API key for embeddings
        """
        self.db_path = db_path or os.getenv('DB_PATH', 'data/ohip.db')
        self.chroma_path = chroma_path or os.getenv('CHROMA_PATH', '.chroma')
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
        # Initialize text chunker
        self.chunker = TextChunker(max_tokens=6000, overlap_tokens=200)
        
        # Initialize database
        self.db = None
        self._init_database()
        
        # Initialize Chroma
        self.chroma_client = None
        self.collection = None
        self._init_chroma()
        
        # Track ingestion stats
        self.stats = {
            'sections_processed': 0,
            'sql_records': 0,
            'chroma_embeddings': 0,
            'chunks_created': 0,
            'errors': []
        }
    
    def _init_database(self):
        """Initialize SQLite database and create tables if needed."""
        logger.info(f"Initializing database at {self.db_path}")
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        
        # Create Act-specific tables
        self._create_tables()
    
    def _create_tables(self):
        """Create normalized tables for Act rules."""
        cursor = self.db.cursor()
        
        # Eligibility and presence rules
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_eligibility_rule (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            title TEXT NOT NULL,
            condition_json TEXT NOT NULL,
            effect TEXT NOT NULL,
            max_duration_months INTEGER,
            prerequisites_json TEXT,
            notes TEXT,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, title)
        )
        """)
        
        # Health card rules
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_health_card_rule (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            title TEXT NOT NULL,
            requirement TEXT NOT NULL,
            verification_needed BOOLEAN,
            renewal_period_months INTEGER,
            notes TEXT,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, title)
        )
        """)
        
        # Dependant carryover rules
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_dependant_carryover (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            scenario TEXT NOT NULL,
            age_limit INTEGER,
            condition_json TEXT NOT NULL,
            duration_months INTEGER,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, scenario)
        )
        """)
        
        # Extended absence and status rules
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_status_extension (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            reason TEXT NOT NULL,
            max_duration_months INTEGER,
            requirements_json TEXT,
            approval_needed BOOLEAN,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, reason)
        )
        """)
        
        # Uninsured services references
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_uninsured_reference (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            category TEXT NOT NULL,
            service_description TEXT NOT NULL,
            exceptions_json TEXT,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, service_description)
        )
        """)
        
        # Ingestion log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_ingestion_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            status TEXT NOT NULL,
            sections_processed INTEGER,
            sql_records INTEGER,
            chroma_embeddings INTEGER,
            chunks_created INTEGER,
            error_count INTEGER,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            metadata_json TEXT
        )
        """)
        
        # Views for easier querying
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_act_eligibility AS
        SELECT 
            section_ref,
            title,
            json_extract(condition_json, '$.description') as condition_desc,
            effect,
            max_duration_months
        FROM act_eligibility_rule
        ORDER BY section_ref
        """)
        
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_act_all_rules AS
        SELECT 'eligibility' as rule_type, section_ref, title as description, line_range
        FROM act_eligibility_rule
        UNION ALL
        SELECT 'health_card', section_ref, title, line_range
        FROM act_health_card_rule
        UNION ALL
        SELECT 'dependant', section_ref, scenario, line_range
        FROM act_dependant_carryover
        UNION ALL
        SELECT 'status_extension', section_ref, reason, line_range
        FROM act_status_extension
        UNION ALL
        SELECT 'uninsured', section_ref, service_description, line_range
        FROM act_uninsured_reference
        ORDER BY section_ref
        """)
        
        self.db.commit()
        logger.info("Database tables created/verified")
    
    def _init_chroma(self):
        """Initialize Chroma client and collection."""
        logger.info(f"Initializing Chroma at {self.chroma_path}")
        
        # Initialize persistent client
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        
        # Create embedding function
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name="text-embedding-3-small"
        )
        
        # Get or create collection for Act documents
        self.collection = self.chroma_client.get_or_create_collection(
            name="act_documents",
            embedding_function=embedding_function,
            metadata={"description": "Health Insurance Act sections with chunking"}
        )
        
        # Get current document count
        current_count = self.collection.count()
        logger.info(f"Chroma collection initialized with {current_count} existing documents")
    
    async def ingest(self, act_file: str, extracted_sections: Optional[List[Dict]] = None, max_sections: Optional[int] = None):
        """
        Main ingestion pipeline.
        
        Args:
            act_file: Path to Act document
            extracted_sections: Pre-extracted sections (optional)
            max_sections: Limit sections for testing
        """
        start_time = datetime.now()
        
        try:
            self._log_ingestion(act_file, 'started', start_time)
            
            # Get sections - either pre-extracted or extract now
            if extracted_sections:
                # Handle different data formats
                if isinstance(extracted_sections, dict) and 'sections' in extracted_sections:
                    sections = extracted_sections['sections']
                else:
                    sections = extracted_sections
                sections = sections[:max_sections] if max_sections else sections
                logger.info(f"Using {len(sections)} pre-extracted sections")
            else:
                logger.info("Extracting sections from document")
                extractor = EnhancedActExtractor()
                sections = await extractor.extract_sections(act_file)
                sections = sections[:max_sections] if max_sections else sections
            
            logger.info(f"Processing {len(sections)} sections")
            self.stats['sections_processed'] = len(sections)
            
            # Process sections into SQL
            self._upsert_sql_records(sections)
            logger.info(f"Upserted {self.stats['sql_records']} SQL records")
            
            # Process sections into Chroma with chunking
            self._upsert_chroma_embeddings_chunked(sections)
            
            # Log completion
            end_time = datetime.now()
            self._log_ingestion(act_file, 'completed', start_time, end_time)
            
            logger.info(f"Ingestion complete: {self.stats}")
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            self.stats['errors'].append(str(e))
            self._log_ingestion(act_file, 'failed', start_time, datetime.now())
            raise
        
        finally:
            if self.db:
                self.db.close()
        
        return self.stats
    
    def _upsert_sql_records(self, sections: List[Dict]):
        """Upsert records to SQL tables based on extracted section data."""
        cursor = self.db.cursor()
        
        for section in sections:
            try:
                # Create a basic eligibility rule from the section data
                self._upsert_basic_eligibility_rule(cursor, section)
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Error processing section {section.get('section_ref', 'unknown')}: {e}")
                self.stats['errors'].append(f"SQL error in {section.get('section_ref', 'unknown')}: {e}")
                self.db.rollback()
    
    def _upsert_basic_eligibility_rule(self, cursor, section: Dict):
        """Create a basic eligibility rule from section data."""
        # Extract key fields
        section_ref = section.get('section_ref', '')
        title = section.get('title', '')
        effect = section.get('effect', '')
        
        # Create basic condition from available data
        condition = {
            'description': effect,
            'conditions': section.get('conditions', []),
            'durations': section.get('durations', {}),
            'prerequisites': section.get('prerequisites', {}),
            'actors': section.get('actors', [])
        }
        
        cursor.execute("""
        INSERT OR REPLACE INTO act_eligibility_rule
        (section_ref, title, condition_json, effect, max_duration_months, prerequisites_json, notes, line_range)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            section_ref,
            title,
            json.dumps(condition),
            effect,
            None,  # No max duration extracted
            json.dumps(section.get('prerequisites', {})) if section.get('prerequisites') else None,
            section.get('notes', ''),
            section.get('line_range', '')
        ))
        self.stats['sql_records'] += 1
    
    def _upsert_eligibility_rule(self, cursor, section: Dict, rule: Dict):
        """Upsert eligibility rule."""
        cursor.execute("""
        INSERT OR REPLACE INTO act_eligibility_rule
        (section_ref, title, condition_json, effect, max_duration_months, prerequisites_json, notes, line_range)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            section['section_ref'],
            rule.get('title', section.get('title', '')),
            json.dumps(rule.get('condition', {})),
            rule.get('effect', ''),
            rule.get('max_duration_months'),
            json.dumps(rule.get('prerequisites', [])) if rule.get('prerequisites') else None,
            rule.get('notes'),
            section.get('line_range')
        ))
        self.stats['sql_records'] += 1
    
    def _upsert_health_card_rule(self, cursor, section: Dict, rule: Dict):
        """Upsert health card rule."""
        cursor.execute("""
        INSERT OR REPLACE INTO act_health_card_rule
        (section_ref, title, requirement, verification_needed, renewal_period_months, notes, line_range)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            section['section_ref'],
            rule.get('title', section.get('title', '')),
            rule.get('requirement', ''),
            rule.get('verification_needed', False),
            rule.get('renewal_period_months'),
            rule.get('notes'),
            section.get('line_range')
        ))
        self.stats['sql_records'] += 1
    
    def _upsert_dependant_carryover(self, cursor, section: Dict, rule: Dict):
        """Upsert dependant carryover rule."""
        cursor.execute("""
        INSERT OR REPLACE INTO act_dependant_carryover
        (section_ref, scenario, age_limit, condition_json, duration_months, line_range)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            section['section_ref'],
            rule.get('scenario', ''),
            rule.get('age_limit'),
            json.dumps(rule.get('condition', {})),
            rule.get('duration_months'),
            section.get('line_range')
        ))
        self.stats['sql_records'] += 1
    
    def _upsert_status_extension(self, cursor, section: Dict, rule: Dict):
        """Upsert status extension rule."""
        cursor.execute("""
        INSERT OR REPLACE INTO act_status_extension
        (section_ref, reason, max_duration_months, requirements_json, approval_needed, line_range)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            section['section_ref'],
            rule.get('reason', ''),
            rule.get('max_duration_months'),
            json.dumps(rule.get('requirements', [])) if rule.get('requirements') else None,
            rule.get('approval_needed', False),
            section.get('line_range')
        ))
        self.stats['sql_records'] += 1
    
    def _upsert_uninsured_reference(self, cursor, section: Dict, rule: Dict):
        """Upsert uninsured service reference."""
        cursor.execute("""
        INSERT OR REPLACE INTO act_uninsured_reference
        (section_ref, category, service_description, exceptions_json, line_range)
        VALUES (?, ?, ?, ?, ?)
        """, (
            section['section_ref'],
            rule.get('category', 'general'),
            rule.get('service_description', ''),
            json.dumps(rule.get('exceptions', [])) if rule.get('exceptions') else None,
            section.get('line_range')
        ))
        self.stats['sql_records'] += 1
    
    def _upsert_chroma_embeddings_chunked(self, sections: List[Dict]):
        """Upsert section embeddings to Chroma with chunking for large sections."""
        if not sections:
            return
        
        # Collect all chunks
        all_chunks = []
        
        for section in sections:
            # Prepare base metadata
            base_metadata = {
                'source': 'act',
                'section_ref': section['section_ref'],
                'title': section.get('title', ''),
                'line_range': section.get('line_range', ''),
                'incomplete': section.get('incomplete', False)
            }
            
            # Add topics as comma-separated string
            if section.get('topics'):
                base_metadata['topics'] = ','.join(section['topics'])
            
            # Add effect if present
            if section.get('effect'):
                base_metadata['effect'] = section['effect'][:500]  # Limit length
            
            # Chunk the text
            chunks = self.chunker.chunk_text(section['raw_text'], base_metadata)
            
            # Create chunk records
            for i, (chunk_text, chunk_metadata) in enumerate(chunks):
                # Create stable ID including chunk number
                chunk_num = chunk_metadata.get('chunk_num', i + 1)
                chunk_id = f"act::{section['section_ref']}::chunk{chunk_num}::{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}"
                
                all_chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
            
            self.stats['chunks_created'] += len(chunks)
        
        # Batch upsert all chunks
        batch_size = 50  # Smaller batch size since chunks are larger
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i+batch_size]
            
            ids = [c['id'] for c in batch]
            texts = [c['text'] for c in batch]
            metadatas = [c['metadata'] for c in batch]
            
            try:
                self.collection.upsert(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas
                )
                self.stats['chroma_embeddings'] += len(ids)
                logger.info(f"Upserted batch of {len(ids)} embeddings")
                
            except Exception as e:
                logger.error(f"Failed to upsert Chroma batch: {e}")
                self.stats['errors'].append(f"Chroma error: {e}")
        
        logger.info(f"Total embeddings upserted: {self.stats['chroma_embeddings']}")
        logger.info(f"Total chunks created: {self.stats['chunks_created']}")
    
    def _log_ingestion(self, source_file: str, status: str, start_time: datetime, end_time: Optional[datetime] = None):
        """Log ingestion to database."""
        cursor = self.db.cursor()
        
        cursor.execute("""
        INSERT INTO act_ingestion_log
        (source_file, status, sections_processed, sql_records, chroma_embeddings, chunks_created, error_count, started_at, completed_at, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_file,
            status,
            self.stats['sections_processed'],
            self.stats['sql_records'],
            self.stats['chroma_embeddings'],
            self.stats['chunks_created'],
            len(self.stats['errors']),
            start_time.isoformat(),
            end_time.isoformat() if end_time else None,
            json.dumps({'errors': self.stats['errors'][:10]})  # Keep first 10 errors
        ))
        
        self.db.commit()
        logger.info(f"Logged ingestion: {status}")


async def main():
    """CLI interface for ingestion."""
    import argparse
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Ingest Health Insurance Act into SQL and Chroma with chunking')
    parser.add_argument('--db', default='data/ohip.db', help='SQLite database path')
    parser.add_argument('--chroma', default='.chroma', help='Chroma storage path')
    parser.add_argument('--act-file', required=True, help='Path to act document')
    parser.add_argument('--extracted', help='Pre-extracted JSON file')
    parser.add_argument('--max-sections', type=int, help='Limit sections for testing')
    
    args = parser.parse_args()
    
    # Load pre-extracted data if provided
    extracted_sections = None
    if args.extracted:
        logger.info(f"Loading pre-extracted data from {args.extracted}")
        with open(args.extracted, 'r') as f:
            extracted_sections = json.load(f)
    
    # Run ingestion
    ingester = EnhancedActIngester(
        db_path=args.db,
        chroma_path=args.chroma,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    stats = await ingester.ingest(
        act_file=args.act_file,
        extracted_sections=extracted_sections,
        max_sections=args.max_sections
    )
    
    print(f"Ingestion complete: {json.dumps(stats, indent=2)}")
    return stats


if __name__ == "__main__":
    asyncio.run(main())