#!/usr/bin/env python3
"""
Master script for ingesting extracted documents into SQL and vector databases.

Usage:
    python run_ingestion.py --source cpso
    python run_ingestion.py --source ontario_health --input-dir data/dr_opa_agent/processed/ontario_health
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_cpso_ingestion(args):
    """Run CPSO document ingestion."""
    from cpso.batch_ingest import BatchIngester
    
    print(f"Starting CPSO ingestion...")
    print(f"  Input: {args.input_dir}")
    print(f"  Database: {args.db_path}")
    print(f"  Chroma: {args.chroma_path}")
    print(f"  OpenAI Key: {'Available' if args.openai_key else 'Not available (no embeddings will be generated)'}")
    
    ingester = BatchIngester(
        db_path=args.db_path,
        chroma_path=args.chroma_path,
        openai_api_key=args.openai_key
    )
    
    stats = ingester.ingest_directory(args.input_dir)
    
    print(f"\nIngestion complete!")
    print(f"  Total: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Skipped: {stats['skipped']}")
    
    if stats['errors']:
        print(f"\n{len(stats['errors'])} errors encountered:")
        for err in stats['errors'][:5]:
            print(f"  - {err}")
        if len(stats['errors']) > 5:
            print(f"  ... and {len(stats['errors']) - 5} more")
    
    return stats

def run_ontario_health_ingestion(args):
    """Run Ontario Health document ingestion (placeholder)."""
    print("Ontario Health ingestion not yet implemented")
    print("Steps to implement:")
    print("1. Create ontario_health/ingestion.py inheriting from BaseOPAIngester")
    print("2. Implement document-specific extraction logic")
    print("3. Use parent-child chunking from base class")
    return {}

def run_generic_ingestion(args):
    """Run generic document ingestion using base ingester."""
    from base_ingester import BaseOPAIngester
    
    print(f"Generic ingestion for source: {args.source}")
    print("Using base ingester with standard chunking strategy")
    
    # This would need a concrete implementation
    # For now, return placeholder
    return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}

def main():
    parser = argparse.ArgumentParser(description='Ingest documents for Dr. OPA agent')
    parser.add_argument('--source', required=True,
                       choices=['cpso', 'ontario_health', 'cep', 'pho', 'moh', 'generic'],
                       help='Source organization of documents')
    
    # Paths
    parser.add_argument('--input-dir',
                       help='Input directory with extracted documents (default: data/dr_opa_agent/processed/{source})')
    parser.add_argument('--db-path',
                       default='data/dr_opa_agent/opa.db',
                       help='Path to SQLite database')
    parser.add_argument('--chroma-path',
                       default='data/dr_opa_agent/chroma',
                       help='Path to Chroma vector database')
    
    # API Keys
    parser.add_argument('--openai-key',
                       help='OpenAI API key for embeddings (optional, uses env if not provided)')
    
    args = parser.parse_args()
    
    # Set defaults based on source
    if not args.input_dir:
        args.input_dir = f'data/dr_opa_agent/processed/{args.source}'
    
    # Get OpenAI key from environment if not provided
    if not args.openai_key:
        args.openai_key = os.getenv('OPENAI_API_KEY')
    
    # Ensure directories exist
    Path(args.db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.chroma_path).mkdir(parents=True, exist_ok=True)
    
    # Dispatch to appropriate ingester
    if args.source == 'cpso':
        stats = run_cpso_ingestion(args)
    elif args.source == 'ontario_health':
        stats = run_ontario_health_ingestion(args)
    elif args.source == 'generic':
        stats = run_generic_ingestion(args)
    else:
        print(f"Ingester for {args.source} not yet implemented")
        sys.exit(1)
    
    return 0 if stats.get('success', 0) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())