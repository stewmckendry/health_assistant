#!/usr/bin/env python3
"""
Migrate existing ChromaDB collections to Railway
Transfers actual vector store data from local ChromaDB to Railway
"""

import chromadb
import requests
import json
from pathlib import Path
from typing import Dict, List, Any
import argparse
import time
import logging
from datetime import datetime

class ChromaCollectionMigrator:
    """Migrate existing ChromaDB collections to Railway"""
    
    def __init__(self, railway_url: str = None, logger=None):
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
        self.logger = logger or logging.getLogger(__name__)
    
    def log(self, message: str, level="info"):
        """Log to both console and file"""
        print(message)
        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
    def migrate_collection(self, source_path: str, collection_name: str) -> bool:
        """Migrate a single collection from local ChromaDB to Railway"""
        
        self.log(f"\n🔄 Migrating collection: {collection_name}")
        self.log(f"   Source: {source_path}")
        
        try:
            # Connect to source ChromaDB
            client = chromadb.PersistentClient(path=source_path)
            collection = client.get_collection(collection_name)
            
            # Get collection count
            count = collection.count()
            self.log(f"   Documents to migrate: {count}")
            
            if count == 0:
                self.log(f"   ⚠️  Collection is empty, skipping", "warning")
                return False
            
            # ChromaDB doesn't support offset, so we get all at once
            # But we'll upload in batches to avoid timeouts
            self.log(f"   📥 Extracting all documents...")
            start_time = time.time()
            results = collection.get(
                include=["documents", "metadatas", "embeddings"]
                # No limit means get all documents
            )
            
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            ids = results.get("ids", [])
            extract_time = time.time() - start_time
            self.log(f"   ⏱️  Extraction took {extract_time:.1f}s")
            
            # Note: embeddings are already computed, but we'll let Railway recompute them
            # to ensure consistency with their OpenAI setup
            
            self.log(f"   📤 Uploading {len(documents)} documents to Railway...")
            upload_start = time.time()
            
            # Upload to Railway endpoint
            response = requests.post(
                f"{self.railway_url}/admin/direct-chroma-upload",
                json={
                    "collection_name": collection_name,
                    "documents": documents,
                    "metadatas": metadatas,
                    "ids": ids
                },
                timeout=1200  # 20 minutes for large collections
            )
            
            upload_time = time.time() - upload_start
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log(f"   ✅ Successfully migrated {result.get('documents_added', 0)} documents in {upload_time:.1f}s")
                    return True
                else:
                    self.log(f"   ❌ Migration failed: {result.get('message', 'Unknown error')}", "error")
                    return False
            else:
                self.log(f"   ❌ HTTP {response.status_code}: {response.text[:200]}", "error")
                return False
                
        except Exception as e:
            self.log(f"   ❌ Error: {e}", "error")
            return False
    
    def check_railway_collections(self) -> Dict[str, int]:
        """Get current collections on Railway"""
        try:
            response = requests.get(
                f"{self.railway_url}/admin/chroma-collections",
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return {col['name']: col['count'] for col in result.get('collections', [])}
            return {}
        except Exception as e:
            print(f"Error checking Railway collections: {e}")
            return {}

def main():
    parser = argparse.ArgumentParser(description="Migrate ChromaDB collections to Railway")
    parser.add_argument("--railway-url", default="https://healthassistant-production-3613.up.railway.app",
                       help="Railway app URL")
    parser.add_argument("--collection", help="Specific collection to migrate (optional)")
    parser.add_argument("--skip-existing", action="store_true", 
                       help="Skip collections that already exist on Railway")
    parser.add_argument("--log-file", default="chroma_migration.log",
                       help="Log file path (default: chroma_migration.log)")
    
    args = parser.parse_args()
    
    # Set up logging to file and console
    log_file = Path(args.log_file)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Create migrator with logger
    migrator = ChromaCollectionMigrator(args.railway_url, logger)
    
    # Log startup info
    logger.info("=" * 80)
    logger.info(f"🚀 ChromaDB Collection Migration to Railway - {datetime.now()}")
    logger.info(f"Railway URL: {args.railway_url}")
    logger.info(f"Log file: {log_file.absolute()}")
    logger.info("=" * 80)
    
    print(f"\n📝 Logging to: {log_file.absolute()}")
    print("   Monitor with: tail -f", log_file)
    print("=" * 80)
    
    # Check existing Railway collections
    print("\n📊 Current Railway collections:")
    railway_collections = migrator.check_railway_collections()
    if railway_collections:
        for name, count in railway_collections.items():
            print(f"  - {name}: {count} documents")
    else:
        print("  No collections found or unable to connect")
    
    # Define collections to migrate
    migrations = [
        # Dr. OFF collections (18,409 documents total)
        {
            "source_path": "data/dr_off_agent/processed/dr_off/chroma",
            "collections": [
                "ohip_documents",  # 6,983 documents
                "odb_documents",   # 10,815 documents  
                "adp_documents"    # 610 documents
                # Skip ohip_documents_cosine (only 1 doc, likely test)
            ]
        },
        # Dr. OPA collections (555 documents total)
        {
            "source_path": "data/dr_opa_agent/chroma",
            "collections": [
                "opa_cpso_corpus",  # 366 documents
                "opa_pho_corpus",   # 132 documents
                "opa_cep_corpus"    # 57 documents
            ]
        }
    ]
    
    # Filter collections if specific one requested
    if args.collection:
        print(f"\n🎯 Migrating only: {args.collection}")
        filtered_migrations = []
        for migration in migrations:
            if args.collection in migration["collections"]:
                migration["collections"] = [args.collection]
                filtered_migrations.append(migration)
        migrations = filtered_migrations
    
    print("\n🚀 Starting migrations...")
    total_collections = 0
    successful = 0
    skipped = 0
    failed = 0
    
    for migration in migrations:
        source_path = migration["source_path"]
        
        if not Path(source_path).exists():
            print(f"\n⚠️  Source path not found: {source_path}")
            continue
        
        print(f"\n📁 Source: {source_path}")
        
        for collection_name in migration["collections"]:
            total_collections += 1
            
            # Skip if already exists on Railway (if flag set)
            if args.skip_existing and collection_name in railway_collections:
                print(f"\n⏭️  Skipping {collection_name} (already exists with {railway_collections[collection_name]} docs)")
                skipped += 1
                continue
            
            # Migrate the collection
            success = migrator.migrate_collection(source_path, collection_name)
            
            if success:
                successful += 1
            else:
                failed += 1
            
            # Small delay between migrations to avoid overload
            time.sleep(2)
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Total collections: {total_collections}")
    print(f"✅ Successful: {successful}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    
    # Check final state
    print("\n📊 Final Railway collections:")
    final_collections = migrator.check_railway_collections()
    if final_collections:
        total_docs = 0
        for name, count in final_collections.items():
            print(f"  - {name}: {count} documents")
            total_docs += count
        print(f"\nTotal documents on Railway: {total_docs}")
    
    return 0 if successful > 0 else 1

if __name__ == "__main__":
    exit(main())