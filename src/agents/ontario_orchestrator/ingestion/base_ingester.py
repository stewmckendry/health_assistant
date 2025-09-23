"""Base ingester class for Dr. OFF data sources."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Tuple
import hashlib
import json
from datetime import datetime
import sqlite3

import chromadb
from chromadb.config import Settings
import openai
from tqdm import tqdm

from .database import Database

logger = logging.getLogger(__name__)


class BaseIngester(ABC):
    """Abstract base class for data ingestion.
    
    Provides common functionality for:
    - Database operations
    - Document chunking
    - Embedding generation
    - Vector store management
    - Error handling and logging
    """
    
    DEFAULT_CHUNK_SIZE = 1000  # tokens
    DEFAULT_CHUNK_OVERLAP = 200  # tokens
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_BATCH_SIZE = 100
    
    def __init__(
        self,
        source_type: str,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize base ingester.
        
        Args:
            source_type: Type of data source ('odb', 'ohip', 'adp')
            db_path: Path to SQLite database
            chroma_path: Path to Chroma vector store
            openai_api_key: OpenAI API key for embeddings
        """
        self.source_type = source_type
        self.db = Database(db_path)
        
        # Set up Chroma
        if chroma_path is None:
            chroma_path = "data/processed/dr_off/chroma"
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection for this source type
        collection_name = f"{source_type}_documents"
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Using existing Chroma collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"source": source_type}
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
            'records_processed': 0,
            'records_failed': 0,
            'chunks_created': 0,
            'embeddings_created': 0,
            'errors': []
        }
    
    @abstractmethod
    def ingest(self, source_file: str) -> Dict[str, Any]:
        """Ingest data from source file.
        
        Must be implemented by subclasses.
        
        Args:
            source_file: Path to source data file
            
        Returns:
            Dictionary with ingestion statistics
        """
        pass
    
    @abstractmethod
    def parse_source(self, source_file: str) -> Generator[Dict[str, Any], None, None]:
        """Parse source file and yield records.
        
        Must be implemented by subclasses.
        
        Args:
            source_file: Path to source data file
            
        Yields:
            Parsed records as dictionaries
        """
        pass
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Chunk text for embedding.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            metadata: Additional metadata for chunks
            
        Returns:
            List of chunk dictionaries
        """
        if chunk_size is None:
            chunk_size = self.DEFAULT_CHUNK_SIZE
        if chunk_overlap is None:
            chunk_overlap = self.DEFAULT_CHUNK_OVERLAP
        
        # Simple character-based chunking (can be improved with tiktoken)
        # Approximate 1 token = 4 characters
        char_size = chunk_size * 4
        char_overlap = chunk_overlap * 4
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = min(start + char_size, len(text))
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + char_size // 2:
                    end = last_period + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = self._generate_chunk_id(chunk_text, chunk_index)
                
                chunk = {
                    'chunk_id': chunk_id,
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'start_char': start,
                    'end_char': end,
                    'metadata': metadata or {}
                }
                chunks.append(chunk)
                chunk_index += 1
            
            start = end - char_overlap if end < len(text) else end
        
        return chunks
    
    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for embedding API calls
            
        Returns:
            List of embedding vectors
        """
        if not self.openai_client:
            logger.warning("No OpenAI client - returning empty embeddings")
            return [[0.0] * 1536 for _ in texts]  # Mock embeddings
        
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
                # Return zero vectors on error
                embeddings.extend([[0.0] * 1536 for _ in batch])
        
        return embeddings
    
    def store_chunks_with_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        source_document: str
    ) -> int:
        """Store chunks in database and vector store.
        
        Args:
            chunks: List of chunk dictionaries
            source_document: Name of source document
            
        Returns:
            Number of chunks stored
        """
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
                    INSERT INTO document_chunks (
                        chunk_id, source_type, source_document, chunk_text,
                        chunk_index, page_number, section, subsection,
                        start_char, end_char, embedding_model, embedding_id,
                        metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk['chunk_id'],
                    self.source_type,
                    source_document,
                    chunk['text'],
                    chunk['chunk_index'],
                    chunk['metadata'].get('page_number'),
                    chunk['metadata'].get('section'),
                    chunk['metadata'].get('subsection'),
                    chunk['start_char'],
                    chunk['end_char'],
                    self.EMBEDDING_MODEL if embeddings else None,
                    chunk['chunk_id'],  # Use chunk_id as embedding_id
                    json.dumps(chunk['metadata'])
                ))
                
                # Store in Chroma if we have real embeddings
                if self.openai_client and not all(v == 0.0 for v in embedding):
                    self.collection.add(
                        ids=[chunk['chunk_id']],
                        embeddings=[embedding],
                        documents=[chunk['text']],
                        metadatas=[{
                            'source_type': self.source_type,
                            'source_document': source_document,
                            'chunk_index': chunk['chunk_index'],
                            **chunk['metadata']
                        }]
                    )
                
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing chunk {chunk['chunk_id']}: {e}")
                self.ingestion_stats['errors'].append(str(e))
        
        conn.commit()
        self.ingestion_stats['chunks_created'] += stored_count
        self.ingestion_stats['embeddings_created'] += stored_count
        
        return stored_count
    
    def log_ingestion(
        self,
        source_file: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """Log ingestion progress to database.
        
        Args:
            source_file: Source file being processed
            status: Current status ('started', 'completed', 'failed')
            error_message: Optional error message
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        if status == 'started':
            cursor.execute("""
                INSERT INTO ingestion_log (
                    source_type, source_file, status, started_at
                ) VALUES (?, ?, ?, ?)
            """, (self.source_type, source_file, status, datetime.now()))
            
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
                self.ingestion_stats['records_processed'],
                self.ingestion_stats['records_failed'],
                error_message,
                datetime.now(),
                self.source_type,
                source_file
            ))
        
        conn.commit()
    
    def _generate_chunk_id(self, text: str, index: int) -> str:
        """Generate unique ID for chunk.
        
        Args:
            text: Chunk text
            index: Chunk index
            
        Returns:
            Unique chunk ID
        """
        content = f"{self.source_type}_{index}_{text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def search_similar(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in vector store.
        
        Args:
            query: Query text
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of similar chunks with scores
        """
        if not self.openai_client:
            logger.warning("No OpenAI client - cannot search")
            return []
        
        # Generate query embedding
        query_embedding = self.generate_embeddings([query])[0]
        
        # Search in Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        if results['ids']:
            for i, chunk_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    'chunk_id': chunk_id,
                    'text': results['documents'][0][i],
                    'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                    'metadata': results['metadatas'][0][i]
                })
        
        return formatted_results
    
    def validate_ingestion(self) -> bool:
        """Validate ingestion completed successfully.
        
        Returns:
            True if validation passes
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Check for records in relevant tables
        table_checks = {
            'odb': ['odb_drugs', 'odb_interchangeable_groups'],
            'ohip': ['ohip_fee_schedule'],
            'adp': ['adp_device_rules']
        }
        
        tables_to_check = table_checks.get(self.source_type, [])
        
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Table {table} has {count} records")
            
            if count == 0:
                logger.warning(f"No records found in {table}")
                return False
        
        # Check chunks and embeddings
        cursor.execute(
            "SELECT COUNT(*) FROM document_chunks WHERE source_type = ?",
            (self.source_type,)
        )
        chunk_count = cursor.fetchone()[0]
        logger.info(f"Created {chunk_count} document chunks for {self.source_type}")
        
        return True
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.db.close()