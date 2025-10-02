#!/usr/bin/env python3
"""
Ingest Ontario Health Quality Standards into Chroma vector database.
Supports both local Chroma and Railway deployment.

Two-level chunking strategy:
1. Document-level: Overview with all statement summaries
2. Statement-level: Complete individual statements
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
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from openai import OpenAI

# Configure logging to both console and file
log_dir = Path("logs/quality_standards")
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


class QualityStandardsIngester:
    """Unified ingester for Ontario Health Quality Standards."""
    
    # Chunking parameters
    CHUNK_SIZE = 2000  # Larger for structured content
    BATCH_SIZE = 50    # Embeddings per batch
    EMBEDDING_MODEL = "text-embedding-3-small"  # CRITICAL: Must be explicit
    EMBEDDING_DIM = 1536  # CRITICAL: Must verify
    
    def __init__(
        self,
        mode: str = "local",
        chroma_path: Optional[str] = None,
        railway_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        collection_name: str = "opa_quality_standards_corpus"
    ):
        """Initialize Quality Standards ingester.
        
        Args:
            mode: "local" for local Chroma, "railway" for Railway endpoint
            chroma_path: Path to local Chroma database (for local mode)
            railway_url: Railway app URL (for railway mode)
            openai_api_key: OpenAI API key for embeddings (local mode only)
            collection_name: Name of Chroma collection
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
            raise ValueError("OpenAI API key is required for local ingestion")
        
        # Initialize embedding function with EXPLICIT model
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_client.api_key,
            model_name=self.EMBEDDING_MODEL
        )
        logger.info(f"Using embedding model: {self.EMBEDDING_MODEL} (dim={self.EMBEDDING_DIM})")
        
        # Initialize local Chroma client
        chroma_path = chroma_path or "data/dr_opa_agent/chroma"
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info(f"Using local Chroma at {chroma_path}")
        
        # Get or create collection with EXPLICIT embedding function
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"dimension": self.EMBEDDING_DIM}
        )
        logger.info(f"Using collection: {collection_name}")
    
    def _init_railway(self, railway_url: str):
        """Initialize for Railway ingestion."""
        self.railway_url = railway_url or "https://healthassistant-production-3613.up.railway.app"
        logger.info(f"Using Railway URL: {self.railway_url}")
    
    # ==================== CHUNKING METHODS ====================
    
    def create_chunks_from_standard(
        self, 
        qs_data: Dict[str, Any], 
        json_path: str
    ) -> List[Dict[str, Any]]:
        """Create two-level chunks from a quality standard document."""
        chunks = []
        
        # Generate document ID
        doc_id = self._generate_doc_id(qs_data.get('title', 'unknown'))
        logger.debug(f"Processing: {qs_data.get('title')} -> {doc_id}")
        
        # Base metadata for all chunks
        base_metadata = {
            'source': 'ontario_health_quality_standards',
            'source_org': 'ontario_health',
            'title': qs_data.get('title', ''),
            'source_file': qs_data.get('source_file', ''),
            'json_path': str(json_path),
            'ingested_at': datetime.now().isoformat()
        }
        
        # Add year only if it exists (Chroma doesn't accept None)
        if qs_data.get('year'):
            base_metadata['year'] = qs_data['year']
        
        # Add source URL for citations - use actual PDF filename
        pdf_filename = qs_data.get('source_file', '')
        if pdf_filename:
            base_metadata['source_url'] = f"https://www.hqontario.ca/Portals/0/documents/evidence/quality-standards/{pdf_filename}"
        else:
            # Fallback if no source_file available
            base_metadata['source_url'] = "https://www.hqontario.ca/evidence-to-improve-care/quality-standards/"
        
        # ==================== 1. DOCUMENT-LEVEL CHUNK ====================
        doc_text = self._create_document_overview(qs_data)
        
        doc_chunk = {
            'id': f"qs_{doc_id}_document",
            'text': doc_text,
            'metadata': {
                **base_metadata,
                'doc_type': 'quality_standard_overview',
                'chunk_type': 'document',
                'num_statements': len(qs_data.get('statements', [])),
                'has_executive_summary': bool(qs_data.get('front_matter', {}).get('executive_summary')),
                'has_scope': bool(qs_data.get('front_matter', {}).get('scope')),
                'has_indicators': bool(qs_data.get('front_matter', {}).get('how_measured')),
                # Convert list to string for Chroma compatibility
                'statement_titles': ', '.join([s.get('title', '') for s in qs_data.get('statements', [])])
            }
        }
        chunks.append(doc_chunk)
        logger.debug(f"  Created document chunk: {len(doc_text)} chars")
        
        # ==================== 2. STATEMENT-LEVEL CHUNKS ====================
        for stmt in qs_data.get('statements', []):
            stmt_num = stmt.get('number', 0)
            stmt_text = self._create_statement_text(stmt, qs_data.get('title', ''))
            
            stmt_chunk = {
                'id': f"qs_{doc_id}_stmt{stmt_num}",
                'text': stmt_text,
                'metadata': {
                    **base_metadata,
                    'doc_type': 'quality_statement',
                    'chunk_type': 'statement',
                    'statement_number': stmt_num,
                    'statement_title': stmt.get('title', ''),
                    'has_background': bool(stmt.get('background')),
                    'has_indicators': bool(stmt.get('indicators')),
                    'has_sources': bool(stmt.get('sources')),
                    'has_patient_info': bool(stmt.get('for_patients')),
                    'has_clinician_info': bool(stmt.get('for_clinicians')),
                    'has_health_services_info': bool(stmt.get('for_health_services'))
                }
            }
            chunks.append(stmt_chunk)
            logger.debug(f"  Created statement {stmt_num} chunk: {len(stmt_text)} chars")
        
        logger.info(f"Created {len(chunks)} chunks for {qs_data.get('title')}")
        return chunks
    
    def _create_document_overview(self, qs_data: Dict[str, Any]) -> str:
        """Create document-level text with front matter and statement summaries."""
        text = f"Ontario Health Quality Standard: {qs_data.get('title', 'Unknown')}"
        
        if qs_data.get('year'):
            text += f" ({qs_data['year']})"
        
        # Add front matter sections if available
        fm = qs_data.get('front_matter', {})
        
        if fm.get('executive_summary'):
            text += f"\n\n## Executive Summary\n{fm['executive_summary']}"
        
        if fm.get('scope'):
            text += f"\n\n## Scope\n{fm['scope']}"
        
        if fm.get('why_needed'):
            text += f"\n\n## Why This Standard is Needed\n{fm['why_needed']}"
        
        if fm.get('how_measured'):
            text += f"\n\n## How Success is Measured\n{fm['how_measured']}"
        
        if fm.get('definitions'):
            text += f"\n\n## Key Definitions\n{fm['definitions']}"
        
        if fm.get('principles'):
            text += f"\n\n## Guiding Principles\n{fm['principles']}"
        
        # Add quality statements overview
        statements = qs_data.get('statements', [])
        if statements:
            text += f"\n\n## Quality Statements ({len(statements)} Total)\n"
            
            for stmt in statements:
                stmt_num = stmt.get('number', '?')
                stmt_title = stmt.get('title', 'Untitled')
                
                # Use brief_statement if available, otherwise use first part of full statement
                synopsis = stmt.get('brief_statement', '')
                if not synopsis and stmt.get('full_statement'):
                    # Take first 200 chars of full statement as synopsis
                    full = stmt['full_statement']
                    synopsis = full[:200] + "..." if len(full) > 200 else full
                
                text += f"\n**Statement {stmt_num}: {stmt_title}**\n"
                if synopsis:
                    text += f"{synopsis}\n"
        
        return text
    
    def _create_statement_text(self, stmt: Dict[str, Any], doc_title: str) -> str:
        """Create complete statement text with all sections."""
        stmt_num = stmt.get('number', '?')
        stmt_title = stmt.get('title', 'Untitled')
        
        text = f"Ontario Health Quality Standard: {doc_title}\n"
        text += f"Quality Statement {stmt_num}: {stmt_title}\n"
        text += "=" * 60 + "\n"
        
        # Full statement (main content)
        if stmt.get('full_statement'):
            text += f"\n## Statement\n{stmt['full_statement']}\n"
        elif stmt.get('brief_statement'):
            text += f"\n## Statement\n{stmt['brief_statement']}\n"
        
        # Background
        if stmt.get('background'):
            text += f"\n## Background\n{stmt['background']}\n"
        
        # For Patients
        if stmt.get('for_patients'):
            text += f"\n## For Patients\n{stmt['for_patients']}\n"
        
        # For Clinicians  
        if stmt.get('for_clinicians'):
            text += f"\n## For Clinicians\n{stmt['for_clinicians']}\n"
        
        # For Health Services
        if stmt.get('for_health_services'):
            text += f"\n## For Health Services\n{stmt['for_health_services']}\n"
        
        # Quality Indicators
        if stmt.get('indicators'):
            text += "\n## Quality Indicators\n"
            for indicator in stmt['indicators']:
                text += f"• {indicator}\n"
        
        # Sources
        if stmt.get('sources'):
            text += "\n## Sources\n"
            for source in stmt['sources']:
                text += f"• {source}\n"
        
        return text
    
    def _generate_doc_id(self, title: str) -> str:
        """Generate a clean document ID from title."""
        # Clean and normalize title
        clean_title = title.lower()
        clean_title = ''.join(c if c.isalnum() or c.isspace() else '' for c in clean_title)
        clean_title = '_'.join(clean_title.split())[:50]  # Limit length
        return clean_title
    
    # ==================== LOCAL INGESTION METHODS ====================
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with explicit model and dimension verification."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts with {self.EMBEDDING_MODEL}")
            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,  # EXPLICIT MODEL
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            
            # VERIFY DIMENSIONS
            for i, emb in enumerate(embeddings):
                if len(emb) != self.EMBEDDING_DIM:
                    raise ValueError(f"Embedding {i} has wrong dimension: {len(emb)} != {self.EMBEDDING_DIM}")
            
            logger.debug(f"Successfully generated {len(embeddings)} embeddings (dim={self.EMBEDDING_DIM})")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def ingest_standard_local(self, json_path: str) -> Dict[str, Any]:
        """Ingest a single quality standard JSON file to local Chroma."""
        try:
            # Load JSON data
            with open(json_path, 'r', encoding='utf-8') as f:
                qs_data = json.load(f)
            
            title = qs_data.get('title', 'Unknown')
            num_statements = len(qs_data.get('statements', []))
            logger.info(f"[LOCAL] Ingesting {title} with {num_statements} statements")
            
            # Create chunks
            chunks = self.create_chunks_from_standard(qs_data, json_path)
            logger.info(f"  Created {len(chunks)} chunks (1 doc + {len(chunks)-1} statements)")
            
            # Process chunks in batches
            total_added = 0
            for i in range(0, len(chunks), self.BATCH_SIZE):
                batch = chunks[i:i + self.BATCH_SIZE]
                batch_num = i // self.BATCH_SIZE + 1
                logger.info(f"  Processing batch {batch_num} ({len(batch)} chunks)...")
                
                # Extract components
                ids = [c['id'] for c in batch]
                texts = [c['text'] for c in batch]
                metadatas = [c['metadata'] for c in batch]
                
                # Generate embeddings with verification
                embeddings = self.generate_embeddings(texts)
                
                # Add to Chroma
                self.collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
                
                total_added += len(batch)
                logger.info(f"  ✓ Added batch {batch_num} ({len(batch)} chunks)")
            
            logger.info(f"✓ [LOCAL] Successfully ingested {title}: {total_added} chunks")
            
            return {
                'success': True,
                'mode': 'local',
                'title': title,
                'statements': num_statements,
                'chunks_created': len(chunks),
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
    
    async def ingest_standard_railway(
        self,
        session: aiohttp.ClientSession,
        json_path: str
    ) -> Dict[str, Any]:
        """Ingest a single quality standard JSON file to Railway."""
        try:
            # Load JSON data
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            title = json_data.get('title', 'Unknown')
            num_statements = len(json_data.get('statements', []))
            
            logger.info(f"[RAILWAY] Uploading {title} ({num_statements} statements)")
            
            # Prepare payload for Railway endpoint
            payload = {
                "agent_type": "dr_opa",
                "json_data": json_data,
                "collection_name": "opa_quality_standards_corpus",
                "source_org": "ontario_health",
                "embedding_model": self.EMBEDDING_MODEL,  # Explicit model
                "embedding_dim": self.EMBEDDING_DIM  # Explicit dimension
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
                        "title": title,
                        "statements": num_statements,
                        "items_ingested": count,
                        "json_path": json_path
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"  ❌ [RAILWAY] Failed: HTTP {response.status}")
                    return {
                        "success": False,
                        "mode": "railway",
                        "title": title,
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
        """Ingest all Quality Standards JSON files locally (synchronous)."""
        if not json_dir:
            json_dir = "data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304"
        
        json_path = Path(json_dir)
        json_files = sorted(json_path.glob("*.json"))
        
        # Filter to only quality standards files
        qs_files = [
            f for f in json_files 
            if not any(skip in f.name.lower() for skip in [
                'extraction_', 'front_matter', '_error', 'analysis', 'test'
            ])
        ]
        
        if not qs_files:
            logger.warning(f"No Quality Standards JSON files found in {json_dir}")
            return {"success": False, "message": "No files found"}
        
        logger.info(f"🚀 Starting Quality Standards ingestion (LOCAL mode)")
        logger.info(f"   Directory: {json_dir}")
        logger.info(f"   Files found: {len(qs_files)}")
        
        results = []
        total_chunks = 0
        
        for json_file in qs_files:
            result = self.ingest_standard_local(str(json_file))
            results.append(result)
            if result['success']:
                total_chunks += result.get('chunks_created', 0)
        
        return self._generate_summary(results, qs_files, {'total_chunks': total_chunks})
    
    async def ingest_all_railway(self, json_dir: str = None) -> Dict[str, Any]:
        """Ingest all Quality Standards JSON files to Railway (asynchronous)."""
        if not json_dir:
            json_dir = "data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304"
        
        json_path = Path(json_dir)
        json_files = sorted(json_path.glob("*.json"))
        
        # Filter to only quality standards files
        qs_files = [
            f for f in json_files 
            if not any(skip in f.name.lower() for skip in [
                'extraction_', 'front_matter', '_error', 'analysis', 'test'
            ])
        ]
        
        if not qs_files:
            logger.warning(f"No Quality Standards JSON files found in {json_dir}")
            return {"success": False, "message": "No files found"}
        
        logger.info(f"🚀 Starting Quality Standards ingestion (RAILWAY mode)")
        logger.info(f"   Directory: {json_dir}")
        logger.info(f"   Files found: {len(qs_files)}")
        
        results = []
        total_items = 0
        
        async with aiohttp.ClientSession() as session:
            for json_file in qs_files:
                result = await self.ingest_standard_railway(session, str(json_file))
                results.append(result)
                if result.get('success'):
                    total_items += result.get('items_ingested', 0)
                # Small delay between uploads
                await asyncio.sleep(1)
        
        return self._generate_summary(results, qs_files, {'total_items': total_items})
    
    def _generate_summary(self, results: List[Dict], qs_files: List[Path], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ingestion summary."""
        # Calculate summary
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful
        total_statements = sum(r.get('statements', 0) for r in results if r.get('success'))
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 QUALITY STANDARDS INGESTION SUMMARY ({self.mode.upper()})")
        print("=" * 60)
        
        if self.mode == "local":
            print(f"Chroma path: data/dr_opa_agent/chroma")
            print(f"Collection: {self.collection_name}")
            print(f"Embedding model: {self.EMBEDDING_MODEL}")
            print(f"Embedding dimension: {self.EMBEDDING_DIM}")
            print(f"Total chunks created: {stats.get('total_chunks', 0)}")
        else:
            print(f"Railway URL: {self.railway_url}")
            print(f"Collection: opa_quality_standards_corpus")
            print(f"Total items ingested: {stats.get('total_items', 0)}")
        
        print(f"Files processed: {len(qs_files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total quality statements: {total_statements}")
        
        if successful > 0:
            print(f"\n✅ Successfully ingested standards:")
            for r in results:
                if r.get('success'):
                    title = r.get('title', Path(r['json_path']).stem)
                    if self.mode == "local":
                        print(f"  - {title}: {r.get('chunks_created', 0)} chunks")
                    else:
                        print(f"  - {title}: {r.get('items_ingested', 0)} items")
        
        if failed > 0:
            print("\n❌ Failed files:")
            for r in results:
                if not r.get('success'):
                    print(f"  - {Path(r['json_path']).name}: {r.get('error', 'Unknown error')}")
        
        return {
            'success': successful > 0,
            'mode': self.mode,
            'files_processed': len(qs_files),
            'successful': successful,
            'failed': failed,
            'total_statements': total_statements,
            **stats,
            'results': results
        }


def main():
    """Main entry point for Quality Standards ingestion."""
    from dotenv import load_dotenv
    
    parser = argparse.ArgumentParser(
        description='Ingest Ontario Health Quality Standards into Chroma (local or Railway)'
    )
    parser.add_argument(
        '--mode',
        choices=['local', 'railway'],
        default='local',
        help='Ingestion mode: local Chroma or Railway endpoint'
    )
    parser.add_argument(
        '--json-dir',
        default='data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304',
        help='Directory containing Quality Standards JSON files'
    )
    parser.add_argument(
        '--chroma-path',
        default='data/dr_opa_agent/chroma',
        help='Path to local Chroma database (local mode only)'
    )
    parser.add_argument(
        '--collection',
        default='opa_quality_standards_corpus',
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
    ingester = QualityStandardsIngester(
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
        # Railway mode needs async
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