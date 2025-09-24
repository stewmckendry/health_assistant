#!/usr/bin/env python3
"""Test CEP ingestion pipeline with single tool."""

import sys
import asyncio
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
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


async def test_single_tool():
    """Test pipeline with dementia diagnosis tool."""
    
    print("\n" + "="*60)
    print("CEP INGESTION PIPELINE TEST")
    print("Testing with: Dementia Diagnosis Tool")
    print("="*60 + "\n")
    
    tool_slug = 'dementia-diagnosis'
    
    # Step 1: Crawl
    print("Step 1: CRAWLING")
    print("-" * 40)
    
    crawler = CEPCrawler()
    html_file = Path(f"data/dr_opa_agent/raw/cep/{tool_slug}.html")
    
    if html_file.exists():
        print(f"✓ Tool already crawled: {html_file}")
    else:
        print(f"Crawling {tool_slug}...")
        result = await crawler.crawl_single(tool_slug)
        print(f"✓ Crawled: {result['name']}")
        print(f"  URL: {result['url']}")
        print(f"  Category: {result['category']}")
    
    # Step 2: Extract
    print("\nStep 2: EXTRACTION")
    print("-" * 40)
    
    extractor = CEPExtractor()
    extracted_file = Path(f"data/dr_opa_agent/processed/cep/{tool_slug}_extracted.json")
    
    if extracted_file.exists():
        print(f"✓ Extraction exists: {extracted_file}")
        with open(extracted_file) as f:
            document = json.load(f)
    else:
        # Load HTML and metadata
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        meta_file = Path(f"data/dr_opa_agent/raw/cep/{tool_slug}_meta.json")
        with open(meta_file) as f:
            tool_info = json.load(f)
        
        # Extract
        print(f"Extracting structured data...")
        document = extractor.extract_from_html(
            html, 
            tool_info['url'],
            tool_info
        )
        
        # Save
        extractor.save_extracted_data(document)
        print(f"✓ Extracted and saved to: {extracted_file}")
    
    # Print extraction summary
    print("\nExtraction Summary:")
    print(f"  Title: {document['title']}")
    print(f"  Category: {document['tool_category']}")
    print(f"  Sections: {len(document.get('sections', []))}")
    print(f"  Navigation items: {len(document.get('navigation', []))}")
    
    features = document.get('features', {})
    active_features = [k.replace('has_', '') for k, v in features.items() if v]
    if active_features:
        print(f"  Features: {', '.join(active_features)}")
    
    key_content = document.get('key_content', {})
    if key_content.get('assessment_tools'):
        print(f"  Assessment tools: {', '.join(key_content['assessment_tools'])}")
    
    # Step 3: Ingest
    print("\nStep 3: INGESTION")
    print("-" * 40)
    
    # Load environment variables for OpenAI API key
    from dotenv import load_dotenv
    env_path = Path('/Users/liammckendry/health_assistant_dr_off_worktree/.env')
    if env_path.exists():
        load_dotenv(env_path)
        print("✓ Loaded environment variables")
    
    ingester = CEPIngester()
    
    print(f"Ingesting into database and vector store...")
    stats = ingester.ingest_tool(tool_slug)
    
    print("\n✓ Ingestion Complete!")
    print("\nIngestion Statistics:")
    print(f"  Document ID: {stats['document_id']}")
    print(f"  Chunks created: {stats['chunks_created']}")
    print(f"  Chunks stored: {stats['chunks_stored']}")
    print(f"  Sections: {stats['sections']}")
    print(f"  Navigation items: {stats['navigation_items']}")
    
    if stats.get('features'):
        active = [k.replace('has_', '') for k, v in stats['features'].items() if v]
        if active:
            print(f"  Active features: {', '.join(active)}")
    
    # Step 4: Verify in database
    print("\nStep 4: VERIFICATION")
    print("-" * 40)
    
    import sqlite3
    db_path = "data/processed/dr_opa/opa.db"
    
    if Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check document
        cursor.execute(
            "SELECT COUNT(*) FROM opa_documents WHERE document_id = ?",
            (stats['document_id'],)
        )
        doc_count = cursor.fetchone()[0]
        print(f"✓ Document in database: {doc_count > 0}")
        
        # Check sections
        cursor.execute(
            "SELECT COUNT(*) FROM opa_sections WHERE document_id = ?",
            (stats['document_id'],)
        )
        section_count = cursor.fetchone()[0]
        print(f"✓ Sections in database: {section_count}")
        
        # Sample section
        cursor.execute(
            "SELECT section_heading, chunk_type FROM opa_sections WHERE document_id = ? LIMIT 3",
            (stats['document_id'],)
        )
        samples = cursor.fetchall()
        if samples:
            print("\nSample sections:")
            for heading, chunk_type in samples:
                print(f"  - [{chunk_type}] {heading}")
        
        conn.close()
    
    print("\n" + "="*60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")
    
    return stats


async def test_all_tools():
    """Test crawling and processing all CEP tools."""
    
    print("\n" + "="*60)
    print("CEP FULL CRAWL TEST")
    print("="*60 + "\n")
    
    # Crawl all
    crawler = CEPCrawler()
    await crawler.crawl_all(max_concurrent=2, resume=True)
    
    # Extract all
    extractor = CEPExtractor()
    raw_dir = Path("data/dr_opa_agent/raw/cep")
    processed_count = 0
    
    for html_file in raw_dir.glob("*.html"):
        if '_meta' in str(html_file):
            continue
            
        tool_slug = html_file.stem
        meta_file = raw_dir / f"{tool_slug}_meta.json"
        
        if meta_file.exists():
            with open(meta_file) as f:
                tool_info = json.load(f)
            
            with open(html_file, 'r', encoding='utf-8') as f:
                html = f.read()
            
            document = extractor.extract_from_html(html, tool_info['url'], tool_info)
            extractor.save_extracted_data(document)
            processed_count += 1
            print(f"✓ Extracted {tool_slug}")
    
    print(f"\nExtracted {processed_count} tools")
    
    # Ingest all
    ingester = CEPIngester()
    summary = ingester.ingest_all_tools()
    
    print("\nFinal Summary:")
    print(json.dumps(summary, indent=2))
    
    return summary


if __name__ == "__main__":
    # Test single tool first
    stats = asyncio.run(test_single_tool())
    
    # Uncomment to test all tools
    # summary = asyncio.run(test_all_tools())