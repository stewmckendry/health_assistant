#!/usr/bin/env python3
"""
Fixed Data Migration Script to Railway
Handles serialization issues and SQLite internal tables
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
import requests
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import argparse
from typing import Dict, List, Any, Optional
import numpy as np
from decimal import Decimal

# Load environment variables
load_dotenv()

def safe_json_serialize(obj):
    """Safely serialize objects that may contain numpy arrays or other non-serializable types"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (list, tuple)):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: safe_json_serialize(value) for key, value in obj.items()}
    else:
        return obj

class DatabaseMigrator:
    """Migrates SQLite and ChromaDB data to Railway with proper serialization"""
    
    def __init__(self, railway_url: str = None):
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
        self.export_dir = Path("data_exports")
        self.export_dir.mkdir(exist_ok=True)
        
        # Tables to skip (SQLite internal tables)
        self.skip_tables = {'sqlite_sequence', 'sqlite_master', 'sqlite_temp_master'}
        
    def export_sqlite_data(self, db_path: str, export_name: str) -> Dict[str, Any]:
        """Export SQLite database to JSON with proper serialization"""
        print(f"Exporting SQLite database: {db_path}")
        
        if not Path(db_path).exists():
            print(f"  ⚠️  Database not found: {db_path}")
            return {"tables": {}, "metadata": {"source": db_path, "found": False}}
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        export_data = {
            "metadata": {
                "source": db_path,
                "export_name": export_name,
                "found": True
            },
            "tables": {}
        }
        
        # Get all table names (excluding internal SQLite tables)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"  Found {len(tables)} tables: {tables}")
        
        # Export each table
        for table in tables:
            if table in self.skip_tables:
                print(f"    ⏭️  Skipping internal table: {table}")
                continue
                
            try:
                cursor = conn.execute(f"SELECT * FROM {table}")
                rows = []
                for row in cursor.fetchall():
                    # Convert row to dict and serialize safely
                    row_dict = dict(row)
                    safe_row = safe_json_serialize(row_dict)
                    rows.append(safe_row)
                
                export_data["tables"][table] = rows
                print(f"    ✓ {table}: {len(rows)} rows")
            except Exception as e:
                print(f"    ❌ Error exporting {table}: {e}")
                export_data["tables"][table] = []
        
        conn.close()
        
        # Save to file with safe serialization
        export_file = self.export_dir / f"{export_name}.json"
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=safe_json_serialize)
        
        print(f"  ✓ Exported to: {export_file}")
        return export_data
    
    def export_chroma_data(self, chroma_path: str, collection_name: str, export_name: str) -> Dict[str, Any]:
        """Export ChromaDB collection to JSON with proper serialization"""
        print(f"Exporting ChromaDB: {chroma_path}/{collection_name}")
        
        if not Path(chroma_path).exists():
            print(f"  ⚠️  ChromaDB not found: {chroma_path}")
            return {"documents": [], "metadata": {"source": chroma_path, "found": False}}
        
        try:
            # Initialize ChromaDB client
            client = chromadb.PersistentClient(path=chroma_path)
            
            # Check if collection exists
            try:
                collection = client.get_collection(collection_name)
            except Exception as e:
                print(f"  ⚠️  Collection '{collection_name}' not found: {e}")
                return {"documents": [], "metadata": {"source": chroma_path, "found": False, "error": str(e)}}
            
            # Get all data from collection
            results = collection.get(include=["documents", "metadatas", "embeddings"])
            
            # Safely serialize embeddings (numpy arrays)
            safe_embeddings = safe_json_serialize(results.get("embeddings", []))
            safe_metadatas = safe_json_serialize(results.get("metadatas", []))
            
            export_data = {
                "metadata": {
                    "source": chroma_path,
                    "collection_name": collection_name,
                    "export_name": export_name,
                    "found": True,
                    "count": len(results["documents"])
                },
                "documents": results["documents"],
                "metadatas": safe_metadatas,
                "embeddings": safe_embeddings,
                "ids": results["ids"]
            }
            
            print(f"  ✓ Exported {len(results['documents'])} documents")
            
            # Save to file
            export_file = self.export_dir / f"{export_name}_chroma.json"
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=safe_json_serialize)
            
            print(f"  ✓ Exported to: {export_file}")
            return export_data
            
        except Exception as e:
            print(f"  ❌ Error exporting ChromaDB: {e}")
            return {"documents": [], "metadata": {"source": chroma_path, "found": False, "error": str(e)}}
    
    def load_to_railway_sqlite(self, export_data: Dict[str, Any], target_db: str) -> bool:
        """Load exported data to Railway SQLite database via API"""
        print(f"Loading data to Railway database: {target_db}")
        
        if not export_data["metadata"]["found"]:
            print(f"  ⚠️  No data to load (source not found)")
            return False
        
        # Filter out empty tables and SQLite internal tables
        filtered_tables = {}
        for table_name, rows in export_data["tables"].items():
            if table_name in self.skip_tables:
                print(f"    ⏭️  Skipping internal table: {table_name}")
                continue
            if rows:  # Only include tables with data
                filtered_tables[table_name] = rows
            else:
                print(f"    ⏭️  Skipping empty table: {table_name}")
        
        if not filtered_tables:
            print(f"  ⚠️  No tables with data to load")
            return False
        
        try:
            # Send data to Railway API endpoint for database loading
            response = requests.post(
                f"{self.railway_url}/admin/load-database",
                json={
                    "target_db": target_db,
                    "tables": filtered_tables,
                    "metadata": export_data["metadata"]
                },
                timeout=300,  # 5 minutes timeout for large data loads
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ Successfully loaded to Railway")
                print(f"    Tables loaded: {result.get('tables_loaded', 'unknown')}")
                print(f"    Total rows: {result.get('total_rows', 'unknown')}")
                return True
            else:
                print(f"  ❌ Failed to load: HTTP {response.status_code}")
                print(f"    Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error loading to Railway: {e}")
            return False
    
    def load_to_railway_chroma(self, export_data: Dict[str, Any], collection_name: str) -> bool:
        """Load exported ChromaDB data to Railway via API"""
        print(f"Loading ChromaDB data to Railway: {collection_name}")
        
        if not export_data["metadata"]["found"]:
            print(f"  ⚠️  No data to load (source not found)")
            return False
        
        if not export_data["documents"]:
            print(f"  ⚠️  No documents to load")
            return False
        
        try:
            # Send data to Railway API endpoint for ChromaDB loading
            response = requests.post(
                f"{self.railway_url}/admin/load-chroma",
                json={
                    "collection_name": collection_name,
                    "documents": export_data["documents"],
                    "metadatas": export_data["metadatas"],
                    "embeddings": export_data["embeddings"],
                    "ids": export_data["ids"],
                    "metadata": export_data["metadata"]
                },
                timeout=600,  # 10 minutes timeout for large vector loads
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ Successfully loaded ChromaDB to Railway")
                print(f"    Documents loaded: {result.get('documents_loaded', 'unknown')}")
                return True
            else:
                print(f"  ❌ Failed to load: HTTP {response.status_code}")
                print(f"    Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error loading ChromaDB to Railway: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Migrate databases to Railway (Fixed Version)")
    parser.add_argument("--export-only", action="store_true", help="Only export data, don't load to Railway")
    parser.add_argument("--load-only", action="store_true", help="Only load to Railway (assumes exports exist)")
    parser.add_argument("--railway-url", help="Railway app URL", default="https://healthassistant-production-3613.up.railway.app")
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator(args.railway_url)
    
    print("🚀 Starting FIXED database migration to Railway")
    print(f"Railway URL: {args.railway_url}")
    print("=" * 80)
    
    # Database configurations - only include existing databases
    databases_to_migrate = [
        # Core databases that we know exist
        {"path": "data/ohip.db", "name": "ohip_fixed", "target": "ohip.db"},
        {"path": "data/dr_off_conversations.db", "name": "dr_off_conversations_fixed", "target": "dr_off_conversations.db"},
        {"path": "data/dr_opa_conversations.db", "name": "dr_opa_conversations_fixed", "target": "dr_opa_conversations.db"},
        {"path": "data/orchestrator_conversations.db", "name": "orchestrator_conversations_fixed", "target": "orchestrator_conversations.db"},
        {"path": "data/dr_opa_agent/opa.db", "name": "dr_opa_agent_fixed", "target": "dr_opa_agent/opa.db"},
    ]
    
    # ChromaDB configurations - only include collections that exist
    chroma_to_migrate = [
        {"path": "data/dr_off_agent/processed/dr_off/chroma", "collection": "odb_documents", "name": "dr_off_odb_fixed"},
    ]
    
    export_results = {}
    
    # Export phase
    if not args.load_only:
        print("\n📤 EXPORT PHASE (FIXED)")
        print("-" * 40)
        
        # Export SQLite databases
        for db_config in databases_to_migrate:
            result = migrator.export_sqlite_data(db_config["path"], db_config["name"])
            export_results[db_config["name"]] = result
        
        # Export ChromaDB collections
        for chroma_config in chroma_to_migrate:
            result = migrator.export_chroma_data(
                chroma_config["path"], 
                chroma_config["collection"], 
                chroma_config["name"]
            )
            export_results[f"{chroma_config['name']}_chroma"] = result
    
    # Load phase
    if not args.export_only:
        print("\n📥 LOAD PHASE (FIXED)")
        print("-" * 40)
        
        success_count = 0
        total_count = 0
        
        # Load SQLite databases to Railway
        for db_config in databases_to_migrate:
            total_count += 1
            if args.load_only:
                # Load from existing export file
                export_file = migrator.export_dir / f"{db_config['name']}.json"
                if export_file.exists():
                    with open(export_file) as f:
                        export_data = json.load(f)
                else:
                    print(f"  ⚠️  Export file not found: {export_file}")
                    continue
            else:
                export_data = export_results.get(db_config["name"], {})
            
            if migrator.load_to_railway_sqlite(export_data, db_config["target"]):
                success_count += 1
        
        # Load ChromaDB collections to Railway
        for chroma_config in chroma_to_migrate:
            total_count += 1
            export_key = f"{chroma_config['name']}_chroma"
            
            if args.load_only:
                # Load from existing export file
                export_file = migrator.export_dir / f"{chroma_config['name']}_chroma.json"
                if export_file.exists():
                    with open(export_file) as f:
                        export_data = json.load(f)
                else:
                    print(f"  ⚠️  Export file not found: {export_file}")
                    continue
            else:
                export_data = export_results.get(export_key, {})
            
            if migrator.load_to_railway_chroma(export_data, chroma_config["collection"]):
                success_count += 1
        
        print(f"\n🎯 Migration Summary: {success_count}/{total_count} successful")
    
    print("\n✅ Fixed migration process completed!")

if __name__ == "__main__":
    main()