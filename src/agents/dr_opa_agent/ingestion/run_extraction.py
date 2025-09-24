#!/usr/bin/env python3
"""
Master script for extracting documents from various sources.

Usage:
    python run_extraction.py --source cpso [--types policies advice statements] [--workers 5]
    python run_extraction.py --source ontario_health --url https://...
"""

import argparse
import os
import sys
from pathlib import Path

def run_cpso_extraction(args):
    """Run CPSO document extraction."""
    from cpso.crawler import CPSOCrawlerParallel, main as cpso_main
    
    print(f"Starting CPSO extraction...")
    print(f"  Document types: {args.types or 'all'}")
    print(f"  Workers: {args.workers}")
    print(f"  Output: {args.output_dir}")
    
    crawler = CPSOCrawlerParallel(
        output_dir=args.output_dir,
        max_workers=args.workers,
        delay_seconds=args.delay,
        resume_from_checkpoint=not args.no_resume
    )
    
    result = crawler.crawl_all(args.types)
    
    print(f"\nExtraction complete!")
    print(f"  Total: {result['total']}")
    print(f"  Success: {result['success']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Skipped: {result['skipped']}")
    
    return result

def run_ontario_health_extraction(args):
    """Run Ontario Health document extraction (placeholder)."""
    print("Ontario Health extraction not yet implemented")
    print("This will extract from ontario.ca/health resources")
    return {}

def run_cep_extraction(args):
    """Run CEP (Centre for Effective Practice) extraction (placeholder)."""
    print("CEP extraction not yet implemented")
    print("This will extract clinical tools and guidelines from CEP")
    return {}

def main():
    parser = argparse.ArgumentParser(description='Extract documents for Dr. OPA agent')
    parser.add_argument('--source', required=True, 
                       choices=['cpso', 'ontario_health', 'cep', 'pho', 'moh'],
                       help='Source organization to extract from')
    
    # CPSO-specific arguments
    parser.add_argument('--types', nargs='+',
                       choices=['policies', 'advice', 'statements'],
                       help='Document types to extract (CPSO only)')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of parallel workers')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Delay between requests in seconds')
    parser.add_argument('--no-resume', action='store_true',
                       help='Start fresh, ignore checkpoint')
    
    # Common arguments
    parser.add_argument('--output-dir', default='data/dr_opa_agent',
                       help='Output directory for extracted documents')
    parser.add_argument('--url', help='Specific URL to extract (for some sources)')
    
    args = parser.parse_args()
    
    # Dispatch to appropriate extractor
    if args.source == 'cpso':
        result = run_cpso_extraction(args)
    elif args.source == 'ontario_health':
        result = run_ontario_health_extraction(args)
    elif args.source == 'cep':
        result = run_cep_extraction(args)
    else:
        print(f"Extractor for {args.source} not yet implemented")
        sys.exit(1)
    
    return 0 if result.get('success', 0) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())