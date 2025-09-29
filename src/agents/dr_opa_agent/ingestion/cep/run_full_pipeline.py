#!/usr/bin/env python3
"""Run full CEP ingestion pipeline - crawl, extract, and ingest all tools."""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.dr_opa_agent.ingestion.cep import (
    CEPCrawler,
    CEPExtractor,
    CEPIngester
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_full_pipeline():
    """Run complete CEP ingestion pipeline."""
    
    print("\n" + "="*70)
    print("CEP CLINICAL TOOLS - FULL INGESTION PIPELINE")
    print("="*70 + "\n")
    
    pipeline_start = datetime.now()
    
    # Phase 1: Crawl all tools
    print("PHASE 1: CRAWLING ALL TOOLS")
    print("-" * 50)
    
    crawler = CEPCrawler()
    await crawler.crawl_all(max_concurrent=3, resume=True)
    
    # Phase 2: Extract all tools
    print("\nPHASE 2: EXTRACTING STRUCTURED DATA")
    print("-" * 50)
    
    extractor = CEPExtractor()
    raw_dir = Path("data/dr_opa_agent/raw/cep")
    processed_dir = Path("data/dr_opa_agent/processed/cep")
    
    extracted_count = 0
    failed_extractions = []
    
    for html_file in raw_dir.glob("*.html"):
        if '_meta' in str(html_file):
            continue
        
        tool_slug = html_file.stem
        extracted_file = processed_dir / f"{tool_slug}_extracted.json"
        
        # Skip if already extracted
        if extracted_file.exists():
            logger.info(f"✓ Already extracted: {tool_slug}")
            extracted_count += 1
            continue
        
        try:
            # Load metadata
            meta_file = raw_dir / f"{tool_slug}_meta.json"
            if not meta_file.exists():
                logger.warning(f"⚠ No metadata for {tool_slug}, skipping")
                continue
            
            with open(meta_file) as f:
                tool_info = json.load(f)
            
            # Extract
            with open(html_file, 'r', encoding='utf-8') as f:
                html = f.read()
            
            document = extractor.extract_from_html(html, tool_info['url'], tool_info)
            extractor.save_extracted_data(document)
            
            extracted_count += 1
            logger.info(f"✓ Extracted: {tool_slug}")
            
        except Exception as e:
            logger.error(f"✗ Failed to extract {tool_slug}: {e}")
            failed_extractions.append({'tool': tool_slug, 'error': str(e)})
    
    print(f"\nExtraction complete: {extracted_count} tools extracted")
    if failed_extractions:
        print(f"Failed extractions: {len(failed_extractions)}")
        for failure in failed_extractions:
            print(f"  - {failure['tool']}: {failure['error'][:100]}")
    
    # Phase 3: Ingest all tools
    print("\nPHASE 3: INGESTING INTO DATABASE")
    print("-" * 50)
    
    # Load environment for OpenAI key
    from dotenv import load_dotenv
    env_path = Path('/Users/liammckendry/health_assistant_dr_off_worktree/.env')
    if env_path.exists():
        load_dotenv(env_path)
        print("✓ Loaded environment variables")
    
    ingester = CEPIngester()
    
    ingested_count = 0
    failed_ingestions = []
    total_chunks = 0
    
    # Find all extracted files
    extracted_files = list(processed_dir.glob("*_extracted.json"))
    
    print(f"Found {len(extracted_files)} extracted tools to ingest")
    
    for extracted_file in extracted_files:
        tool_slug = extracted_file.stem.replace('_extracted', '')
        
        try:
            stats = ingester.ingest_tool(tool_slug)
            ingested_count += 1
            total_chunks += stats['chunks_stored']
            logger.info(f"✓ Ingested {tool_slug}: {stats['chunks_stored']} chunks")
            
        except Exception as e:
            logger.error(f"✗ Failed to ingest {tool_slug}: {e}")
            failed_ingestions.append({'tool': tool_slug, 'error': str(e)})
    
    # Phase 4: Generate summary
    print("\nPHASE 4: GENERATING SUMMARY")
    print("-" * 50)
    
    pipeline_end = datetime.now()
    duration = (pipeline_end - pipeline_start).total_seconds()
    
    # Check database stats
    import sqlite3
    db_path = "data/processed/dr_opa/opa.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM opa_documents WHERE source_org='cep'")
    doc_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM opa_sections WHERE document_id IN (SELECT document_id FROM opa_documents WHERE source_org='cep')")
    section_count = cursor.fetchone()[0]
    
    conn.close()
    
    summary = {
        'pipeline_started': pipeline_start.isoformat(),
        'pipeline_completed': pipeline_end.isoformat(),
        'duration_seconds': duration,
        'tools_crawled': len(list(raw_dir.glob("*.html"))),
        'tools_extracted': extracted_count,
        'tools_ingested': ingested_count,
        'total_chunks': total_chunks,
        'documents_in_db': doc_count,
        'sections_in_db': section_count,
        'failed_extractions': failed_extractions,
        'failed_ingestions': failed_ingestions
    }
    
    # Save summary
    summary_file = processed_dir / "full_pipeline_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("PIPELINE COMPLETE!")
    print("="*70)
    print(f"\nDuration: {duration:.1f} seconds")
    print(f"Tools crawled: {summary['tools_crawled']}")
    print(f"Tools extracted: {summary['tools_extracted']}")
    print(f"Tools ingested: {summary['tools_ingested']}")
    print(f"Total chunks stored: {summary['total_chunks']}")
    print(f"Documents in database: {summary['documents_in_db']}")
    print(f"Sections in database: {summary['sections_in_db']}")
    
    if failed_extractions or failed_ingestions:
        print(f"\n⚠ Issues encountered:")
        print(f"  Failed extractions: {len(failed_extractions)}")
        print(f"  Failed ingestions: {len(failed_ingestions)}")
    
    print(f"\nFull summary saved to: {summary_file}")
    
    return summary


if __name__ == "__main__":
    summary = asyncio.run(run_full_pipeline())
    
    # Return exit code based on success
    if summary['tools_ingested'] == 0:
        sys.exit(1)
    elif summary.get('failed_ingestions'):
        sys.exit(2)  # Partial success
    else:
        sys.exit(0)  # Full success