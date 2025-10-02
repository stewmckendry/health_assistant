#!/usr/bin/env python3
"""
Ingest Choosing Wisely recommendations into Chroma vector database.
Supports both local Chroma and Railway deployment.
"""

import os
import sys
import json
import logging
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import argparse

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import chromadb
from chromadb.config import Settings
from openai import OpenAI

# Configure logging to both console and file
log_dir = Path("logs/choosing_wisely")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"ingestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to: {log_file}")


class ChoosingWiselyIngester:
    """Unified ingester for Choosing Wisely recommendations."""
    
    # Chunking parameters
    CHUNK_SIZE = 1000  # Characters per chunk
    CHUNK_OVERLAP = 200  # Overlap between chunks
    BATCH_SIZE = 100  # Embeddings per batch
    
    def __init__(
        self,
        mode: str = "local",
        chroma_path: Optional[str] = None,
        railway_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        collection_name: str = "choosing_wisely_recommendations"
    ):
        """Initialize Choosing Wisely ingester.
        
        Args:
            mode: "local" for local Chroma, "railway" for Railway endpoint
            chroma_path: Path to local Chroma database (for local mode)
            railway_url: Railway app URL (for railway mode)
            openai_api_key: OpenAI API key for embeddings (local mode only)
            collection_name: Name of Chroma collection (local mode only)
        """
        self.mode = mode
        self.collection_name = collection_name
        
        if mode == "local":
            self._init_local(chroma_path, openai_api_key, collection_name)
        elif mode == "railway":
            self._init_railway(railway_url)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'local' or 'railway'")
    
    def _init_local(self, chroma_path: str, openai_api_key: str, collection_name: str):
        """Initialize for local Chroma ingestion."""
        # Initialize OpenAI client for embeddings
        self.openai_client = None
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        elif os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI()
        else:
            logger.warning("No OpenAI API key provided - embeddings will not be generated")
        
        # Initialize local Chroma client
        chroma_path = chroma_path or "data/dr_opa_agent/chroma"
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info(f"Using local Chroma at {chroma_path}")
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name
        )
        logger.info(f"Using collection: {collection_name}")
    
    def _init_railway(self, railway_url: str):
        """Initialize for Railway ingestion."""
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
        logger.info(f"Using Railway URL: {self.railway_url}")
    
    # ==================== LOCAL INGESTION METHODS ====================
    
    def create_chunks_from_recommendation(
        self, 
        recommendation: Dict[str, Any], 
        specialty_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create chunks from a single recommendation (local mode)."""
        chunks = []
        
        # Create recommendation text
        rec_number = recommendation.get('number', 'N/A')
        rec_title = recommendation.get('title', '')
        rec_desc = recommendation.get('description', '')
        
        rec_text = f"Recommendation #{rec_number}: {rec_title}\n\n"
        rec_text += f"{rec_desc}"
        
        # Add references if present
        references = recommendation.get('references', [])
        if references:
            rec_text += f"\n\nReferences:\n"
            for ref in references:
                rec_text += f"- {ref}\n"
        
        # Create metadata for this recommendation
        metadata = {
            **specialty_metadata,
            'recommendation_number': recommendation.get('number'),
            'recommendation_title': recommendation.get('title', ''),
            'has_references': len(references) > 0,
            'reference_count': len(references),
            'chunk_type': 'recommendation',
            'text_length': len(rec_text)
        }
        
        # If text is short enough, create single chunk
        if len(rec_text) <= self.CHUNK_SIZE:
            chunk_id = self._generate_chunk_id(
                specialty_metadata['specialty'],
                recommendation.get('number', 0)
            )
            chunks.append({
                'id': chunk_id,
                'text': rec_text,
                'metadata': metadata
            })
        else:
            # Split into overlapping chunks
            for i, chunk_text in enumerate(self._split_text(rec_text)):
                chunk_id = self._generate_chunk_id(
                    specialty_metadata['specialty'],
                    recommendation.get('number', 0),
                    chunk_index=i
                )
                chunk_metadata = {
                    **metadata,
                    'chunk_index': i,
                    'is_partial': True
                }
                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
        
        return chunks
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.CHUNK_SIZE, len(text))
            
            # Try to break at sentence boundary
            if end < len(text):
                for sep in ['. ', '.\n', '? ', '! ']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep != -1:
                        end = last_sep + len(sep) - 1
                        break
            
            chunks.append(text[start:end])
            
            # Check if we're done before setting next start
            if end >= len(text):
                break
                
            start = end - self.CHUNK_OVERLAP
            
            # Prevent infinite loop on small remaining text
            if start >= len(text) - 10:
                break
        
        return chunks
    
    def _generate_chunk_id(self, specialty: str, rec_number: int, chunk_index: int = 0) -> str:
        """Generate unique chunk ID."""
        specialty_clean = specialty.lower().replace(' ', '_').replace('-', '_')
        return f"cw_{specialty_clean}_rec{rec_number}_chunk{chunk_index}"
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks (local mode)."""
        if not self.openai_client:
            logger.warning("No OpenAI client - returning empty embeddings")
            return [[0.0] * 1536 for _ in texts]
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return [[0.0] * 1536 for _ in texts]
    
    def ingest_specialty_local(self, json_path: str) -> Dict[str, Any]:
        """Ingest a single specialty JSON file to local Chroma."""
        try:
            # Load JSON data
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            specialty = data.get('specialty', 'Unknown')
            logger.info(f"[LOCAL] Ingesting {specialty} with {len(data.get('recommendations', []))} recommendations")
            
            # Prepare specialty-level metadata
            specialty_metadata = {
                'source': 'choosing_wisely',
                'source_org': 'choosing_wisely_canada',
                'specialty': specialty,
                'organization': data.get('organization', ''),
                'last_updated': data.get('last_updated', ''),
                'has_methodology': bool(data.get('methodology')),
                'total_sources': len(data.get('all_sources', [])),
                'ingested_at': datetime.now().isoformat()
            }
            
            # Create chunks for each recommendation
            all_chunks = []
            for rec in data.get('recommendations', []):
                chunks = self.create_chunks_from_recommendation(rec, specialty_metadata)
                all_chunks.extend(chunks)
            
            logger.info(f"  Created {len(all_chunks)} chunks from {len(data.get('recommendations', []))} recommendations")
            
            # Process chunks in batches
            logger.info(f"  Processing {len(all_chunks)} chunks in batches of {self.BATCH_SIZE}")
            for i in range(0, len(all_chunks), self.BATCH_SIZE):
                batch = all_chunks[i:i + self.BATCH_SIZE]
                batch_num = i//self.BATCH_SIZE + 1
                logger.info(f"  Processing batch {batch_num} ({len(batch)} chunks)...")
                
                # Extract components
                ids = [c['id'] for c in batch]
                texts = [c['text'] for c in batch]
                metadatas = [c['metadata'] for c in batch]
                
                # Generate embeddings
                embeddings = self.generate_embeddings(texts)
                
                # Add to Chroma
                self.collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings if embeddings[0] != [0.0] * 1536 else None
                )
                
                logger.info(f"  ✓ Added batch {batch_num} ({len(batch)} chunks)")
            
            logger.info(f"✓ [LOCAL] Successfully ingested {specialty}: {len(all_chunks)} chunks")
            
            return {
                'success': True,
                'mode': 'local',
                'specialty': specialty,
                'recommendations': len(data.get('recommendations', [])),
                'chunks_created': len(all_chunks),
                'json_path': json_path
            }
            
        except Exception as e:
            logger.error(f"[LOCAL] Error ingesting {json_path}: {e}")
            return {
                'success': False,
                'mode': 'local',
                'error': str(e),
                'json_path': json_path
            }
    
    # ==================== RAILWAY INGESTION METHODS ====================
    
    async def ingest_specialty_railway(
        self,
        session: aiohttp.ClientSession,
        json_path: str
    ) -> Dict[str, Any]:
        """Ingest a single specialty JSON file to Railway."""
        try:
            # Load JSON data
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            specialty = json_data.get('specialty', 'Unknown')
            num_recommendations = len(json_data.get('recommendations', []))
            
            logger.info(f"[RAILWAY] Uploading {specialty} ({num_recommendations} recommendations)")
            
            # Prepare payload for Railway endpoint
            payload = {
                "agent_type": "dr_opa",
                "json_data": json_data,
                "collection_name": "opa_choosing_wisely_corpus",
                "source_org": "choosing_wisely"
            }
            
            # Send to Railway
            async with session.post(
                f"{self.railway_url}/admin/ingest-json",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=600)  # 10 minute timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    count = result.get("sections_ingested", 0) or result.get("documents_ingested", 0)
                    logger.info(f"  ✅ [RAILWAY] Success: {count} items ingested")
                    return {
                        "success": True,
                        "mode": "railway",
                        "specialty": specialty,
                        "recommendations": num_recommendations,
                        "items_ingested": count,
                        "json_path": json_path
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"  ❌ [RAILWAY] Failed: HTTP {response.status}")
                    return {
                        "success": False,
                        "mode": "railway",
                        "specialty": specialty,
                        "error": f"HTTP {response.status}: {error_text[:200]}",
                        "json_path": json_path
                    }
                    
        except Exception as e:
            logger.error(f"[RAILWAY] Error processing {json_path}: {e}")
            return {
                "success": False,
                "mode": "railway",
                "error": str(e),
                "json_path": json_path
            }
    
    # ==================== UNIFIED INGESTION METHODS ====================
    
    def ingest_all_local(self, json_dir: str = None) -> Dict[str, Any]:
        """Ingest all Choosing Wisely JSON files locally (synchronous)."""
        if not json_dir:
            json_dir = "."
        
        json_path = Path(json_dir)
        json_files = sorted(json_path.glob("*.json"))
        
        # Filter to only Choosing Wisely files
        cw_files = [
            f for f in json_files 
            if not any(skip in f.name.lower() for skip in [
                'section_map', 'test', 'config', 'package',
                'tsconfig', 'analysis', 'extraction'
            ])
        ]
        
        if not cw_files:
            logger.warning(f"No Choosing Wisely JSON files found in {json_dir}")
            return {"success": False, "message": "No files found"}
        
        logger.info(f"🚀 Starting Choosing Wisely ingestion (LOCAL mode)")
        logger.info(f"   Directory: {json_dir}")
        logger.info(f"   Files found: {len(cw_files)}")
        
        results = []
        total_chunks = 0
        
        for json_file in cw_files:
            result = self.ingest_specialty_local(str(json_file))
            results.append(result)
            if result['success']:
                total_chunks += result.get('chunks_created', 0)
        
        return self._generate_summary(results, cw_files, {'total_chunks': total_chunks})
    
    async def ingest_all_railway(self, json_dir: str = None) -> Dict[str, Any]:
        """Ingest all Choosing Wisely JSON files to Railway (asynchronous)."""
        if not json_dir:
            json_dir = "."
        
        json_path = Path(json_dir)
        json_files = sorted(json_path.glob("*.json"))
        
        # Filter to only Choosing Wisely files
        cw_files = [
            f for f in json_files 
            if not any(skip in f.name.lower() for skip in [
                'section_map', 'test', 'config', 'package',
                'tsconfig', 'analysis', 'extraction'
            ])
        ]
        
        if not cw_files:
            logger.warning(f"No Choosing Wisely JSON files found in {json_dir}")
            return {"success": False, "message": "No files found"}
        
        logger.info(f"🚀 Starting Choosing Wisely ingestion (RAILWAY mode)")
        logger.info(f"   Directory: {json_dir}")
        logger.info(f"   Files found: {len(cw_files)}")
        
        results = []
        total_items = 0
        
        async with aiohttp.ClientSession() as session:
            for json_file in cw_files:
                result = await self.ingest_specialty_railway(session, str(json_file))
                results.append(result)
                if result.get('success'):
                    total_items += result.get('items_ingested', 0)
                # Small delay between uploads
                await asyncio.sleep(1)
        
        return self._generate_summary(results, cw_files, {'total_items': total_items})
    
    def _generate_summary(self, results: List[Dict], cw_files: List[Path], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ingestion summary."""
        # Calculate summary
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful
        total_recommendations = sum(r.get('recommendations', 0) for r in results if r.get('success'))
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 CHOOSING WISELY INGESTION SUMMARY ({self.mode.upper()})")
        print("=" * 60)
        
        if self.mode == "local":
            print(f"Chroma path: data/dr_opa_agent/chroma")
            print(f"Collection: {self.collection_name}")
            print(f"Total chunks created: {stats.get('total_chunks', 0)}")
        else:
            print(f"Railway URL: {self.railway_url}")
            print(f"Collection: opa_choosing_wisely_corpus")
            print(f"Total items ingested: {stats.get('total_items', 0)}")
        
        print(f"Files processed: {len(cw_files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total recommendations: {total_recommendations}")
        
        if successful > 0:
            print(f"\n✅ Successfully ingested specialties:")
            for r in results:
                if r.get('success'):
                    specialty = r.get('specialty', Path(r['json_path']).stem)
                    if self.mode == "local":
                        print(f"  - {specialty}: {r.get('chunks_created', 0)} chunks")
                    else:
                        print(f"  - {specialty}: {r.get('items_ingested', 0)} items")
        
        if failed > 0:
            print("\n❌ Failed files:")
            for r in results:
                if not r.get('success'):
                    print(f"  - {Path(r['json_path']).name}: {r.get('error', 'Unknown error')}")
        
        return {
            'success': successful > 0,
            'mode': self.mode,
            'files_processed': len(cw_files),
            'successful': successful,
            'failed': failed,
            'total_recommendations': total_recommendations,
            **stats,
            'results': results
        }


def main():
    """Main entry point for Choosing Wisely ingestion."""
    from dotenv import load_dotenv
    
    parser = argparse.ArgumentParser(
        description='Ingest Choosing Wisely recommendations into Chroma (local or Railway)'
    )
    parser.add_argument(
        '--mode',
        choices=['local', 'railway'],
        default='local',
        help='Ingestion mode: local Chroma or Railway endpoint'
    )
    parser.add_argument(
        '--json-dir',
        default='.',
        help='Directory containing JSON files'
    )
    parser.add_argument(
        '--chroma-path',
        default='data/dr_opa_agent/chroma',
        help='Path to local Chroma database (local mode only)'
    )
    parser.add_argument(
        '--collection',
        default='choosing_wisely_recommendations',
        help='Chroma collection name (local mode only)'
    )
    parser.add_argument(
        '--railway-url',
        default='https://healthassistant-production-3613.up.railway.app',
        help='Railway app URL (railway mode only)'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key for embeddings (local mode only)'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Initialize ingester
    ingester = ChoosingWiselyIngester(
        mode=args.mode,
        chroma_path=args.chroma_path if args.mode == 'local' else None,
        railway_url=args.railway_url if args.mode == 'railway' else None,
        openai_api_key=args.api_key if args.mode == 'local' else None,
        collection_name=args.collection if args.mode == 'local' else None
    )
    
    # Run ingestion based on mode
    if args.mode == 'local':
        result = ingester.ingest_all_local(args.json_dir)
    else:
        # Railway mode still needs async
        result = asyncio.run(ingester.ingest_all_railway(args.json_dir))
    
    # Exit with appropriate code
    if result.get('success'):
        print(f"\n🎉 {args.mode.upper()} ingestion completed successfully!")
        return 0
    else:
        print(f"\n⚠️ {args.mode.upper()} ingestion completed with errors")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)