#!/usr/bin/env python3
"""
Async parallel ChromaDB migration to Railway
Handles large vector store uploads with multiple workers
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path
import chromadb
from dotenv import load_dotenv
import argparse
import numpy as np
from typing import List, Dict, Any
import time

# Load environment variables
load_dotenv()

class AsyncChromaMigrator:
    """Async ChromaDB migrator with parallel workers"""
    
    def __init__(self, railway_url: str = None, max_workers: int = 3):
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
        self.max_workers = max_workers
        self.batch_size = 250  # Smaller batches for parallel processing
        self.export_dir = Path("data_exports")
        self.export_dir.mkdir(exist_ok=True)
        
    def safe_json_serialize(self, obj):
        """Handle numpy arrays and invalid floats in JSON serialization"""
        try:
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float32, np.float64)):
                val = float(obj)
                if np.isnan(val) or np.isinf(val):
                    return None
                return val
            elif isinstance(obj, float):
                if np.isnan(obj) or np.isinf(obj):
                    return None
                return obj
            return obj
        except Exception:
            return str(obj)
    
    def export_chroma_collection(self, chroma_path: str, collection_name: str, export_name: str) -> Dict[str, Any]:
        """Export ChromaDB collection to JSON with proper serialization"""
        print(f"Exporting ChromaDB: {chroma_path}/{collection_name}")
        
        if not Path(chroma_path).exists():
            print(f"  ⚠️  ChromaDB not found: {chroma_path}")
            return {"documents": [], "metadata": {"source": chroma_path, "found": False}}
        
        try:
            # Initialize ChromaDB client
            client = chromadb.PersistentClient(path=chroma_path)
            collection = client.get_collection(collection_name)
            
            # Get all data from collection
            results = collection.get(include=["documents", "metadatas", "embeddings"])
            
            # Clean embeddings data
            cleaned_embeddings = []
            if results["embeddings"] is not None and len(results["embeddings"]) > 0:
                try:
                    for embedding in results["embeddings"]:
                        if embedding is not None:
                            # Convert numpy array or list to clean list
                            if hasattr(embedding, 'tolist'):
                                cleaned_embedding = embedding.tolist()
                            elif isinstance(embedding, list):
                                cleaned_embedding = [
                                    float(val) if not (np.isnan(float(val)) or np.isinf(float(val))) else 0.0 
                                    for val in embedding
                                ]
                            else:
                                cleaned_embedding = []
                            cleaned_embeddings.append(cleaned_embedding)
                        else:
                            cleaned_embeddings.append([])
                except Exception as e:
                    print(f"    ⚠️  Error cleaning embeddings, skipping: {e}")
                    cleaned_embeddings = []
            
            export_data = {
                "metadata": {
                    "source": chroma_path,
                    "collection_name": collection_name,
                    "export_name": export_name,
                    "found": True,
                    "count": len(results["documents"])
                },
                "documents": results["documents"],
                "metadatas": results["metadatas"],
                "embeddings": cleaned_embeddings,
                "ids": results["ids"]
            }
            
            print(f"  ✓ Exported {len(results['documents'])} documents")
            
            # Save to file
            export_file = self.export_dir / f"{export_name}_chroma.json"
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=self.safe_json_serialize)
            
            print(f"  ✓ Exported to: {export_file}")
            return export_data
            
        except Exception as e:
            print(f"  ❌ Error exporting ChromaDB: {e}")
            return {"documents": [], "metadata": {"source": chroma_path, "found": False, "error": str(e)}}
    
    async def upload_chroma_batch(self, session: aiohttp.ClientSession, collection_name: str, 
                                 batch_data: Dict[str, List], batch_num: int) -> bool:
        """Upload a single batch of ChromaDB data"""
        try:
            batch_size = len(batch_data["documents"])
            print(f"  🔄 Worker uploading batch {batch_num}: {batch_size} documents")
            
            payload = {
                "collection_name": collection_name,
                "documents": batch_data["documents"],
                "metadatas": batch_data["metadatas"],
                "embeddings": batch_data["embeddings"],
                "ids": batch_data["ids"],
                "metadata": {
                    "batch_num": batch_num,
                    "batch_size": batch_size
                }
            }
            
            async with session.post(
                f"{self.railway_url}/admin/load-chroma",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes per batch
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"  ✅ Batch {batch_num} uploaded: {result.get('documents_loaded', 0)} documents")
                    return True
                else:
                    error_text = await response.text()
                    print(f"  ❌ Batch {batch_num} failed: HTTP {response.status}")
                    print(f"    Response: {error_text[:200]}...")
                    return False
                    
        except asyncio.TimeoutError:
            print(f"  ⏰ Batch {batch_num} timed out")
            return False
        except Exception as e:
            print(f"  ❌ Batch {batch_num} error: {e}")
            return False
    
    async def upload_chroma_parallel(self, export_data: Dict[str, Any], collection_name: str) -> bool:
        """Upload ChromaDB data with parallel workers"""
        print(f"🚀 Starting parallel upload for {collection_name}")
        
        if not export_data["metadata"]["found"]:
            print(f"  ⚠️  No data to upload (source not found)")
            return False
        
        documents = export_data["documents"]
        metadatas = export_data["metadatas"]
        embeddings = export_data["embeddings"]
        ids = export_data["ids"]
        
        total_docs = len(documents)
        print(f"  📊 Total documents: {total_docs}")
        print(f"  🔧 Batch size: {self.batch_size}")
        print(f"  👥 Workers: {self.max_workers}")
        
        # Create batches
        batches = []
        for i in range(0, total_docs, self.batch_size):
            batch_end = min(i + self.batch_size, total_docs)
            batch_data = {
                "documents": documents[i:batch_end],
                "metadatas": metadatas[i:batch_end],
                "embeddings": embeddings[i:batch_end] if embeddings else [[] for _ in range(batch_end - i)],
                "ids": ids[i:batch_end]
            }
            batches.append((i // self.batch_size + 1, batch_data))
        
        print(f"  📦 Created {len(batches)} batches")
        
        # Upload batches with parallel workers
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(self.max_workers)
            
            async def upload_with_semaphore(batch_num, batch_data):
                async with semaphore:
                    return await self.upload_chroma_batch(session, collection_name, batch_data, batch_num)
            
            # Execute all batches
            start_time = time.time()
            results = await asyncio.gather(
                *[upload_with_semaphore(batch_num, batch_data) for batch_num, batch_data in batches],
                return_exceptions=True
            )
            end_time = time.time()
            
            # Calculate results
            successful = sum(1 for r in results if r is True)
            failed = len(results) - successful
            
            print(f"\n📈 Upload Summary:")
            print(f"  ✅ Successful batches: {successful}/{len(batches)}")
            print(f"  ❌ Failed batches: {failed}")
            print(f"  ⏱️  Total time: {end_time - start_time:.1f}s")
            
            return successful > 0 and failed == 0

async def main():
    parser = argparse.ArgumentParser(description="Async ChromaDB migration to Railway")
    parser.add_argument("--railway-url", help="Railway app URL", 
                       default="https://healthassistant-production-3613.up.railway.app")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel workers")
    parser.add_argument("--batch-size", type=int, default=250, help="Batch size for uploads")
    parser.add_argument("--export-only", action="store_true", help="Only export, don't upload")
    
    args = parser.parse_args()
    
    migrator = AsyncChromaMigrator(args.railway_url, args.workers)
    migrator.batch_size = args.batch_size
    
    print("🚀 Starting async ChromaDB migration to Railway")
    print(f"Railway URL: {args.railway_url}")
    print(f"Workers: {args.workers}")
    print(f"Batch size: {args.batch_size}")
    print("=" * 80)
    
    # ChromaDB configurations to migrate - prioritizing largest collections first
    chroma_to_migrate = [
        # Largest collection first - 10,815 documents
        {
            "path": "data/dr_off_agent/processed/dr_off/chroma", 
            "collection": "odb_documents", 
            "name": "dr_off_odb_documents"
        },
        # Second largest - 6,983 documents
        {
            "path": "data/dr_off_agent/processed/dr_off/chroma", 
            "collection": "ohip_documents", 
            "name": "dr_off_ohip_documents"
        },
        # ADP documents - 610 documents
        {
            "path": "data/dr_off_agent/processed/dr_off/chroma", 
            "collection": "adp_documents", 
            "name": "dr_off_adp_documents"
        },
        {
            "path": "data/processed/dr_off/chroma", 
            "collection": "adp_v1", 
            "name": "dr_off_adp_v1"
        },
        # OPA collections
        {
            "path": "data/processed/dr_opa/chroma", 
            "collection": "opa_cep_corpus", 
            "name": "dr_opa_cep_corpus"
        },
        {
            "path": "data/dr_opa_agent/chroma", 
            "collection": "opa_cpso_corpus", 
            "name": "dr_opa_cpso_corpus"
        },
        {
            "path": "data/dr_opa_agent/chroma", 
            "collection": "opa_pho_corpus", 
            "name": "dr_opa_pho_corpus"
        },
        {
            "path": "data/processed/dr_opa/chroma", 
            "collection": "opa_pho_corpus", 
            "name": "dr_opa_pho_processed"
        },
        {
            "path": "data/dr_opa_agent/chroma", 
            "collection": "opa_cep_corpus", 
            "name": "dr_opa_cep_agent"
        }
    ]
    
    for chroma_config in chroma_to_migrate:
        print(f"\n🔄 Processing {chroma_config['name']}")
        
        # Export phase
        export_data = migrator.export_chroma_collection(
            chroma_config["path"],
            chroma_config["collection"],
            chroma_config["name"]
        )
        
        if not args.export_only and export_data["metadata"]["found"]:
            # Upload phase
            success = await migrator.upload_chroma_parallel(
                export_data,
                chroma_config["collection"]
            )
            
            if success:
                print(f"  ✅ Successfully migrated {chroma_config['name']}")
            else:
                print(f"  ❌ Failed to migrate {chroma_config['name']}")
        
    print("\n🎯 Async ChromaDB migration completed!")

if __name__ == "__main__":
    asyncio.run(main())