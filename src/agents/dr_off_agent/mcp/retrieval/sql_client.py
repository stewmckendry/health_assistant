"""
SQLite client with connection pooling and timeout support for MCP tools.
Shared utility for all domain tools to query OHIP, ADP, and ODB data.
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
    Used by all MCP tools for structured data queries.
    """
    
    def __init__(
        self,
        db_path: str = "data/ohip.db",
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
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            # Convert Row objects to dicts
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        finally:
            conn.close()
    
    async def query(
        self,
        sql: str,
        params: tuple = (),
        timeout_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query with timeout.
        
        Args:
            sql: SQL query string
            params: Query parameters for safe binding
            timeout_ms: Override default timeout (optional)
            
        Returns:
            List of result dictionaries
            
        Raises:
            asyncio.TimeoutError: If query exceeds timeout
        """
        timeout = (timeout_ms / 1000.0) if timeout_ms else self.timeout_seconds
        
        start_time = time.time()
        try:
            # Run blocking SQLite operation in thread pool with timeout
            results = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._execute_query,
                    sql,
                    params
                ),
                timeout=timeout
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"SQL query completed in {elapsed_ms:.1f}ms: {len(results)} results")
            
            return results
            
        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(f"SQL query timeout after {elapsed_ms:.1f}ms: {sql[:100]}...")
            raise
        except Exception as e:
            logger.error(f"SQL query error: {e}")
            raise
    
    async def query_schedule_fees(
        self,
        codes: Optional[List[str]] = None,
        search_text: Optional[str] = None,
        specialty: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Query OHIP fee schedule with common filters.
        
        Args:
            codes: Specific fee codes to lookup
            search_text: Text search in description
            specialty: Filter by specialty
            limit: Max results to return
            
        Returns:
            List of fee schedule records
        """
        conditions = []
        params = []
        
        if codes:
            placeholders = ','.join(['?' for _ in codes])
            conditions.append(f"fee_code IN ({placeholders})")
            params.extend(codes)
        
        if search_text:
            conditions.append("(description LIKE ? OR requirements LIKE ?)")
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern])
        
        if specialty:
            conditions.append("specialty = ?")
            params.append(specialty)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT 
                fee_code as code,
                description,
                amount,
                specialty,
                requirements,
                page_number,
                section
            FROM ohip_fee_schedule
            {where_clause}
            ORDER BY fee_code
            LIMIT ?
        """
        params.append(limit)
        
        return await self.query(query, tuple(params))
    
    async def query_adp_funding(
        self,
        device_category: Optional[str] = None,
        scenario_search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query ADP funding rules.
        
        Args:
            device_category: Filter by device category
            scenario_search: Search in scenario text
            
        Returns:
            List of funding rules
        """
        conditions = []
        params = []
        
        if device_category:
            conditions.append("scenario LIKE ?")
            params.append(f"%{device_category}%")
        
        if scenario_search:
            conditions.append("(scenario LIKE ? OR details LIKE ?)")
            search_pattern = f"%{scenario_search}%"
            params.extend([search_pattern, search_pattern])
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT 
                scenario,
                client_share_percent,
                100 - client_share_percent as adp_share_percent,
                details,
                section_ref,
                adp_doc
            FROM adp_funding_rule
            {where_clause}
            ORDER BY scenario
        """
        
        return await self.query(query, tuple(params))
    
    async def query_adp_exclusions(
        self,
        search_term: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query ADP exclusions.
        
        Args:
            search_term: Search in exclusion phrases
            
        Returns:
            List of exclusion rules
        """
        if search_term:
            query = """
                SELECT 
                    phrase,
                    applies_to,
                    section_ref,
                    adp_doc as details
                FROM adp_exclusion
                WHERE phrase LIKE ? OR applies_to LIKE ?
                ORDER BY phrase
            """
            params = (f"%{search_term}%", f"%{search_term}%")
        else:
            query = """
                SELECT 
                    phrase,
                    applies_to,
                    section_ref,
                    adp_doc as details
                FROM adp_exclusion
                ORDER BY phrase
            """
            params = ()
        
        return await self.query(query, params)
    
    async def query_odb_drugs(
        self,
        din: Optional[str] = None,
        ingredient: Optional[str] = None,
        interchangeable_group: Optional[str] = None,
        lowest_cost_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Query ODB drug formulary.
        
        Args:
            din: Specific DIN to lookup
            ingredient: Search by ingredient name
            interchangeable_group: Filter by group
            lowest_cost_only: Only return lowest cost options
            limit: Max results
            
        Returns:
            List of drug records
        """
        conditions = []
        params = []
        
        if din:
            conditions.append("din = ?")
            params.append(din)
        
        if ingredient:
            conditions.append("(generic_name LIKE ? OR name LIKE ?)")
            search_pattern = f"%{ingredient}%"
            params.extend([search_pattern, search_pattern])
        
        if interchangeable_group:
            conditions.append("interchangeable_group_id = ?")
            params.append(interchangeable_group)
        
        if lowest_cost_only:
            conditions.append("is_lowest_cost = 1")
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT 
                din,
                generic_name,
                name,
                strength,
                dosage_form,
                individual_price,
                is_lowest_cost,
                interchangeable_group_id
            FROM odb_drugs
            {where_clause}
            ORDER BY generic_name, name
            LIMIT ?
        """
        params.append(limit)
        
        return await self.query(query, tuple(params))
    
    async def close(self):
        """Cleanup thread pool executor."""
        self.executor.shutdown(wait=True)
    
    def __del__(self):
        """Ensure executor is cleaned up."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)