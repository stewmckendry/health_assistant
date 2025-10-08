#!/usr/bin/env python3
"""
Send pre-chunked quality standards data to Railway using the new endpoint.
This script prepares chunks locally and sends them to Railway for ingestion.
"""

import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import argparse


def create_chunks_from_quality_standard(qs_data: Dict[str, Any], json_path: str) -> List[Dict[str, Any]]:
    """Create chunks from a quality standard document."""
    chunks = []
    
    # Generate document ID
    title = qs_data.get('title', 'unknown')
    doc_id = ''.join(c if c.isalnum() or c.isspace() else '' for c in title.lower())
    doc_id = '_'.join(doc_id.split())[:50]
    
    # Base metadata
    base_metadata = {
        'source': 'ontario_health_quality_standards',
        'source_org': 'ontario_health',
        'title': qs_data.get('title', ''),
        'source_file': qs_data.get('source_file', ''),
        'json_path': str(json_path),
        'ingested_at': datetime.now().isoformat()
    }
    
    # Add year only if it exists (no None values)
    if qs_data.get('year'):
        base_metadata['year'] = qs_data['year']
    
    # Add source URL for citations - use actual PDF filename
    pdf_filename = qs_data.get('source_file', '')
    if pdf_filename:
        base_metadata['source_url'] = f"https://www.hqontario.ca/Portals/0/documents/evidence/quality-standards/{pdf_filename}"
    else:
        # Fallback if no source_file available
        base_metadata['source_url'] = "https://www.hqontario.ca/evidence-to-improve-care/quality-standards/"
    
    # 1. Document-level chunk
    doc_text = create_document_overview(qs_data)
    doc_chunk = {
        'id': f"qs_{doc_id}_document",
        'text': doc_text,
        'metadata': {
            **base_metadata,
            'doc_type': 'quality_standard_overview',
            'chunk_type': 'document',
            'num_statements': len(qs_data.get('statements', [])),
            'statement_titles': ', '.join([s.get('title', '') for s in qs_data.get('statements', [])])
        }
    }
    chunks.append(doc_chunk)
    
    # 2. Statement-level chunks
    for stmt in qs_data.get('statements', []):
        stmt_num = stmt.get('number', 0)
        stmt_text = create_statement_text(stmt, qs_data.get('title', ''))
        
        stmt_chunk = {
            'id': f"qs_{doc_id}_stmt{stmt_num}",
            'text': stmt_text,
            'metadata': {
                **base_metadata,
                'doc_type': 'quality_statement',
                'chunk_type': 'statement',
                'statement_number': stmt_num,
                'statement_title': stmt.get('title', ''),
                'has_background': str(bool(stmt.get('background'))),
                'has_indicators': str(bool(stmt.get('indicators'))),
                'has_patient_info': str(bool(stmt.get('for_patients'))),
                'has_clinician_info': str(bool(stmt.get('for_clinicians')))
            }
        }
        chunks.append(stmt_chunk)
    
    return chunks


def create_document_overview(qs_data: Dict[str, Any]) -> str:
    """Create document-level overview text."""
    text = f"Ontario Health Quality Standard: {qs_data.get('title', 'Unknown')}"
    
    if qs_data.get('year'):
        text += f" ({qs_data['year']})"
    
    # Add front matter sections
    fm = qs_data.get('front_matter', {})
    
    if fm.get('executive_summary'):
        text += f"\n\n## Executive Summary\n{fm['executive_summary']}"
    
    if fm.get('scope'):
        text += f"\n\n## Scope\n{fm['scope']}"
    
    if fm.get('why_needed'):
        text += f"\n\n## Why This Standard is Needed\n{fm['why_needed']}"
    
    if fm.get('how_measured'):
        text += f"\n\n## How Success is Measured\n{fm['how_measured']}"
    
    # Add statement list
    statements = qs_data.get('statements', [])
    if statements:
        text += f"\n\n## Quality Statements ({len(statements)} Total)\n"
        for stmt in statements:
            text += f"\nStatement {stmt.get('number', '?')}: {stmt.get('title', 'Untitled')}"
            if stmt.get('brief_statement'):
                text += f"\n{stmt['brief_statement']}"
    
    return text


