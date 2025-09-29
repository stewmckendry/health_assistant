"""
SQLite client with connection pooling and timeout support for OPA MCP tools.
Shared utility for all OPA tools to query practice guidance data.
"""
import asyncio
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
import logging
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)


class SQLClient:
    """
    Async SQLite client with connection pooling and query timeout.
    Used by all OPA MCP tools for structured data queries.
    """
    
    def __init__(
        self,
        db_path: str = "data/dr_opa_agent/opa.db",
        timeout_ms: int = 500,
        max_connections: int = 5
    ):
        """
        Initialize SQL client with connection pool.
        
        Args:
            db_path: Path to SQLite database
            timeout_ms: Query timeout in milliseconds (default 500ms)
            max_connections: Max concurrent connections in pool
        """
        self.db_path = Path(db_path)
        self.timeout_seconds = timeout_ms / 1000.0
        self.max_connections = max_connections
        
        # Thread pool for SQLite operations (SQLite doesn't support true async)
        self.executor = ThreadPoolExecutor(max_workers=max_connections)
        
        # Verify database exists
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        logger.info(f"SQL client initialized: {self.db_path} (timeout={timeout_ms}ms)")
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute query in thread (SQLite is not async-safe).
        
        Args:
            query: SQL query to execute
            params: Query parameters for safe binding
            
        Returns:
            List of result dictionaries
        """
        conn = sqlite3.connect(str(self.db_path), timeout=self.timeout_seconds)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            # Convert Row objects to dicts
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            
            return results
        finally:
            conn.close()
    
    async def search_sections(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        doc_types: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        limit: int = 10,
        include_superseded: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search document sections using FTS5 full-text search.
        
        Args:
            query: Search query
            sources: Filter by source organizations
            doc_types: Filter by document types
            topics: Filter by topics
            limit: Max results to return
            include_superseded: Include superseded documents
            
        Returns:
            List of matching sections with metadata
        """
        # Build the query with filters
        sql_parts = [
            """
            SELECT 
                s.section_id,
                s.document_id,
                s.chunk_type,
                s.section_heading,
                s.section_text,
                s.section_idx,
                d.source_org,
                d.document_type,
                d.title as document_title,
                d.effective_date,
                d.topics,
                d.is_superseded,
                d.source_url
            FROM opa_sections s
            JOIN opa_documents d ON s.document_id = d.document_id
            WHERE s.section_text LIKE ?
            """
        ]
        
        params = [f'%{query}%']
        
        # Add filters
        if not include_superseded:
            sql_parts.append("AND d.is_superseded = 0")
        
        if sources:
            placeholders = ','.join('?' * len(sources))
            sql_parts.append(f"AND d.source_org IN ({placeholders})")
            params.extend(sources)
        
        if doc_types:
            placeholders = ','.join('?' * len(doc_types))
            sql_parts.append(f"AND d.document_type IN ({placeholders})")
            params.extend(doc_types)
        
        if topics:
            # Topics are stored as JSON array, need to check each
            topic_conditions = []
            for topic in topics:
                topic_conditions.append("d.topics LIKE ?")
                params.append(f'%{topic}%')
            sql_parts.append(f"AND ({' OR '.join(topic_conditions)})")
        
        # Order by parent chunks first, then by relevance
        sql_parts.append("ORDER BY s.chunk_type DESC, s.section_idx")
        sql_parts.append(f"LIMIT {limit}")
        
        full_query = ' '.join(sql_parts)
        
        # Execute in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self._execute_query,
            full_query,
            tuple(params)
        )
        
        # Parse JSON fields
        for result in results:
            if result.get('topics'):
                try:
                    result['topics'] = json.loads(result['topics'])
                except json.JSONDecodeError:
                    result['topics'] = []
        
        return results
    
    async def get_section_by_id(
        self,
        section_id: str,
        include_children: bool = True,
        include_context: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific section by ID with optional children and context.
        
        Args:
            section_id: Section ID to retrieve
            include_children: Include child chunks
            include_context: Include surrounding sections
            
        Returns:
            Section data with requested additional content
        """
        # Get the main section
        main_query = """
            SELECT 
                s.*,
                d.source_org,
                d.document_type,
                d.title as document_title,
                d.effective_date,
                d.topics,
                d.source_url,
                d.metadata_json as document_metadata
            FROM opa_sections s
            JOIN opa_documents d ON s.document_id = d.document_id
            WHERE s.section_id = ?
        """
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self._execute_query,
            main_query,
            (section_id,)
        )
        
        if not results:
            return None
        
        section = results[0]
        
        # Parse JSON fields
        if section.get('topics'):
            try:
                section['topics'] = json.loads(section['topics'])
            except json.JSONDecodeError:
                section['topics'] = []
        
        # Get children if requested
        if include_children and section.get('chunk_type') == 'parent':
            children_query = """
                SELECT * FROM opa_sections
                WHERE parent_id = ?
                ORDER BY chunk_idx
            """
            children = await loop.run_in_executor(
                self.executor,
                self._execute_query,
                children_query,
                (section_id,)
            )
            section['children'] = children
        
        # Get context if requested
        if include_context:
            context_query = """
                SELECT section_id, section_heading, section_idx
                FROM opa_sections
                WHERE document_id = ? 
                AND section_idx BETWEEN ? AND ?
                AND section_id != ?
                ORDER BY section_idx
            """
            context = await loop.run_in_executor(
                self.executor,
                self._execute_query,
                context_query,
                (section['document_id'], 
                 section['section_idx'] - 2,
                 section['section_idx'] + 2,
                 section_id)
            )
            section['context'] = context
        
        return section
    
    async def search_policies(
        self,
        topic: str,
        policy_level: Optional[str] = None,
        include_related: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search CPSO policies by topic and level.
        
        Args:
            topic: Topic to search for
            policy_level: Filter by 'expectation', 'advice', or None for both
            include_related: Include related documents
            
        Returns:
            List of matching policies and advice
        """
        # Main search for CPSO documents
        query = """
            SELECT DISTINCT
                d.document_id,
                d.title,
                d.document_type,
                d.effective_date,
                d.topics,
                d.policy_level,
                d.source_url,
                COUNT(s.section_id) as matching_sections
            FROM opa_documents d
            JOIN opa_sections s ON d.document_id = s.document_id
            WHERE d.source_org = 'cpso'
            AND d.is_superseded = 0
            AND (d.title LIKE ? OR s.section_text LIKE ? OR d.topics LIKE ?)
        """
        
        params = [f'%{topic}%', f'%{topic}%', f'%{topic}%']
        
        if policy_level and policy_level != 'both':
            query += " AND d.policy_level = ?"
            params.append(policy_level)
        
        query += " GROUP BY d.document_id ORDER BY d.effective_date DESC"
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self._execute_query,
            query,
            tuple(params)
        )
        
        # Parse topics JSON
        for result in results:
            if result.get('topics'):
                try:
                    result['topics'] = json.loads(result['topics'])
                except json.JSONDecodeError:
                    result['topics'] = []
        
        return results
    
    async def get_program_info(
        self,
        program: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get Ontario Health screening program information.
        
        Args:
            program: Program name (breast, cervical, colorectal, lung, hpv)
            
        Returns:
            Program information from Ontario Health documents
        """
        query = """
            SELECT 
                d.document_id,
                d.title,
                d.effective_date,
                d.source_url,
                s.section_heading,
                s.section_text
            FROM opa_documents d
            JOIN opa_sections s ON d.document_id = s.document_id
            WHERE d.source_org = 'ontario_health'
            AND d.is_superseded = 0
            AND (
                (d.title LIKE ? OR s.section_text LIKE ?)
                OR (d.topics LIKE ?)
            )
            ORDER BY d.effective_date DESC, s.section_idx
            LIMIT 20
        """
        
        params = (f'%{program}%', f'%{program}%', f'%{program}%')
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self._execute_query,
            query,
            params
        )
        
        if not results:
            return None
        
        # Group sections by document
        program_info = {
            'program': program,
            'documents': {},
            'sections': []
        }
        
        for row in results:
            doc_id = row['document_id']
            if doc_id not in program_info['documents']:
                program_info['documents'][doc_id] = {
                    'title': row['title'],
                    'effective_date': row['effective_date'],
                    'url': row['source_url']
                }
            
            program_info['sections'].append({
                'document_id': doc_id,
                'heading': row['section_heading'],
                'text': row['section_text']
            })
        
        return program_info
    
    async def check_freshness(
        self,
        topic: str,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check the freshness of guidance on a topic.
        
        Args:
            topic: Topic to check
            sources: Specific sources to check
            
        Returns:
            Information about the most recent guidance
        """
        query = """
            SELECT 
                d.document_id,
                d.title,
                d.source_org,
                d.document_type,
                d.effective_date,
                d.updated_date,
                d.published_date,
                d.source_url
            FROM opa_documents d
            WHERE d.is_superseded = 0
            AND (d.title LIKE ? OR d.topics LIKE ?)
        """
        
        params = [f'%{topic}%', f'%{topic}%']
        
        if sources:
            placeholders = ','.join('?' * len(sources))
            query += f" AND d.source_org IN ({placeholders})"
            params.extend(sources)
        
        query += " ORDER BY COALESCE(d.effective_date, d.updated_date, d.published_date) DESC LIMIT 10"
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self._execute_query,
            query,
            tuple(params)
        )
        
        if not results:
            return {
                'topic': topic,
                'current_guidance': None,
                'last_updated': None
            }
        
        # Get the most recent document
        most_recent = results[0]
        last_date = most_recent.get('effective_date') or \
                   most_recent.get('updated_date') or \
                   most_recent.get('published_date')
        
        return {
            'topic': topic,
            'current_guidance': most_recent,
            'last_updated': last_date,
            'all_matches': results
        }
    
    async def close(self):
        """Close the thread pool executor."""
        self.executor.shutdown(wait=True)