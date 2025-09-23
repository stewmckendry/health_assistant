"""Database schema and initialization for Dr. OFF.

This module defines the database schema for Ontario healthcare data.
Designed to be portable between SQLite (local) and PostgreSQL/MySQL (cloud).
"""

import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# SQL schema definitions - SQLite compatible
SCHEMA_SQL = {
    'odb_drugs': """
        CREATE TABLE IF NOT EXISTS odb_drugs (
            din TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            generic_name TEXT,
            manufacturer_id TEXT,
            strength TEXT,
            dosage_form TEXT,
            item_number TEXT,
            therapeutic_class TEXT,
            category TEXT,
            interchangeable_group_id TEXT,
            individual_price REAL,
            daily_cost REAL,
            amount_mohltc_pays REAL,
            listing_date DATE,
            status TEXT,
            is_lowest_cost BOOLEAN DEFAULT FALSE,
            is_benefit BOOLEAN DEFAULT TRUE,
            is_chronic_use BOOLEAN DEFAULT FALSE,
            is_section_3 BOOLEAN DEFAULT FALSE,
            is_section_3b BOOLEAN DEFAULT FALSE,
            is_section_3c BOOLEAN DEFAULT FALSE,
            is_section_9 BOOLEAN DEFAULT FALSE,
            is_section_12 BOOLEAN DEFAULT FALSE,
            additional_benefit_type TEXT,
            notes TEXT,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    'odb_interchangeable_groups': """
        CREATE TABLE IF NOT EXISTS odb_interchangeable_groups (
            group_id TEXT PRIMARY KEY,
            generic_name TEXT NOT NULL,
            therapeutic_class TEXT,
            category TEXT,
            strength TEXT,
            dosage_form TEXT,
            item_number TEXT,
            member_count INTEGER DEFAULT 0,
            lowest_cost_din TEXT,
            lowest_cost_price REAL,
            daily_cost TEXT,
            notes TEXT,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    'ohip_fee_schedule': """
        CREATE TABLE IF NOT EXISTS ohip_fee_schedule (
            fee_code TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            amount REAL,
            units TEXT,
            specialty TEXT,
            category TEXT,
            subcategory TEXT,
            requirements TEXT,
            notes TEXT,
            effective_date DATE,
            end_date DATE,
            page_number INTEGER,
            section TEXT,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    'ohip_diagnostic_codes': """
        CREATE TABLE IF NOT EXISTS ohip_diagnostic_codes (
            diagnostic_code TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            category TEXT,
            notes TEXT,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    'adp_device_rules': """
        CREATE TABLE IF NOT EXISTS adp_device_rules (
            device_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            subcategory TEXT,
            device_name TEXT NOT NULL,
            device_description TEXT,
            funding_percentage REAL,
            max_funding_amount REAL,
            cost_share_amount REAL,
            eligibility_criteria TEXT,
            age_restrictions TEXT,
            diagnosis_requirements TEXT,
            prescription_requirements TEXT,
            assessment_requirements TEXT,
            replacement_interval_months INTEGER,
            repair_coverage TEXT,
            forms_required TEXT,
            vendor_requirements TEXT,
            notes TEXT,
            effective_date DATE,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    'adp_eligibility_criteria': """
        CREATE TABLE IF NOT EXISTS adp_eligibility_criteria (
            criteria_id TEXT PRIMARY KEY,
            device_category TEXT,
            diagnosis_code TEXT,
            functional_requirements TEXT,
            medical_requirements TEXT,
            environmental_requirements TEXT,
            notes TEXT,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    'document_chunks': """
        CREATE TABLE IF NOT EXISTS document_chunks (
            chunk_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_document TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER,
            page_number INTEGER,
            section TEXT,
            subsection TEXT,
            start_char INTEGER,
            end_char INTEGER,
            embedding_model TEXT,
            embedding_id TEXT,
            metadata_json TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    'ingestion_log': """
        CREATE TABLE IF NOT EXISTS ingestion_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_file TEXT NOT NULL,
            status TEXT NOT NULL,
            records_processed INTEGER DEFAULT 0,
            records_failed INTEGER DEFAULT 0,
            error_message TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """
}

# SQLite-specific index creation (PostgreSQL syntax differs slightly)
SQLITE_INDEXES = {
    'odb_drugs': [
        "CREATE INDEX IF NOT EXISTS idx_odb_din ON odb_drugs(din);",
        "CREATE INDEX IF NOT EXISTS idx_odb_generic ON odb_drugs(generic_name);",
        "CREATE INDEX IF NOT EXISTS idx_odb_group ON odb_drugs(interchangeable_group_id);",
        "CREATE INDEX IF NOT EXISTS idx_odb_therapeutic ON odb_drugs(therapeutic_class);",
        "CREATE INDEX IF NOT EXISTS idx_odb_lowest ON odb_drugs(is_lowest_cost);"
    ],
    'odb_interchangeable_groups': [
        "CREATE INDEX IF NOT EXISTS idx_grp_generic ON odb_interchangeable_groups(generic_name);",
        "CREATE INDEX IF NOT EXISTS idx_grp_therapeutic ON odb_interchangeable_groups(therapeutic_class);"
    ],
    'ohip_fee_schedule': [
        "CREATE INDEX IF NOT EXISTS idx_ohip_specialty ON ohip_fee_schedule(specialty);",
        "CREATE INDEX IF NOT EXISTS idx_ohip_category ON ohip_fee_schedule(category);",
        "CREATE INDEX IF NOT EXISTS idx_ohip_effective ON ohip_fee_schedule(effective_date);"
    ],
    'adp_device_rules': [
        "CREATE INDEX IF NOT EXISTS idx_adp_category ON adp_device_rules(category);",
        "CREATE INDEX IF NOT EXISTS idx_adp_device ON adp_device_rules(device_name);"
    ],
    'document_chunks': [
        "CREATE INDEX IF NOT EXISTS idx_chunk_source ON document_chunks(source_type, source_document);",
        "CREATE INDEX IF NOT EXISTS idx_chunk_embedding ON document_chunks(embedding_id);"
    ]
}

class Database:
    """Database manager for Dr. OFF data.
    
    Supports both SQLite (local) and cloud databases.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = "data/processed/dr_off/dr_off.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        
    def connect(self) -> sqlite3.Connection:
        """Create database connection."""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            # Enable foreign keys for SQLite
            self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn
    
    def init_schema(self):
        """Initialize database schema."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Create tables
        for table_name, schema in SCHEMA_SQL.items():
            logger.info(f"Creating table: {table_name}")
            cursor.execute(schema)
        
        # Create indexes separately for SQLite
        for table_name, indexes in SQLITE_INDEXES.items():
            for index_sql in indexes:
                cursor.execute(index_sql)
        
        conn.commit()
        logger.info("Database schema initialized successfully")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_cloud_schema(self) -> dict:
        """Get schema formatted for cloud databases (PostgreSQL/MySQL).
        
        Returns:
            Dictionary of table schemas with cloud-compatible syntax.
        """
        # This would return schemas with appropriate modifications for cloud DBs
        # e.g., SERIAL instead of AUTOINCREMENT, different index syntax, etc.
        return SCHEMA_SQL
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def init_database(db_path: Optional[str] = None) -> Database:
    """Initialize database with schema.
    
    Args:
        db_path: Optional path to database file.
    
    Returns:
        Initialized Database instance.
    """
    db = Database(db_path)
    db.init_schema()
    return db


if __name__ == "__main__":
    # Initialize database when run directly
    logging.basicConfig(level=logging.INFO)
    db = init_database()
    logger.info(f"Database initialized at: {db.db_path}")
    db.close()