def create_statement_text(stmt: Dict[str, Any], doc_title: str) -> str:
    """Create complete statement text."""
    text = f"Ontario Health Quality Standard: {doc_title}\n"
    text += f"Quality Statement {stmt.get('number', '?')}: {stmt.get('title', 'Untitled')}\n"
    text += "=" * 60 + "\n"
    
    if stmt.get('full_statement'):
        text += f"\n## Statement\n{stmt['full_statement']}\n"
    elif stmt.get('brief_statement'):
        text += f"\n## Statement\n{stmt['brief_statement']}\n"
    
    if stmt.get('background'):
        text += f"\n## Background\n{stmt['background']}\n"
    
    if stmt.get('for_patients'):
        text += f"\n## For Patients\n{stmt['for_patients']}\n"
    
    if stmt.get('for_clinicians'):
        text += f"\n## For Clinicians\n{stmt['for_clinicians']}\n"
    
    if stmt.get('for_health_services'):
        text += f"\n## For Health Services\n{stmt['for_health_services']}\n"
    
    if stmt.get('indicators'):
        text += "\n## Quality Indicators\n"
        for indicator in stmt['indicators']:
            text += f"• {indicator}\n"
    
    if stmt.get('sources'):
        text += "\n## Sources\n"
        for source in stmt['sources']:
            text += f"• {source}\n"
    
    return text


async def send_chunks_to_railway(
    chunks: List[Dict[str, Any]], 
    railway_url: str,
    collection_name: str
) -> Dict[str, Any]:
    """Send pre-chunked data to Railway endpoint."""
    
    # Check if using new endpoint
    endpoint = f"{railway_url}/admin/ingest-prechunked"
    
    payload = {
        "collection_name": collection_name,
        "source_org": "ontario_health",
        "embedding_model": "text-embedding-3-small",
        "chunks": chunks
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            endpoint,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=600)
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                return {"error": f"HTTP {response.status}: {error_text[:500]}"}


async def main():
    parser = argparse.ArgumentParser(description='Send quality standards to Railway')
    parser.add_argument(
        '--railway-url',
        default='https://healthassistant-production-3613.up.railway.app',
        help='Railway app URL'
    )
    parser.add_argument(
        '--collection',
        default='opa_quality_standards_corpus',
        help='Collection name'
    )
    parser.add_argument(
        '--json-dir',
        default='data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304',
        help='Directory containing quality standards JSON files'
    )
    
    args = parser.parse_args()
    
    json_dir = Path(args.json_dir)
    json_files = sorted(json_dir.glob("*.json"))
    
    # Filter quality standards files
    qs_files = [
        f for f in json_files 
        if not any(skip in f.name.lower() for skip in [
            'extraction_', 'front_matter', '_error', 'analysis', 'test'
        ])
    ]
    
    print(f"📊 QUALITY STANDARDS RAILWAY INGESTION")
    print(f"=" * 60)
    print(f"Railway URL: {args.railway_url}")
    print(f"Collection: {args.collection}")
    print(f"Files found: {len(qs_files)}")
    print()
    
    # Process all files and collect chunks
    all_chunks = []
    
    for json_file in qs_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                qs_data = json.load(f)
            
            chunks = create_chunks_from_quality_standard(qs_data, str(json_file))
            all_chunks.extend(chunks)
            
            print(f"✓ Processed {qs_data.get('title', json_file.name)}: {len(chunks)} chunks")
            
        except Exception as e:
            print(f"✗ Error processing {json_file.name}: {e}")
    
    print(f"\nTotal chunks to send: {len(all_chunks)}")
    
    # Send to Railway
    print(f"\n🚀 Sending to Railway...")
    result = await send_chunks_to_railway(all_chunks, args.railway_url, args.collection)
    
    if "error" in result:
        print(f"❌ Failed: {result['error']}")
        return 1
    else:
        print(f"✅ Success: {result.get('message', 'Chunks ingested')}")
        print(f"   Chunks ingested: {result.get('chunks_ingested', 0)}")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)