#!/usr/bin/env python3
"""Update database schema to better support MCP tool access."""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from agents.clinical.dr_off.ingestion.database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_schema():
    """Add junction table and update schema for better MCP access."""
    
    db = Database()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # 1. Add junction table for chunk-fee relationships
        logger.info("Creating chunk_fee_codes junction table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunk_fee_codes (
                chunk_id TEXT NOT NULL,
                fee_code TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0,
                PRIMARY KEY (chunk_id, fee_code),
                FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id),
                FOREIGN KEY (fee_code) REFERENCES ohip_fee_schedule(fee_code)
            )
        """)
        
        # Add indexes for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_fee_chunk 
            ON chunk_fee_codes(chunk_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_fee_code 
            ON chunk_fee_codes(fee_code)
        """)
        
        # 2. Add fee_codes_list column to document_chunks for quick access
        logger.info("Adding fee_codes_list column to document_chunks...")
        cursor.execute("""
            ALTER TABLE document_chunks 
            ADD COLUMN fee_codes_list TEXT
        """)
        
        # 3. Add embedding_vector column for potential local similarity search
        logger.info("Adding embedding_vector column for future use...")
        cursor.execute("""
            ALTER TABLE document_chunks 
            ADD COLUMN embedding_vector BLOB
        """)
        
        # 4. Create view for MCP tools to easily query
        logger.info("Creating MCP-friendly views...")
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_fee_code_context AS
            SELECT 
                f.fee_code,
                f.description,
                f.amount,
                f.specialty,
                f.category,
                c.chunk_id,
                c.chunk_text,
                c.page_number,
                c.section,
                c.subsection
            FROM ohip_fee_schedule f
            LEFT JOIN chunk_fee_codes cfc ON f.fee_code = cfc.fee_code
            LEFT JOIN document_chunks c ON cfc.chunk_id = c.chunk_id
        """)
        
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_chunk_summary AS
            SELECT 
                c.chunk_id,
                c.source_type,
                c.section,
                c.subsection,
                c.page_number,
                c.fee_codes_list,
                COUNT(cfc.fee_code) as fee_code_count,
                GROUP_CONCAT(cfc.fee_code) as linked_fee_codes
            FROM document_chunks c
            LEFT JOIN chunk_fee_codes cfc ON c.chunk_id = cfc.chunk_id
            WHERE c.source_type = 'ohip'
            GROUP BY c.chunk_id
        """)
        
        conn.commit()
        logger.info("✓ Schema updated successfully")
        
        # Show current state
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"\nCurrent tables: {[t[0] for t in tables]}")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = cursor.fetchall()
        logger.info(f"Current views: {[v[0] for v in views]}")
        
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            logger.warning(f"Column already exists: {e}")
        else:
            logger.error(f"Error updating schema: {e}")
            raise
    finally:
        conn.close()


def create_mcp_functions():
    """Create Python functions that MCP tools can call."""
    
    functions = """
# MCP Tool Functions for OHIP Data Access

def mcp_get_fee_code(fee_code: str) -> dict:
    '''Get fee code details with associated context.'''
    query = '''
        SELECT 
            f.*,
            GROUP_CONCAT(c.chunk_id) as chunk_ids
        FROM ohip_fee_schedule f
        LEFT JOIN chunk_fee_codes cfc ON f.fee_code = cfc.fee_code
        LEFT JOIN document_chunks c ON cfc.chunk_id = c.chunk_id
        WHERE f.fee_code = ?
        GROUP BY f.fee_code
    '''
    # Returns fee details + list of relevant chunk IDs

def mcp_search_fee_codes(query: str, specialty: str = None) -> list:
    '''Search fee codes by description or specialty.'''
    sql = '''
        SELECT * FROM ohip_fee_schedule
        WHERE description LIKE ?
    '''
    if specialty:
        sql += ' AND specialty = ?'
    # Returns matching fee codes

def mcp_get_chunk_context(chunk_id: str) -> dict:
    '''Get chunk text with associated fee codes.'''
    query = '''
        SELECT 
            c.*,
            GROUP_CONCAT(cfc.fee_code) as fee_codes
        FROM document_chunks c
        LEFT JOIN chunk_fee_codes cfc ON c.chunk_id = cfc.chunk_id
        WHERE c.chunk_id = ?
        GROUP BY c.chunk_id
    '''
    # Returns chunk with fee code list

def mcp_vector_search(query: str, n_results: int = 5) -> list:
    '''Semantic search using ChromaDB embeddings.'''
    # Query ChromaDB collection
    # Return chunks with metadata including fee codes

def mcp_get_fee_context(fee_code: str) -> dict:
    '''Get fee code with full text context from chunks.'''
    # Combines SQL fee data + ChromaDB context
    # Returns comprehensive fee information
"""
    
    logger.info("\nSuggested MCP tool functions:")
    print(functions)
    
    # Save to file for reference
    with open('mcp_tool_functions.py', 'w') as f:
        f.write(functions)
    logger.info("Saved MCP function templates to mcp_tool_functions.py")


if __name__ == '__main__':
    logger.info("Updating database schema for MCP access...")
    update_schema()
    create_mcp_functions()