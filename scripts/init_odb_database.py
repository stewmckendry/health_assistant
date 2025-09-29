#!/usr/bin/env python3
"""
Initialize ODB database schema
"""

import sqlite3
from pathlib import Path

def init_odb_database():
    """Initialize ODB database with required tables"""
    
    # Database path
    db_path = "data/dr_off_agent/processed/odb_processed_data.db"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    print(f"🔧 Initializing ODB database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create ingestion_log table (required by base ingester)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            source_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created ingestion_log table")
    
    # Create odb_drugs table (main formulary table)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odb_drugs (
            din TEXT PRIMARY KEY,
            name TEXT,
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
            listing_date TEXT,
            status TEXT,
            is_lowest_cost BOOLEAN,
            is_benefit BOOLEAN,
            is_chronic_use BOOLEAN,
            is_section_3 BOOLEAN,
            is_section_3b BOOLEAN,
            is_section_3c BOOLEAN,
            is_section_9 BOOLEAN,
            is_section_12 BOOLEAN,
            additional_benefit_type TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created odb_drugs table")
    
    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_odb_drugs_generic ON odb_drugs(generic_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_odb_drugs_group ON odb_drugs(interchangeable_group_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_odb_drugs_lowest ON odb_drugs(is_lowest_cost)")
    print("✅ Created indexes on odb_drugs")
    
    # Create odb_interchangeable_groups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odb_interchangeable_groups (
            group_id TEXT PRIMARY KEY,
            generic_name TEXT,
            therapeutic_class TEXT,
            category TEXT,
            strength TEXT,
            dosage_form TEXT,
            item_number TEXT,
            member_count INTEGER,
            lowest_cost_din TEXT,
            lowest_cost_price REAL,
            daily_cost TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created odb_interchangeable_groups table")
    
    # Create odb_limited_use table for LU criteria
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odb_limited_use (
            lu_code TEXT PRIMARY KEY,
            din TEXT,
            generic_name TEXT,
            criteria TEXT,
            conditions TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (din) REFERENCES odb_drugs(din)
        )
    """)
    print("✅ Created odb_limited_use table")
    
    # Create odb_exceptional_access table for EAP
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odb_exceptional_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            din TEXT,
            generic_name TEXT,
            indication TEXT,
            criteria TEXT,
            approval_duration TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (din) REFERENCES odb_drugs(din)
        )
    """)
    print("✅ Created odb_exceptional_access table")
    
    # Create odb_manufacturers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odb_manufacturers (
            manufacturer_id TEXT PRIMARY KEY,
            name TEXT,
            address TEXT,
            phone TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created odb_manufacturers table")
    
    # Create aliases table for the tool (maps SQL client expectations)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odb_formulary (
            din TEXT PRIMARY KEY,
            generic_name TEXT,
            brand_name TEXT,
            strength TEXT,
            dosage_form TEXT,
            price REAL,
            lu_code TEXT,
            status TEXT,
            FOREIGN KEY (din) REFERENCES odb_drugs(din)
        )
    """)
    print("✅ Created odb_formulary alias table")
    
    conn.commit()
    conn.close()
    
    print("\n✨ ODB database initialization complete!")

if __name__ == "__main__":
    init_odb_database()