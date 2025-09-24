"""Base ingester class for Dr. OPA data sources."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Tuple
import hashlib
import json
from datetime import datetime
import sqlite3
import re
from urllib.parse import urlparse

import chromadb
from chromadb.config import Settings
import openai
from tqdm import tqdm

from .database import Database

logger = logging.getLogger(__name__)


class BaseOPAIngester(ABC):
    """Abstract base class for OPA guidance document ingestion.
    
    Provides common functionality for:
    - HTML/PDF document processing
    - Parent-child chunking strategy
    - Metadata extraction (dates, organization, topic)
    - Embedding generation
    - Vector store management with Chroma
    - Supersession tracking
    """
    
    # Chunking parameters for parent-child strategy
    PARENT_CHUNK_SIZE = 2500  # tokens (approx 10000 chars)
    CHILD_CHUNK_SIZE = 500    # tokens (approx 2000 chars)
    CHUNK_OVERLAP = 100        # tokens (approx 400 chars)
    
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_BATCH_SIZE = 100
    
    # Control token templates for enhanced retrieval
    CONTROL_TOKEN_TEMPLATE = "[ORG={org}] [TOPIC={topic}] [DATE={date}] [TYPE={doc_type}]"
    
    def __init__(
        self,
        source_org: str,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize OPA ingester.
        
        Args:
            source_org: Source organization ('cpso', 'ontario_health', 'cep', 'pho', 'moh')
            db_path: Path to SQLite database
            chroma_path: Path to Chroma vector store
            openai_api_key: OpenAI API key for embeddings
        """
        self.source_org = source_org
        self.db = Database(db_path)
        
        # Set up Chroma
        if chroma_path is None:
            chroma_path = "data/processed/dr_opa/chroma"
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection for OPA corpus
        collection_name = f"opa_{source_org}_corpus"
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Using existing Chroma collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"source": "dr_opa", "organization": source_org}
            )
            logger.info(f"Created new Chroma collection: {collection_name}")
        
        # Set up OpenAI client for embeddings
        if openai_api_key:
            openai.api_key = openai_api_key
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
        else:
            self.openai_client = None
            logger.warning("No OpenAI API key provided - embeddings will be skipped")
        
        self.ingestion_stats = {
            'documents_processed': 0,
            'documents_failed': 0,
            'sections_created': 0,
            'chunks_created': 0,
            'embeddings_created': 0,
            'superseded_documents': 0,
            'errors': []
        }
    
    @abstractmethod
    def fetch_document(self, url: str) -> Tuple[str, str]:
        """Fetch and normalize document from URL.
        
        Must be implemented by subclasses for HTML/PDF handling.
        
        Args:
            url: Document URL
            
        Returns:
            Tuple of (normalized_text, document_format)
        """
        pass
    
    def extract_metadata(self, text: str, url: str) -> Dict[str, Any]:
        """Extract metadata from document text.
        
        Args:
            text: Document text
            url: Source URL
            
        Returns:
            Metadata dictionary with title, dates, topics, etc.
        """
        metadata = {
            'source_url': url,
            'source_org': self.source_org,
            'ingested_at': datetime.now().isoformat()
        }
        
        # Extract title (first heading or first line)
        title_match = re.search(r'^#?\s*(.+?)(?:\n|$)', text, re.MULTILINE)
        metadata['title'] = title_match.group(1).strip() if title_match else 'Untitled'
        
        # Extract dates
        metadata['effective_date'] = self._extract_effective_date(text)
        metadata['updated_date'] = self._extract_updated_date(text)
        metadata['published_date'] = self._extract_published_date(text)
        
        # Extract topics and tags
        metadata['topics'] = self._extract_topics(text, url)
        metadata['policy_level'] = self._extract_policy_level(text)
        metadata['document_type'] = self._infer_document_type(url, text)
        
        # Generate content hash for deduplication
        metadata['content_hash'] = hashlib.sha256(text.encode()).hexdigest()
        
        return metadata
    
    def _extract_effective_date(self, text: str) -> Optional[str]:
        """Extract effective date from text."""
        patterns = [
            r'[Ee]ffective\s+(?:date|from|as\s+of)[:\s]+(\w+\s+\d{1,2},?\s+\d{4})',
            r'[Ee]ffective[:\s]+(\d{4}-\d{2}-\d{2})',
            r'[Ii]n\s+effect\s+(?:from|as\s+of)[:\s]+(\w+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._normalize_date(match.group(1))
        
        return None
    
    def _extract_updated_date(self, text: str) -> Optional[str]:
        """Extract last updated date from text."""
        patterns = [
            r'[Ll]ast\s+[Uu]pdated[:\s]+(\w+\s+\d{1,2},?\s+\d{4})',
            r'[Uu]pdated[:\s]+(\d{4}-\d{2}-\d{2})',
            r'[Rr]evised[:\s]+(\w+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._normalize_date(match.group(1))
        
        return None
    
    def _extract_published_date(self, text: str) -> Optional[str]:
        """Extract publication date from text."""
        patterns = [
            r'[Pp]ublished[:\s]+(\w+\s+\d{1,2},?\s+\d{4})',
            r'[Dd]ate\s+[Pp]ublished[:\s]+(\d{4}-\d{2}-\d{2})',
            r'[Ii]ssued[:\s]+(\w+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._normalize_date(match.group(1))
        
        return None
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to ISO format."""
        # Simplified - in production use dateutil.parser
        return date_str
    
    def _extract_topics(self, text: str, url: str) -> List[str]:
        """Extract topics from document text and URL."""
        topics = []
        
        # Common Ontario health topics to detect
        topic_keywords = {
            'cervical_screening': ['cervical', 'hpv', 'pap', 'screening'],
            'ipac': ['infection', 'prevention', 'control', 'ipac'],
            'privacy': ['privacy', 'confidentiality', 'disclosure', 'consent'],
            'continuity_care': ['continuity', 'transfer', 'referral'],
            'digital_health': ['ehr', 'emr', 'olis', 'hrm', 'digital'],
            'prescribing': ['prescrib', 'medication', 'drug', 'opioid'],
            'documentation': ['document', 'record', 'chart'],
            'billing': ['bill', 'ohip', 'fee', 'claim']
        }
        
        text_lower = text.lower()
        url_lower = url.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower or kw in url_lower for kw in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_policy_level(self, text: str) -> Optional[str]:
        """Extract CPSO policy level (expectation vs advice)."""
        if self.source_org != 'cpso':
            return None
        
        # CPSO uses specific language for expectations vs advice
        if re.search(r'\bmust\b|\bshall\b|\brequired\b', text, re.IGNORECASE):
            return 'expectation'
        elif re.search(r'\bshould\b|\badvised\b|\brecommended\b', text, re.IGNORECASE):
            return 'advice'
        
        return 'general'
    
    def _infer_document_type(self, url: str, text: str) -> str:
        """Infer document type from URL and content."""
        url_lower = url.lower()
        
        if 'policy' in url_lower or 'policies' in url_lower:
            return 'policy'
        elif 'guideline' in url_lower:
            return 'guideline'
        elif 'tool' in url_lower or 'algorithm' in url_lower:
            return 'clinical_tool'
        elif 'bulletin' in url_lower or 'infobulletin' in url_lower:
            return 'bulletin'
        elif 'advice' in url_lower:
            return 'advice'
        else:
            return 'guidance'
    
    def create_parent_child_chunks(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Create parent and child chunks with hierarchical structure.
        
        Args:
            text: Document text
            metadata: Document metadata
            
        Returns:
            Tuple of (parent_chunks, child_chunks)
        """
        # Split into sections first
        sections = self._split_into_sections(text)
        
        parent_chunks = []
        child_chunks = []
        
        for section_idx, section in enumerate(sections):
            # Create parent chunk for section
            parent_id = self._generate_chunk_id(section['text'], f"parent_{section_idx}")
            
            # Add control tokens to parent
            control_tokens = self.CONTROL_TOKEN_TEMPLATE.format(
                org=metadata['source_org'],
                topic=','.join(metadata.get('topics', [])),
                date=metadata.get('effective_date', 'unknown'),
                doc_type=metadata.get('document_type', 'guidance')
            )
            
            parent_text = f"{control_tokens}\n{section['heading']}\n{section['text']}"
            
            parent_chunk = {
                'chunk_id': parent_id,
                'text': parent_text[:self.PARENT_CHUNK_SIZE * 4],  # Approx char limit
                'chunk_type': 'parent',
                'section_idx': section_idx,
                'section_heading': section['heading'],
                'metadata': {**metadata, 'chunk_type': 'parent'}
            }
            parent_chunks.append(parent_chunk)
            
            # Create child chunks from section content
            section_children = self._create_child_chunks(
                section['text'],
                parent_id,
                section_idx,
                section['heading'],
                metadata
            )
            child_chunks.extend(section_children)
        
        return parent_chunks, child_chunks
    
    def _split_into_sections(self, text: str) -> List[Dict[str, str]]:
        """Split document into logical sections."""
        # Look for markdown-style headings or numbered sections
        section_pattern = r'^(?:#{1,3}\s+(.+?)$|^(\d+\.?\s+.+?)$)'
        
        sections = []
        current_section = {'heading': 'Introduction', 'text': ''}
        
        for line in text.split('\n'):
            heading_match = re.match(section_pattern, line, re.MULTILINE)
            if heading_match:
                # Save previous section if it has content
                if current_section['text'].strip():
                    sections.append(current_section)
                # Start new section
                heading = heading_match.group(1) or heading_match.group(2)
                current_section = {'heading': heading, 'text': ''}
            else:
                current_section['text'] += line + '\n'
        
        # Don't forget the last section
        if current_section['text'].strip():
            sections.append(current_section)
        
        # If no sections found, treat whole doc as one section
        if not sections:
            sections = [{'heading': 'Full Document', 'text': text}]
        
        return sections
    
    def _create_child_chunks(
        self,
        text: str,
        parent_id: str,
        section_idx: int,
        section_heading: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create child chunks from section text."""
        child_chunks = []
        
        # Character-based chunking with overlap
        char_size = self.CHILD_CHUNK_SIZE * 4  # Approximate chars per token
        char_overlap = self.CHUNK_OVERLAP * 4
        
        start = 0
        chunk_idx = 0
        
        while start < len(text):
            end = min(start + char_size, len(text))
            
            # Try to break at paragraph or sentence boundary
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind('\n\n', start, end)
                if para_break > start + char_size // 2:
                    end = para_break
                else:
                    # Look for sentence break
                    sent_break = text.rfind('. ', start, end)
                    if sent_break > start + char_size // 2:
                        end = sent_break + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                child_id = self._generate_chunk_id(chunk_text, f"child_{section_idx}_{chunk_idx}")
                
                child_chunk = {
                    'chunk_id': child_id,
                    'parent_id': parent_id,
                    'text': chunk_text,
                    'chunk_type': 'child',
                    'section_idx': section_idx,
                    'section_heading': section_heading,
                    'chunk_idx': chunk_idx,
                    'metadata': {**metadata, 'chunk_type': 'child', 'parent_id': parent_id}
                }
                child_chunks.append(child_chunk)
                chunk_idx += 1
            
            start = end - char_overlap if end < len(text) else end
        
        return child_chunks
    
    def check_and_mark_superseded(
        self,
        topic: str,
        effective_date: str,
        current_doc_id: str
    ) -> int:
        """Check for and mark superseded documents.
        
        Args:
            topic: Document topic
            effective_date: Effective date of new document
            current_doc_id: ID of current document
            
        Returns:
            Number of documents marked as superseded
        """
        if not effective_date or not topic:
            return 0
        
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Find older documents on same topic
        cursor.execute("""
            SELECT document_id, title, effective_date
            FROM opa_documents
            WHERE topic = ? 
              AND effective_date < ?
              AND document_id != ?
              AND is_superseded = 0
        """, (topic, effective_date, current_doc_id))
        
        older_docs = cursor.fetchall()
        superseded_count = 0
        
        for doc in older_docs:
            # Mark as superseded
            cursor.execute("""
                UPDATE opa_documents
                SET is_superseded = 1,
                    superseded_by = ?,
                    superseded_date = ?
                WHERE document_id = ?
            """, (current_doc_id, datetime.now().isoformat(), doc[0]))
            
            logger.info(f"Marked document {doc[0]} ({doc[1]}) as superseded by {current_doc_id}")
            superseded_count += 1
        
        conn.commit()
        self.ingestion_stats['superseded_documents'] = superseded_count
        
        return superseded_count
    
    def ingest(self, source_urls: List[str]) -> Dict[str, Any]:
        """Ingest documents from source URLs.
        
        Args:
            source_urls: List of document URLs to ingest
            
        Returns:
            Dictionary with ingestion statistics
        """
        for url in tqdm(source_urls, desc=f"Ingesting {self.source_org} documents"):
            try:
                # Log start
                self.log_ingestion(url, 'started')
                
                # Fetch and normalize document
                text, doc_format = self.fetch_document(url)
                
                # Extract metadata
                metadata = self.extract_metadata(text, url)
                
                # Store document record
                doc_id = self._store_document(metadata)
                
                # Create parent-child chunks
                parent_chunks, child_chunks = self.create_parent_child_chunks(text, metadata)
                
                # Generate embeddings and store
                all_chunks = parent_chunks + child_chunks
                self.store_chunks_with_embeddings(all_chunks, doc_id)
                
                # Check for superseded documents
                if metadata.get('topics'):
                    for topic in metadata['topics']:
                        self.check_and_mark_superseded(
                            topic,
                            metadata.get('effective_date'),
                            doc_id
                        )
                
                self.ingestion_stats['documents_processed'] += 1
                
                # Log completion
                self.log_ingestion(url, 'completed')
                
            except Exception as e:
                logger.error(f"Error ingesting {url}: {e}")
                self.ingestion_stats['documents_failed'] += 1
                self.ingestion_stats['errors'].append(str(e))
                self.log_ingestion(url, 'failed', str(e))
        
        return self.ingestion_stats
    
    def _store_document(self, metadata: Dict[str, Any]) -> str:
        """Store document record in database."""
        conn = self.db.connect()
        cursor = conn.cursor()
        
        doc_id = hashlib.sha256(metadata['source_url'].encode()).hexdigest()[:16]
        
        cursor.execute("""
            INSERT OR REPLACE INTO opa_documents (
                document_id, source_org, source_url, title,
                document_type, effective_date, updated_date, published_date,
                topics, policy_level, content_hash, metadata_json,
                is_superseded, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id,
            metadata['source_org'],
            metadata['source_url'],
            metadata['title'],
            metadata.get('document_type'),
            metadata.get('effective_date'),
            metadata.get('updated_date'),
            metadata.get('published_date'),
            json.dumps(metadata.get('topics', [])),
            metadata.get('policy_level'),
            metadata['content_hash'],
            json.dumps(metadata),
            False,
            metadata['ingested_at']
        ))
        
        conn.commit()
        return doc_id
    
    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        if not self.openai_client:
            logger.warning("No OpenAI client - returning empty embeddings")
            return [[0.0] * 1536 for _ in texts]
        
        if batch_size is None:
            batch_size = self.EMBEDDING_BATCH_SIZE
        
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.openai_client.embeddings.create(
                    input=batch,
                    model=self.EMBEDDING_MODEL
                )
                batch_embeddings = [e.embedding for e in response.data]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                embeddings.extend([[0.0] * 1536 for _ in batch])
        
        return embeddings
    
    def store_chunks_with_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str
    ) -> int:
        """Store chunks in database and vector store."""
        if not chunks:
            return 0
        
        # Prepare texts for embedding
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.generate_embeddings(texts)
        
        # Store in database
        conn = self.db.connect()
        cursor = conn.cursor()
        
        stored_count = 0
        for chunk, embedding in zip(chunks, embeddings):
            try:
                # Store in database
                cursor.execute("""
                    INSERT INTO opa_sections (
                        section_id, document_id, chunk_type, parent_id,
                        section_heading, section_text, section_idx, chunk_idx,
                        embedding_model, embedding_id, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk['chunk_id'],
                    document_id,
                    chunk['chunk_type'],
                    chunk.get('parent_id'),
                    chunk.get('section_heading'),
                    chunk['text'],
                    chunk.get('section_idx'),
                    chunk.get('chunk_idx'),
                    self.EMBEDDING_MODEL if self.openai_client else None,
                    chunk['chunk_id'],
                    json.dumps(chunk['metadata'])
                ))
                
                # Store in Chroma if we have real embeddings
                if self.openai_client and not all(v == 0.0 for v in embedding):
                    # Prepare metadata for Chroma (convert lists to strings)
                    chroma_metadata = {}
                    for key, value in chunk['metadata'].items():
                        if isinstance(value, list):
                            chroma_metadata[key] = ','.join(map(str, value))
                        elif value is None:
                            chroma_metadata[key] = ''
                        else:
                            chroma_metadata[key] = str(value)
                    
                    self.collection.add(
                        ids=[chunk['chunk_id']],
                        embeddings=[embedding],
                        documents=[chunk['text']],
                        metadatas=[chroma_metadata]
                    )
                
                stored_count += 1
                
                if chunk['chunk_type'] == 'parent':
                    self.ingestion_stats['sections_created'] += 1
                else:
                    self.ingestion_stats['chunks_created'] += 1
                
            except Exception as e:
                logger.error(f"Error storing chunk {chunk['chunk_id']}: {e}")
                self.ingestion_stats['errors'].append(str(e))
        
        conn.commit()
        self.ingestion_stats['embeddings_created'] += stored_count
        
        return stored_count
    
    def log_ingestion(
        self,
        source_url: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """Log ingestion progress to database."""
        conn = self.db.connect()
        cursor = conn.cursor()
        
        if status == 'started':
            cursor.execute("""
                INSERT INTO ingestion_log (
                    source_type, source_file, status, started_at
                ) VALUES (?, ?, ?, ?)
            """, (f"opa_{self.source_org}", source_url, status, datetime.now()))
            
        else:  # completed or failed
            cursor.execute("""
                UPDATE ingestion_log 
                SET status = ?, 
                    records_processed = ?,
                    records_failed = ?,
                    error_message = ?,
                    completed_at = ?
                WHERE source_type = ? 
                    AND source_file = ?
                    AND status = 'started'
                ORDER BY started_at DESC
                LIMIT 1
            """, (
                status,
                self.ingestion_stats['documents_processed'],
                self.ingestion_stats['documents_failed'],
                error_message,
                datetime.now(),
                f"opa_{self.source_org}",
                source_url
            ))
        
        conn.commit()
    
    def _generate_chunk_id(self, text: str, suffix: str) -> str:
        """Generate unique ID for chunk."""
        content = f"{self.source_org}_{suffix}_{text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.db.close()