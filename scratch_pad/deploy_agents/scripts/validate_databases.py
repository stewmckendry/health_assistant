#!/usr/bin/env python3
"""
Database Validation Script
Checks all SQLite and ChromaDB databases for expected tables, collections, and record counts.
"""

import sqlite3
import os
from pathlib import Path
import json
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_sqlite_db(db_path, expected_tables):
    """Check SQLite database for tables and record counts."""
    print(f"\n{BLUE}Checking SQLite: {db_path}{RESET}")
    
    if not Path(db_path).exists():
        print(f"{RED}✗ Database not found!{RESET}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"  Found {len(tables)} tables")
        
        # Check each table
        all_good = True
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            # Check if table is expected
            status = ""
            if expected_tables and table in expected_tables:
                if count > 0:
                    status = f"{GREEN}✓{RESET}"
                else:
                    status = f"{YELLOW}⚠ (empty){RESET}"
                    all_good = False
            elif expected_tables:
                status = f"{YELLOW}(unexpected){RESET}"
            else:
                status = f"{GREEN}✓{RESET}" if count > 0 else f"{YELLOW}⚠{RESET}"
            
            print(f"    {status} {table}: {count:,} records")
            
            # Show sample columns for important tables
            if table in expected_tables and expected_tables[table]:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()][:5]  # First 5 columns
                print(f"      Columns: {', '.join(columns)}...")
        
        conn.close()
        return all_good
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")
        return False

def check_ohip_database():
    """Check OHIP database for Dr. OFF agent."""
    print(f"\n{BLUE}=== OHIP Database (Dr. OFF Agent) ==={RESET}")
    
    expected = {
        'schedule_benefits': ['fee_code', 'description'],
        'schedule_benefits_meta': [],
        'adp_devices': ['category', 'device_type'],
        'adp_eligibility': [],
        'adp_coverage': [],
        'odb_formulary': ['drug_name', 'din'],
        'odb_coverage': [],
        'odb_limited_use': [],
    }
    
    return check_sqlite_db('data/ohip.db', expected)

def check_conversation_databases():
    """Check conversation tracking databases."""
    print(f"\n{BLUE}=== Conversation Databases ==={RESET}")
    
    expected = {
        'conversations': ['conversation_id', 'created_at'],
        'messages': ['message_id', 'conversation_id', 'content'],
        'feedback': ['feedback_id', 'conversation_id']
    }
    
    all_good = True
    
    # Check each conversation database
    for db_name in ['dr_opa_conversations.db', 'dr_off_conversations.db', 'orchestrator_conversations.db']:
        result = check_sqlite_db(f'data/{db_name}', expected)
        all_good = all_good and result
    
    return all_good

def check_chroma_collections():
    """Check ChromaDB collections."""
    print(f"\n{BLUE}=== ChromaDB Vector Stores ==={RESET}")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        chroma_paths = [
            ('Dr. OPA', 'data/dr_opa_agent/chroma'),
            ('Dr. OFF', 'data/dr_off_agent/processed/dr_off/chroma'),
            ('Dr. OPA (alt)', 'data/processed/dr_opa/chroma'),
            ('Dr. OFF (alt)', 'data/processed/dr_off/chroma'),
        ]
        
        all_good = True
        
        for name, path in chroma_paths:
            print(f"\n{BLUE}Checking ChromaDB: {name} ({path}){RESET}")
            
            if not Path(path).exists():
                print(f"{YELLOW}  ⚠ Directory not found{RESET}")
                continue
            
            try:
                # Initialize client
                client = chromadb.PersistentClient(path=path)
                
                # Get all collections
                collections = client.list_collections()
                print(f"  Found {len(collections)} collections")
                
                for collection in collections:
                    # Get collection info
                    col = client.get_collection(collection.name)
                    count = col.count()
                    
                    # Get sample document
                    sample = col.get(limit=1)
                    
                    status = f"{GREEN}✓{RESET}" if count > 0 else f"{YELLOW}⚠ (empty){RESET}"
                    print(f"    {status} {collection.name}: {count:,} documents")
                    
                    if count > 0 and sample['metadatas']:
                        # Show metadata keys
                        metadata_keys = list(sample['metadatas'][0].keys())[:5]
                        print(f"      Metadata keys: {', '.join(metadata_keys)}")
                    
                    if count == 0:
                        all_good = False
                        
            except Exception as e:
                print(f"{RED}  ✗ Error: {e}{RESET}")
                all_good = False
        
        return all_good
        
    except ImportError:
        print(f"{RED}✗ ChromaDB not installed{RESET}")
        return False

