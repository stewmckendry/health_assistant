#!/usr/bin/env python3
"""
Upload JSON files and run ingestion on Railway using the ingestion pipelines
This is much simpler than trying to export/import ChromaDB data
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import argparse
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

class RailwayJSONIngester:
    """Upload and ingest JSON files on Railway using existing pipelines"""
    
    def __init__(self, railway_url: str = None):
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
        
    async def ingest_single_file(self, session: aiohttp.ClientSession, 
                                file_path: Path, agent_type: str) -> Dict[str, Any]:
        """Upload and ingest a single JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Determine collection name from file path
            filename = file_path.name.lower()
            if "adp" in filename:
                collection_name = "adp_documents"
            elif "odb" in filename:
                collection_name = "odb_documents"  
            elif "ohip" in filename:
                collection_name = "ohip_documents"
            elif "cpso" in str(file_path).lower():
                collection_name = "opa_cpso_corpus"
            elif "cep" in str(file_path).lower():
                collection_name = "opa_cep_corpus"
            elif "pho" in str(file_path).lower():
                collection_name = "opa_pho_corpus"
            else:
                collection_name = "default_collection"
            
            print(f"  📤 Ingesting {file_path.name} -> {collection_name}")
            
            payload = {
                "agent_type": agent_type,
                "json_data": json_data,
                "collection_name": collection_name,
                "source_org": self._extract_source_org(file_path)
            }
            
            async with session.post(
                f"{self.railway_url}/admin/ingest-json",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=600)  # 10 minute timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    count = result.get("sections_ingested") or result.get("documents_ingested", 0)
                    print(f"    ✅ Success: {count} items ingested")
                    return {"success": True, "count": count, "file": file_path.name, "collection": collection_name}
                else:
                    error_text = await response.text()
                    print(f"    ❌ Failed: HTTP {response.status}")
                    print(f"      {error_text[:200]}...")
                    return {"success": False, "error": f"HTTP {response.status}", "file": file_path.name}
                    
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return {"success": False, "error": str(e), "file": file_path.name}
    
    def _extract_source_org(self, file_path: Path) -> str:
        """Extract source organization from file path"""
        path_str = str(file_path).lower()
        if "cpso" in path_str:
            return "cpso"
        elif "cep" in path_str:
            return "ontario_health"
        elif "pho" in path_str:
            return "pho"
        elif "dr_off" in path_str:
            return "moh"
        else:
            return "generic"
    
    async def bulk_ingest_directory(self, directory: Path, agent_type: str, 
                                   pattern: str = "*.json") -> Dict[str, Any]:
        """Bulk ingest all JSON files in a directory"""
        json_files = list(directory.glob(pattern))
        
        if not json_files:
            print(f"⚠️  No JSON files found in {directory} with pattern {pattern}")
            return {"success": False, "message": "No files found"}
        
        print(f"🚀 Starting bulk ingestion for {agent_type}")
        print(f"   Directory: {directory}")
        print(f"   Files found: {len(json_files)}")
        print("=" * 60)
        
        results = []
        total_items = 0
        
        async with aiohttp.ClientSession() as session:
            for file_path in json_files:
                result = await self.ingest_single_file(session, file_path, agent_type)
                results.append(result)
                if result.get("success"):
                    total_items += result.get("count", 0)
        
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful
        
        print("\n" + "=" * 60)
        print("📊 INGESTION SUMMARY")
        print("=" * 60)
        print(f"Files processed: {len(json_files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total items ingested: {total_items}")
        
        if failed > 0:
            print("\n❌ Failed files:")
            for r in results:
                if not r.get("success"):
                    print(f"  - {r['file']}: {r.get('error', 'Unknown error')}")
        
        print("\n✅ Collections created:")
        collections = set(r.get("collection") for r in results if r.get("success") and r.get("collection"))
        for collection in sorted(collections):
            count = sum(r.get("count", 0) for r in results 
                       if r.get("success") and r.get("collection") == collection)
            print(f"  - {collection}: {count} items")
        
        return {
            "success": successful > 0,
            "files_processed": len(json_files),
            "successful": successful,
            "failed": failed,
            "total_items": total_items,
            "collections": list(collections),
            "results": results
        }

async def main():
    parser = argparse.ArgumentParser(description="Upload JSON files and run ingestion on Railway")
    parser.add_argument("--agent", choices=["dr_off", "dr_opa", "both"], default="both",
                       help="Which agent to ingest data for")
    parser.add_argument("--railway-url", default="https://healthassistant-production-3613.up.railway.app",
                       help="Railway app URL")
    parser.add_argument("--pattern", default="*.json", help="File pattern to match")
    
    args = parser.parse_args()
    
    ingester = RailwayJSONIngester(args.railway_url)
    
    print("🚀 Railway JSON Ingestion")
    print(f"Railway URL: {args.railway_url}")
    print(f"Agent(s): {args.agent}")
    print("=" * 80)
    
    # Define ingestion tasks
    tasks = []
    
    if args.agent in ["dr_off", "both"]:
        # Dr. OFF agent - ADP data
        adp_dir = Path("data/processed/dr_off/adp")
        if adp_dir.exists():
            tasks.append(("dr_off", adp_dir, "adp_focused_extraction_llm.json"))
        else:
            print(f"⚠️  Dr. OFF directory not found: {adp_dir}")
    
    if args.agent in ["dr_opa", "both"]:
        # Dr. OPA agent - CPSO, CEP, PHO data
        opa_dirs = [
            ("data/dr_opa_agent/processed/cpso", "*.json"),
            ("data/dr_opa_agent/processed/cep", "*_extracted.json"),
            ("data/dr_opa_agent/processed/pho", "*.json")
        ]
        
        for dir_path, pattern in opa_dirs:
            dir_obj = Path(dir_path)
            if dir_obj.exists():
                tasks.append(("dr_opa", dir_obj, pattern))
            else:
                print(f"⚠️  Dr. OPA directory not found: {dir_obj}")
    
    if not tasks:
        print("❌ No valid directories found for ingestion")
        return 1
    
    # Execute ingestion tasks
    overall_success = True
    for agent_type, directory, file_pattern in tasks:
        print(f"\n🔄 Processing {agent_type} data from {directory}")
        
        if file_pattern.endswith(".json") and not "*" in file_pattern:
            # Single specific file
            file_path = directory / file_pattern
            if file_path.exists():
                async with aiohttp.ClientSession() as session:
                    result = await ingester.ingest_single_file(session, file_path, agent_type)
                    if not result.get("success"):
                        overall_success = False
            else:
                print(f"⚠️  File not found: {file_path}")
                overall_success = False
        else:
            # Directory with pattern
            result = await ingester.bulk_ingest_directory(directory, agent_type, file_pattern)
            if not result.get("success"):
                overall_success = False
    
    print(f"\n🎯 Overall ingestion: {'✅ Success' if overall_success else '❌ Some failures'}")
    return 0 if overall_success else 1

if __name__ == "__main__":
    asyncio.run(main())