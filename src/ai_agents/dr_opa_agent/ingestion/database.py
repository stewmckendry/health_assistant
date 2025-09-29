"""Database handler for Dr. OPA agent."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


class Database:
    """SQLite database handler for OPA knowledge management."""
    
    DEFAULT_DB_PATH = "data/processed/dr_opa/opa.db"
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._initialize_schema()
    
    def connect(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def _initialize_schema(self):
        """Create database tables if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Documents table - stores metadata about ingested documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opa_documents (
                document_id TEXT PRIMARY KEY,
                source_org TEXT NOT NULL,
                source_url TEXT UNIQUE NOT NULL,
                title TEXT,
                document_type TEXT,
                effective_date TEXT,
                updated_date TEXT,
                published_date TEXT,
                topics TEXT,  -- JSON array
                policy_level TEXT,  -- For CPSO: expectation/advice/general
                content_hash TEXT,
                metadata_json TEXT,
                is_superseded BOOLEAN DEFAULT 0,
                superseded_by TEXT,
                superseded_date TEXT,
                ingested_at TEXT NOT NULL,
                FOREIGN KEY (superseded_by) REFERENCES opa_documents(document_id)
            )
        """)
        
        # Sections table - stores document sections and chunks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opa_sections (
                section_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_type TEXT NOT NULL,  -- 'parent' or 'child'
                parent_id TEXT,  -- For child chunks, reference to parent
                section_heading TEXT,
                section_text TEXT NOT NULL,
                section_idx INTEGER,
                chunk_idx INTEGER,
                embedding_model TEXT,
                embedding_id TEXT,
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES opa_documents(document_id),
                FOREIGN KEY (parent_id) REFERENCES opa_sections(section_id)
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_org 
            ON opa_documents(source_org)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_type 
            ON opa_documents(document_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_effective 
            ON opa_documents(effective_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_superseded 
            ON opa_documents(is_superseded)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sections_document 
            ON opa_sections(document_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sections_type 
            ON opa_sections(chunk_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sections_parent 
            ON opa_sections(parent_id)
        """)
        
        # Ingestion log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_file TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                records_processed INTEGER DEFAULT 0,
                records_failed INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)
        
        # Query cache table for performance optimization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT UNIQUE NOT NULL,
                query_text TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                accessed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1
            )
        """)
        
        # Create index for query cache
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_hash 
            ON query_cache(query_hash)
        """)
        
        conn.commit()
        logger.info(f"Database schema initialized at {self.db_path}")
    
    def execute_query(self, query: str, params: tuple = ()) -> Any:
        """Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query results
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an update query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    
    def get_document_by_id(self, document_id: str) -> Optional[dict]:
        """Get document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document record or None
        """
        result = self.execute_query(
            "SELECT * FROM opa_documents WHERE document_id = ?",
            (document_id,)
        )
        return dict(result[0]) if result else None
    
    def get_active_documents(self, source_org: Optional[str] = None) -> list:
        """Get all active (non-superseded) documents.
        
        Args:
            source_org: Optional filter by organization
            
        Returns:
            List of document records
        """
        if source_org:
            query = """
                SELECT * FROM opa_documents 
                WHERE is_superseded = 0 AND source_org = ?
                ORDER BY effective_date DESC
            """
            params = (source_org,)
        else:
            query = """
                SELECT * FROM opa_documents 
                WHERE is_superseded = 0
                ORDER BY effective_date DESC
            """
            params = ()
        
        results = self.execute_query(query, params)
        return [dict(row) for row in results]
    
    def get_sections_by_document(self, document_id: str, chunk_type: Optional[str] = None) -> list:
        """Get sections for a document.
        
        Args:
            document_id: Document ID
            chunk_type: Optional filter by chunk type ('parent' or 'child')
            
        Returns:
            List of section records
        """
        if chunk_type:
            query = """
                SELECT * FROM opa_sections 
                WHERE document_id = ? AND chunk_type = ?
                ORDER BY section_idx, chunk_idx
            """
            params = (document_id, chunk_type)
        else:
            query = """
                SELECT * FROM opa_sections 
                WHERE document_id = ?
                ORDER BY section_idx, chunk_idx
            """
            params = (document_id,)
        
        results = self.execute_query(query, params)
        return [dict(row) for row in results]
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()