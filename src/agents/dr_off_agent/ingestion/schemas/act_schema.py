#!/usr/bin/env python3
"""Add Health Insurance Act tables to the database schema."""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_act_tables(db_path: str = 'data/ohip.db'):
    """Add Health Insurance Act specific tables to the database."""
    
    logger.info(f"Adding Act tables to database: {db_path}")
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Eligibility and presence rules
        logger.info("Creating act_eligibility_rule table...")
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
        
        # 2. Status extensions (CF/RCMP/diplomat)
        logger.info("Creating act_status_extension table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_status_extension (
            ext_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            population TEXT NOT NULL,
            condition_json TEXT NOT NULL,
            effect TEXT NOT NULL,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, population)
        )
        """)
        
        # 3. Dependant carry-over rules
        logger.info("Creating act_dependant_carryover table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_dependant_carryover (
            dep_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            who TEXT NOT NULL,
            anchor_population TEXT NOT NULL,
            effect TEXT NOT NULL,
            prerequisites_json TEXT,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, who, anchor_population)
        )
        """)
        
        # 4. Health card obligations
        logger.info("Creating act_health_card_rule table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_health_card_rule (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ref TEXT NOT NULL,
            obligation TEXT NOT NULL,
            scope TEXT NOT NULL,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_ref, obligation, scope)
        )
        """)
        
        # 5. Uninsured references
        logger.info("Creating act_uninsured_reference table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_uninsured_reference (
            ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
            act_pointer TEXT NOT NULL,
            schedule_pointer TEXT,
            exemplar TEXT NOT NULL,
            line_range TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(act_pointer, exemplar)
        )
        """)
        
        # 6. Ingestion logs
        logger.info("Creating act_ingestion_log table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS act_ingestion_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            status TEXT NOT NULL,
            sections_processed INTEGER,
            sql_records INTEGER,
            chroma_embeddings INTEGER,
            error_count INTEGER,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            metadata_json TEXT
        )
        """)
        
        # Create indexes for performance
        logger.info("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_eligibility_section ON act_eligibility_rule(section_ref)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_eligibility_title ON act_eligibility_rule(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_status_population ON act_status_extension(population)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_dependant_who ON act_dependant_carryover(who)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_health_card_obligation ON act_health_card_rule(obligation)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_uninsured_exemplar ON act_uninsured_reference(exemplar)")
        
        # Create views for easier querying
        logger.info("Creating Act views...")
        
        # View for eligibility rules with readable conditions
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_act_eligibility AS
        SELECT 
            rule_id,
            section_ref,
            title,
            effect,
            max_duration_months,
            condition_json,
            prerequisites_json,
            notes,
            line_range,
            CASE 
                WHEN title LIKE '%student%' THEN 'student'
                WHEN title LIKE '%worker%' THEN 'worker'
                WHEN title LIKE '%spouse%' THEN 'spouse'
                WHEN title LIKE '%dependant%' THEN 'dependant'
                WHEN title LIKE '%CF%' OR title LIKE '%Canadian Forces%' THEN 'military'
                WHEN title LIKE '%RCMP%' THEN 'RCMP'
                WHEN title LIKE '%diplomat%' THEN 'diplomat'
                ELSE 'general'
            END as population_type
        FROM act_eligibility_rule
        """)
        
        # View for all Act rules combined
        cursor.execute("""
        CREATE VIEW IF NOT EXISTS v_act_all_rules AS
        SELECT 
            'eligibility' as rule_type,
            section_ref,
            title,
            effect,
            line_range
        FROM act_eligibility_rule
        UNION ALL
        SELECT 
            'status_extension' as rule_type,
            section_ref,
            population as title,
            effect,
            line_range
        FROM act_status_extension
        UNION ALL
        SELECT 
            'dependant_carryover' as rule_type,
            section_ref,
            who || ' of ' || anchor_population as title,
            effect,
            line_range
        FROM act_dependant_carryover
        UNION ALL
        SELECT 
            'health_card' as rule_type,
            section_ref,
            obligation as title,
            scope as effect,
            line_range
        FROM act_health_card_rule
        UNION ALL
        SELECT 
            'uninsured' as rule_type,
            act_pointer as section_ref,
            exemplar as title,
            schedule_pointer as effect,
            line_range
        FROM act_uninsured_reference
        """)
        
        conn.commit()
        logger.info("✓ Act tables created successfully")
        
        # Show current state
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'act_%'")
        tables = cursor.fetchall()
        logger.info(f"\nAct tables created: {[t[0] for t in tables]}")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'v_act_%'")
        views = cursor.fetchall()
        logger.info(f"Act views created: {[v[0] for v in views]}")
        
        # Create MCP tool functions reference
        create_mcp_functions_for_act()
        
    except Exception as e:
        logger.error(f"Error creating Act tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def create_mcp_functions_for_act():
    """Create MCP tool function templates for Act data access."""
    
    functions = """
# MCP Tool Functions for Health Insurance Act Data Access

def mcp_get_act_eligibility(section_ref: str = None, population: str = None) -> list:
    '''Get eligibility rules from Health Insurance Act.
    
    Args:
        section_ref: Specific section reference (e.g., "1.8(1)")
        population: Filter by population (student, worker, CF, RCMP, diplomat, spouse, dependant)
    
    Returns:
        List of eligibility rules with conditions and effects
    '''
    query = '''
        SELECT * FROM v_act_eligibility
        WHERE 1=1
    '''
    if section_ref:
        query += ' AND section_ref = ?'
    if population:
        query += ' AND population_type = ?'
    # Returns eligibility rules with parsed conditions

def mcp_check_physical_presence(days_in_ontario: int, period_months: int = 12) -> dict:
    '''Check if physical presence requirements are met.
    
    Args:
        days_in_ontario: Number of days physically present in Ontario
        period_months: Period to check (default 12 months)
    
    Returns:
        Dict with eligibility status and applicable rules
    '''
    # Check against 153 days in 12 months rule
    # Check exemptions (student, worker, CF, etc.)
    
def mcp_get_act_section(section_ref: str) -> dict:
    '''Get specific section from Health Insurance Act with all related rules.
    
    Args:
        section_ref: Section reference (e.g., "1.3", "1.8(1)")
    
    Returns:
        Section text from Chroma + all SQL rules for that section
    '''
    # Query Chroma for section text
    # Query SQL for structured rules
    # Combine results
    
def mcp_search_act_rules(query: str, rule_type: str = None) -> list:
    '''Search Act rules by keyword or type.
    
    Args:
        query: Search terms
        rule_type: Filter by type (eligibility, status_extension, dependant_carryover, health_card, uninsured)
    
    Returns:
        Matching rules from all Act tables
    '''
    sql = '''
        SELECT * FROM v_act_all_rules
        WHERE (title LIKE ? OR effect LIKE ?)
    '''
    if rule_type:
        sql += ' AND rule_type = ?'
    # Returns matching rules across all tables

def mcp_get_dependant_rules(anchor: str) -> list:
    '''Get rules for dependants of specific populations.
    
    Args:
        anchor: Anchor population (student, worker, CF, RCMP, diplomat)
    
    Returns:
        Rules for spouse/dependant carry-over
    '''
    query = '''
        SELECT * FROM act_dependant_carryover
        WHERE anchor_population = ?
    '''
    # Returns carry-over rules for dependants

def mcp_get_health_card_obligations() -> list:
    '''Get all health card obligations and rules.'''
    query = 'SELECT * FROM act_health_card_rule'
    # Returns health card requirements

def mcp_get_uninsured_services() -> list:
    '''Get references to uninsured services and exclusions.'''
    query = '''
        SELECT 
            ur.*,
            fs.description as schedule_description
        FROM act_uninsured_reference ur
        LEFT JOIN ohip_fee_schedule fs ON ur.schedule_pointer = fs.fee_code
    '''
    # Returns uninsured service references with Schedule links
"""
    
    logger.info("\nSuggested MCP tool functions for Act data:")
    print(functions)
    
    # Save to file for reference
    with open('mcp_act_tool_functions.py', 'w') as f:
        f.write(functions)
    logger.info("Saved Act MCP function templates to mcp_act_tool_functions.py")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Add Health Insurance Act tables to database')
    parser.add_argument('--db', default='data/ohip.db', help='Database path')
    
    args = parser.parse_args()
    
    add_act_tables(args.db)