#!/usr/bin/env python3
"""
Ingest Choosing Wisely recommendations using Railway's pre-chunked endpoint.
Converts our processed JSON files into pre-chunked format for Railway ingestion.
"""

import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import logging
import argparse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChoosingWiselyPrechunkedIngester:
    """Convert and ingest Choosing Wisely data to Railway's pre-chunked endpoint."""
    
    # Chunking parameters (same as original)
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    def __init__(self, railway_url: str = None):
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
        load_dotenv()
    
    def create_chunks_from_file(self, json_path: str) -> List[Dict[str, Any]]:
        """Convert a Choosing Wisely JSON file into pre-chunked format."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        specialty = data.get('specialty', 'Unknown')
        organization = data.get('organization', '')
        
        # Base metadata for all chunks from this file
        base_metadata = {
            'source': 'choosing_wisely',
            'source_org': 'choosing_wisely_canada',
            'specialty': specialty,
            'organization': organization,
            'doc_type': 'choosing_wisely_recommendation',
            'ingested_at': datetime.now().isoformat()
        }
        
        chunks = []
        
        # Create specialty overview chunk first
        overview_chunk = self._create_specialty_overview_chunk(data, base_metadata)
        chunks.append(overview_chunk)
        
        # Process each recommendation
        for rec in data.get('recommendations', []):
            rec_number = rec.get('number', 'N/A')
            rec_title = rec.get('title', '')
            rec_desc = rec.get('description', '')
            references = rec.get('references', [])
            
            # Create recommendation text
            rec_text = f"Recommendation #{rec_number}: {rec_title}\n\n{rec_desc}"
            
            # Add references if present
            if references:
                rec_text += "\n\nReferences:\n"
                for ref in references:
                    rec_text += f"- {ref}\n"
            
            # Create chunk metadata
            chunk_metadata = {
                **base_metadata,
                'recommendation_number': rec_number,
                'recommendation_title': rec_title[:200] if rec_title else '',  # Truncate long titles
                'has_references': len(references) > 0,
                'reference_count': len(references),
                'chunk_type': 'recommendation',
                'text_length': len(rec_text),
                # Add source URL - construct from specialty and number
                'source_url': f"https://choosingwiselycanada.org/recommendation/{specialty.lower().replace(' ', '-')}/#{rec_number}"
            }
            
            # Clean metadata (remove None values, convert lists to strings)
            chunk_metadata = self._clean_metadata(chunk_metadata)
            
            # If text is short enough, create single chunk
            if len(rec_text) <= self.CHUNK_SIZE:
                chunk_id = f"cw_{self._clean_specialty(specialty)}_rec{rec_number}"
                chunks.append({
                    'id': chunk_id,
                    'text': rec_text,
                    'metadata': chunk_metadata
                })
            else:
                # Split into multiple chunks with overlap
                text_chunks = self._split_text(rec_text)
                for i, chunk_text in enumerate(text_chunks):
                    chunk_id = f"cw_{self._clean_specialty(specialty)}_rec{rec_number}_chunk{i}"
                    chunk_meta = {
                        **chunk_metadata,
                        'chunk_index': i,
                        'total_chunks': len(text_chunks),
                        'is_partial': True
                    }
                    chunks.append({
                        'id': chunk_id,
                        'text': chunk_text,
                        'metadata': chunk_meta
                    })
        
        return chunks
    
    def _create_specialty_overview_chunk(self, data: Dict[str, Any], base_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create an overview chunk for the specialty with all recommendations listed."""
        specialty = data.get('specialty', 'Unknown')
        organization = data.get('organization', '')
        last_updated = data.get('last_updated', '')
        recommendations = data.get('recommendations', [])
        
        # Create overview text
        overview_text = f"Choosing Wisely Canada - {specialty}\n"
        if organization:
            overview_text += f"Organization: {organization}\n"
        if last_updated:
            overview_text += f"Last Updated: {last_updated}\n"
        
        overview_text += f"\nThis specialty has {len(recommendations)} recommendations:\n\n"
        
        # List all recommendations with brief descriptions
        for rec in recommendations:
            rec_num = rec.get('number', 'N/A')
            rec_title = rec.get('title', '')
            rec_desc = rec.get('description', '')
            
            overview_text += f"{rec_num}. {rec_title}\n"
            # Add first 150 chars of description for context
            if rec_desc:
                brief_desc = rec_desc[:150] + "..." if len(rec_desc) > 150 else rec_desc
                overview_text += f"   {brief_desc}\n"
            overview_text += "\n"
        
        # Add methodology if available
        if data.get('methodology'):
            overview_text += f"\nMethodology:\n{data['methodology']}\n"
        
        # Create chunk metadata
        chunk_metadata = {
            **base_metadata,
            'chunk_type': 'specialty_overview',
            'doc_type': 'choosing_wisely_overview',
            'recommendation_count': len(recommendations),
            'has_methodology': bool(data.get('methodology')),
            'text_length': len(overview_text),
            'source_url': f"https://choosingwiselycanada.org/{specialty.lower().replace(' ', '-')}"
        }
        
        # Clean metadata
        chunk_metadata = self._clean_metadata(chunk_metadata)
        
        return {
            'id': f"cw_{self._clean_specialty(specialty)}_overview",
            'text': overview_text,
            'metadata': chunk_metadata
        }
    
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
    
    def _clean_specialty(self, specialty: str) -> str:
        """Clean specialty name for use in IDs."""
        return specialty.lower().replace(' ', '_').replace('&', 'and').replace(':', '').replace('-', '_')
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean metadata to ensure Chroma compatibility."""
        cleaned = {}
        for key, value in metadata.items():
            if value is None:
                cleaned[key] = ''
            elif isinstance(value, list):
                cleaned[key] = ', '.join(str(v) for v in value)
            elif isinstance(value, (dict, tuple)):
                cleaned[key] = str(value)
            else:
                cleaned[key] = value
        return cleaned
    
    async def delete_railway_collection(self, collection_name: str = "opa_choosing_wisely_corpus") -> bool:
        """Delete existing collection on Railway to fix embedding function mismatch."""
        try:
            logger.info(f"Attempting to delete Railway collection: {collection_name}")
            
            # Try to delete the collection
            async with aiohttp.ClientSession() as session:
                delete_url = f"{self.railway_url}/admin/collections/{collection_name}"
                async with session.delete(delete_url) as response:
                    if response.status == 200:
                        logger.info(f"✅ Successfully deleted Railway collection: {collection_name}")
                        return True
                    elif response.status == 404:
                        logger.info(f"Collection {collection_name} does not exist on Railway (404)")
                        return True
                    else:
                        text = await response.text()
                        logger.warning(f"Failed to delete collection {collection_name}: {response.status} - {text}")
                        return False
        except Exception as e:
            logger.warning(f"Error deleting Railway collection {collection_name}: {e}")
            return False

    async def ingest_to_railway(self, json_dir: str = None) -> Dict[str, Any]:
        """Ingest all Choosing Wisely files to Railway using pre-chunked endpoint."""
        if not json_dir:
            json_dir = "data/dr_opa_agent/processed/choosing_wisely"
        
        # First, delete existing collection to fix embedding function mismatch
        logger.info("🗑️ Deleting existing Railway collection to fix embedding function...")
        await self.delete_railway_collection()
        
        json_path = Path(json_dir)
        json_files = sorted(json_path.glob("*.json"))
        
        # Filter out problematic files
        skip_files = ['all_sections_combined.json']
        json_files = [f for f in json_files if f.name not in skip_files]
        
        if not json_files:
            logger.warning(f"No Choosing Wisely JSON files found in {json_dir}")
            return {"success": False, "message": "No files found"}
        
        logger.info(f"🚀 Starting Choosing Wisely ingestion to Railway")
        logger.info(f"   Directory: {json_dir}")
        logger.info(f"   Files found: {len(json_files)}")
        
        # Process all files and collect chunks
        all_chunks = []
        for json_file in json_files:
            logger.info(f"Processing {json_file.name}...")
            try:
                chunks = self.create_chunks_from_file(str(json_file))
                all_chunks.extend(chunks)
                logger.info(f"  ✓ Created {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"  ✗ Error processing {json_file.name}: {e}")
        
        logger.info(f"\nTotal chunks to ingest: {len(all_chunks)}")
        
        # Prepare payload for Railway
        payload = {
            "collection_name": "opa_choosing_wisely_corpus",
            "source_org": "choosing_wisely_canada",
            "embedding_model": "text-embedding-3-small",
            "chunks": all_chunks
        }
        
        # Send to Railway
        logger.info(f"\n📤 Sending {len(all_chunks)} chunks to Railway...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.railway_url}/admin/ingest-prechunked",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=600)  # 10 minute timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Successfully ingested to Railway!")
                        logger.info(f"   Response: {json.dumps(result, indent=2)}")
                        return {
                            "success": True,
                            "chunks_sent": len(all_chunks),
                            "response": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed: HTTP {response.status}")
                        logger.error(f"   Error: {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}"
                        }
            except Exception as e:
                logger.error(f"❌ Error sending to Railway: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest Choosing Wisely recommendations to Railway using pre-chunked endpoint'
    )
    parser.add_argument(
        '--json-dir',
        default='data/dr_opa_agent/processed/choosing_wisely',
        help='Directory containing JSON files'
    )
    parser.add_argument(
        '--railway-url',
        default='https://healthassistant-production-3613.up.railway.app',
        help='Railway app URL'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode - only process first file'
    )
    
    args = parser.parse_args()
    
    if args.test:
        # Test mode - process only one file
        logger.info("🧪 TEST MODE - Processing only cardiology.json")
        ingester = ChoosingWiselyPrechunkedIngester(railway_url=args.railway_url)
        
        test_file = Path(args.json_dir) / "cardiology.json"
        if not test_file.exists():
            logger.error(f"Test file not found: {test_file}")
            return 1
        
        chunks = ingester.create_chunks_from_file(str(test_file))
        logger.info(f"Created {len(chunks)} chunks")
        
        # Show sample chunk
        if chunks:
            logger.info("\nSample chunk:")
            logger.info(json.dumps(chunks[0], indent=2))
        
        # Send just this file's chunks
        payload = {
            "collection_name": "opa_choosing_wisely_corpus",
            "source_org": "choosing_wisely_canada",
            "embedding_model": "text-embedding-3-small",
            "chunks": chunks
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{args.railway_url}/admin/ingest-prechunked",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Test successful!")
                    logger.info(f"   Response: {json.dumps(result, indent=2)}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Test failed: HTTP {response.status}")
                    logger.error(f"   Error: {error_text}")
    else:
        # Full ingestion
        ingester = ChoosingWiselyPrechunkedIngester(railway_url=args.railway_url)
        result = await ingester.ingest_to_railway(args.json_dir)
        
        if result.get('success'):
            logger.info("\n🎉 Ingestion completed successfully!")
            return 0
        else:
            logger.error("\n⚠️ Ingestion failed")
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)