def check_mcp_tool_requirements():
    """Check specific requirements for MCP tools."""
    print(f"\n{BLUE}=== MCP Tool Requirements ==={RESET}")
    
    checks = []
    
    # Dr. OFF MCP tool requirements
    print(f"\n{YELLOW}Dr. OFF Agent MCP Requirements:{RESET}")
    
    # Check OHIP schedule_benefits
    conn = sqlite3.connect('data/ohip.db')
    cursor = conn.cursor()
    
    # Check for specific columns used by MCP tools
    cursor.execute("PRAGMA table_info(schedule_benefits)")
    columns = [row[1] for row in cursor.fetchall()]
    required_cols = ['fee_code', 'description', 'fee_amount', 'effective_date']
    
    for col in required_cols:
        if col in columns:
            print(f"  {GREEN}✓{RESET} schedule_benefits.{col} exists")
            checks.append(True)
        else:
            print(f"  {RED}✗{RESET} schedule_benefits.{col} missing")
            checks.append(False)
    
    # Check ADP tables
    cursor.execute("SELECT COUNT(*) FROM adp_devices")
    adp_count = cursor.fetchone()[0]
    if adp_count > 0:
        print(f"  {GREEN}✓{RESET} ADP devices populated: {adp_count} records")
        checks.append(True)
    else:
        print(f"  {RED}✗{RESET} ADP devices empty")
        checks.append(False)
    
    # Check ODB formulary
    cursor.execute("SELECT COUNT(*) FROM odb_formulary")
    odb_count = cursor.fetchone()[0]
    if odb_count > 0:
        print(f"  {GREEN}✓{RESET} ODB formulary populated: {odb_count} records")
        checks.append(True)
    else:
        print(f"  {RED}✗{RESET} ODB formulary empty")
        checks.append(False)
    
    conn.close()
    
    # Dr. OPA MCP tool requirements
    print(f"\n{YELLOW}Dr. OPA Agent MCP Requirements:{RESET}")
    
    # Check if ChromaDB has required collections
    try:
        import chromadb
        client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
        collections = [c.name for c in client.list_collections()]
        
        required_collections = ['opa_sections', 'cep_tools']
        for col_name in required_collections:
            if col_name in collections:
                col = client.get_collection(col_name)
                count = col.count()
                print(f"  {GREEN}✓{RESET} Collection '{col_name}': {count} documents")
                checks.append(True)
            else:
                # Try alternate names
                found = False
                for actual_col in collections:
                    if col_name.split('_')[0] in actual_col.lower():
                        col = client.get_collection(actual_col)
                        count = col.count()
                        print(f"  {GREEN}✓{RESET} Collection '{actual_col}' (matches {col_name}): {count} documents")
                        checks.append(True)
                        found = True
                        break
                if not found:
                    print(f"  {YELLOW}⚠{RESET} Collection '{col_name}' not found (found: {', '.join(collections)})")
                    checks.append(False)
    except Exception as e:
        print(f"  {RED}✗{RESET} Could not check ChromaDB: {e}")
        checks.append(False)
    
    return all(checks)

def main():
    """Run all database validations."""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Database Validation Report{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    results = []
    
    # Check OHIP database
    results.append(("OHIP Database", check_ohip_database()))
    
    # Check conversation databases
    results.append(("Conversation DBs", check_conversation_databases()))
    
    # Check ChromaDB
    results.append(("ChromaDB", check_chroma_collections()))
    
    # Check MCP requirements
    results.append(("MCP Tools", check_mcp_tool_requirements()))
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Summary:{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    all_passed = True
    for name, passed in results:
        status = f"{GREEN}✓ PASSED{RESET}" if passed else f"{RED}✗ FAILED{RESET}"
        print(f"  {name}: {status}")
        all_passed = all_passed and passed
    
    if all_passed:
        print(f"\n{GREEN}✅ All database checks passed! Ready for deployment.{RESET}")
    else:
        print(f"\n{YELLOW}⚠️  Some checks failed. Review the issues above.{RESET}")
        print(f"{YELLOW}   The agents may still work, but some features might be limited.{RESET}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)