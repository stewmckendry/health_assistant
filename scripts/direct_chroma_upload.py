#!/usr/bin/env python3
"""
Direct ChromaDB upload to Railway using simplified endpoint
Extracts documents from JSON files and uploads directly
"""

import json
import requests
from pathlib import Path
from typing import List, Dict, Any
import argparse

class DirectChromaUploader:
    """Upload documents directly to ChromaDB on Railway"""
    
    def __init__(self, railway_url: str = None):
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
    
    def extract_documents_from_json(self, json_file: Path) -> Dict[str, List]:
        """Extract documents and metadata from JSON files"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        documents = []
        metadatas = []
        ids = []
        
        # Handle different JSON structures
        if isinstance(data, dict):
            # ADP structure - has 'sections' key
            if 'sections' in data:
                for i, section in enumerate(data['sections']):
                    # Create document text from section
                    doc_text = f"{section.get('title', '')}\n{section.get('content', '')}"
                    documents.append(doc_text)
                    
                    # Create metadata
                    metadata = {
                        'source': section.get('adp_doc', 'unknown'),
                        'section': section.get('section', ''),
                        'title': section.get('title', ''),
                        'page': str(section.get('page', 0))
                    }
                    metadatas.append(metadata)
                    ids.append(f"adp_{i}")
            
            # CPSO/CEP structure - has different keys
            elif 'content' in data or 'text' in data:
                doc_text = data.get('content') or data.get('text', '')
                documents.append(doc_text)
                
                metadata = {
                    'source': data.get('source_url', ''),
                    'title': data.get('title', ''),
                    'type': data.get('document_type', 'unknown')
                }
                metadatas.append(metadata)
                ids.append(f"doc_0")
            
            # Handle chunks if present
            elif 'chunks' in data:
                for i, chunk in enumerate(data['chunks']):
                    documents.append(chunk.get('text', ''))
                    metadatas.append(chunk.get('metadata', {}))
                    ids.append(f"chunk_{i}")
        
        elif isinstance(data, list):
            # Handle list of documents
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    doc_text = item.get('content') or item.get('text', '')
                    documents.append(doc_text)
                    
                    metadata = {
                        'source': item.get('source', ''),
                        'title': item.get('title', ''),
                        'index': str(i)
                    }
                    metadatas.append(metadata)
                    ids.append(f"doc_{i}")
        
        return {
            'documents': documents,
            'metadatas': metadatas,
            'ids': ids
        }
    
    def upload_collection(self, collection_name: str, json_files: List[Path]) -> bool:
        """Upload documents from JSON files to a ChromaDB collection"""
        
        all_documents = []
        all_metadatas = []
        all_ids = []
        
        # Extract documents from all files
        for json_file in json_files:
            try:
                extracted = self.extract_documents_from_json(json_file)
                
                # Add file-specific prefix to IDs to ensure uniqueness
                file_prefix = json_file.stem[:20]
                for i, doc_id in enumerate(extracted['ids']):
                    extracted['ids'][i] = f"{file_prefix}_{doc_id}"
                
                all_documents.extend(extracted['documents'])
                all_metadatas.extend(extracted['metadatas'])
                all_ids.extend(extracted['ids'])
                
                print(f"  ✓ Extracted {len(extracted['documents'])} documents from {json_file.name}")
            except Exception as e:
                print(f"  ❌ Error extracting from {json_file.name}: {e}")
        
        if not all_documents:
            print(f"  ⚠️  No documents extracted for {collection_name}")
            return False
        
        print(f"  📤 Uploading {len(all_documents)} documents to {collection_name}")
        
        # Upload to Railway
        try:
            response = requests.post(
                f"{self.railway_url}/admin/direct-chroma-upload",
                json={
                    "collection_name": collection_name,
                    "documents": all_documents,
                    "metadatas": all_metadatas,
                    "ids": all_ids
                },
                timeout=600  # 10 minute timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"  ✅ Successfully uploaded {result.get('documents_added', 0)} documents")
                    return True
                else:
                    print(f"  ❌ Upload failed: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"  ❌ Upload error: {e}")
            return False
    
    def check_collections(self) -> Dict[str, Any]:
        """Check existing ChromaDB collections on Railway"""
        try:
            response = requests.get(
                f"{self.railway_url}/admin/chroma-collections",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Direct ChromaDB upload to Railway")
    parser.add_argument("--railway-url", default="https://healthassistant-production-3613.up.railway.app",
                       help="Railway app URL")
    parser.add_argument("--check-only", action="store_true", help="Only check existing collections")
    
    args = parser.parse_args()
    
    uploader = DirectChromaUploader(args.railway_url)
    
    print("🚀 Direct ChromaDB Upload to Railway")
    print(f"Railway URL: {args.railway_url}")
    print("=" * 80)
    
    # Check existing collections
    print("\n📊 Checking existing collections...")
    collections = uploader.check_collections()
    if collections.get("success"):
        print(f"Found {collections.get('total_collections', 0)} collections:")
        for col in collections.get("collections", []):
            print(f"  - {col['name']}: {col['count']} documents")
    else:
        print(f"  ❌ Could not check collections: {collections.get('error', 'Unknown error')}")
    
    if args.check_only:
        return 0
    
    # Define upload tasks
    upload_tasks = [
        # Dr. OFF - ADP documents
        {
            "collection_name": "adp_documents",
            "files": [Path("data/processed/dr_off/adp/adp_focused_extraction_llm.json")]
        },
        
        # Dr. OPA - CPSO corpus (select key files)
        {
            "collection_name": "opa_cpso_corpus",
            "files": list(Path("data/dr_opa_agent/processed/cpso").glob("*prescribing*.json"))[:10]  # Start with 10 files
        },
        
        # Dr. OPA - CEP corpus (select key files)
        {
            "collection_name": "opa_cep_corpus", 
            "files": list(Path("data/dr_opa_agent/processed/cep").glob("*_extracted.json"))[:10]  # Start with 10 files
        }
    ]
    
    print("\n📤 Starting uploads...")
    successful = 0
    failed = 0
    
    for task in upload_tasks:
        collection_name = task["collection_name"]
        files = [f for f in task["files"] if f.exists()]
        
        if not files:
            print(f"\n⚠️  No files found for {collection_name}")
            failed += 1
            continue
        
        print(f"\n🔄 Processing {collection_name} ({len(files)} files)")
        
        if uploader.upload_collection(collection_name, files):
            successful += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print("📊 UPLOAD SUMMARY")
    print("=" * 80)
    print(f"Successful collections: {successful}")
    print(f"Failed collections: {failed}")
    
    # Check final status
    print("\n📊 Final collection status:")
    collections = uploader.check_collections()
    if collections.get("success"):
        for col in collections.get("collections", []):
            print(f"  - {col['name']}: {col['count']} documents")
    
    return 0 if successful > 0 else 1

if __name__ == "__main__":
    exit(main())