"""
Batch extraction script for all Quality Standards PDFs using enhanced v3 extractor.

Processes all PDFs in the Quality Standards directory and extracts
front matter + quality statements using the improved extractor.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from src.ai_agents.dr_opa_agent.ingestion.quality_standards.qs_extractor_v3 import (
    QualityStandardsExtractorV3,
    QualityStandardDocument
)

# Configure logging
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f'quality_standards_extraction_{timestamp}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BatchQualityStandardsExtractorV3:
    """Batch processor for Quality Standards extraction with enhanced front matter."""
    
    def __init__(self, 
                 input_dir: str = "data/dr_opa_agent/raw/oh_quality_std",
                 output_dir: Optional[str] = None):
        """
        Initialize batch extractor.
        
        Args:
            input_dir: Directory containing Quality Standards PDFs
            output_dir: Directory to save extracted JSON files (will create timestamped subfolder)
        """
        self.input_dir = Path(input_dir)
        
        # Create timestamped output directory
        if output_dir is None:
            base_output = Path("data/dr_opa_agent/processed/quality_standards/extracted_v3")
        else:
            base_output = Path(output_dir)
        
        # Create subfolder with timestamp
        self.output_dir = base_output / f"run_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Output directory: {self.output_dir}")
        
        self.extractor = QualityStandardsExtractorV3()
        
        # Track processing stats
        self.stats = {
            'total_pdfs': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_statements': 0,
            'pdfs_with_errors': []
        }
    
    async def extract_single_pdf(self, pdf_path: Path, skip_existing: bool = True) -> Optional[QualityStandardDocument]:
        """
        Extract a single PDF with enhanced front matter.
        
        Args:
            pdf_path: Path to the PDF file
            skip_existing: Skip if output already exists
            
        Returns:
            Extracted document or None if failed/skipped
        """
        output_path = self.output_dir / f"{pdf_path.stem}.json"
        
        # Check if already processed
        if skip_existing and output_path.exists():
            logger.info(f"Skipping {pdf_path.name} - already extracted")
            self.stats['skipped'] += 1
            
            # Load existing to get statement count
            try:
                with open(output_path, 'r') as f:
                    data = json.load(f)
                    self.stats['total_statements'] += len(data.get('statements', []))
            except:
                pass
            
            return None
        
        logger.info(f"Processing {pdf_path.name}")
        
        try:
            # Extract document with front matter
            document = await self.extractor.extract_document(
                str(pdf_path),
                str(output_path)
            )
            
            self.stats['processed'] += 1
            self.stats['total_statements'] += len(document.statements)
            
            # Log front matter coverage
            fm = document.front_matter
            fm_coverage = sum([
                bool(fm.executive_summary),
                bool(fm.scope),
                bool(fm.why_needed),
                bool(fm.how_measured),
                bool(fm.definitions),
                bool(fm.principles),
                bool(fm.for_patients),
                bool(fm.for_clinicians),
                bool(fm.system_support)
            ])
            
            logger.info(f"✓ Successfully extracted {pdf_path.name}")
            logger.info(f"  - Front matter sections: {fm_coverage}/9")
            logger.info(f"  - Quality statements: {len(document.statements)}")
            
            return document
            
        except Exception as e:
            logger.error(f"✗ Failed to extract {pdf_path.name}: {e}")
            self.stats['failed'] += 1
            self.stats['pdfs_with_errors'].append(pdf_path.name)
            
            # Save error info
            error_path = self.output_dir / f"{pdf_path.stem}_error.json"
            with open(error_path, 'w') as f:
                json.dump({
                    'pdf': str(pdf_path),
                    'error': str(e),
                    'type': type(e).__name__
                }, f, indent=2)
            
            return None
    
    async def extract_batch(self, pdf_files: List[Path], batch_size: int = 2):
        """
        Extract PDFs in batches to avoid overwhelming API.
        
        Args:
            pdf_files: List of PDF files to process
            batch_size: Number of PDFs to process concurrently
        """
        for i in range(0, len(pdf_files), batch_size):
            batch = pdf_files[i:i+batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(pdf_files) + batch_size - 1)//batch_size} ({len(batch)} PDFs)")
            
            # Process batch concurrently
            tasks = [self.extract_single_pdf(pdf) for pdf in batch]
            await asyncio.gather(*tasks)
            
            # Delay between batches to avoid rate limits
            if i + batch_size < len(pdf_files):
                logger.info("Waiting 3 seconds before next batch...")
                await asyncio.sleep(3)
    
    async def extract_all(self, 
                         pattern: str = "*.pdf",
                         limit: Optional[int] = None,
                         batch_size: int = 2):
        """
        Extract all Quality Standards PDFs with enhanced front matter.
        
        Args:
            pattern: File pattern to match
            limit: Maximum number of PDFs to process
            batch_size: Number of PDFs to process concurrently
        """
        # Find all PDFs
        pdf_files = sorted(self.input_dir.glob(pattern))
        
        # Remove duplicates (e.g., files with (1) in name)
        pdf_files = [p for p in pdf_files if '(1)' not in p.name]
        
        self.stats['total_pdfs'] = len(pdf_files)
        
        if limit:
            pdf_files = pdf_files[:limit]
        
        logger.info(f"Found {len(pdf_files)} PDFs to process")
        logger.info(f"Processing with batch size: {batch_size}")
        
        # Process in batches
        start_time = datetime.now()
        await self.extract_batch(pdf_files, batch_size)
        end_time = datetime.now()
        
        # Calculate duration
        duration = end_time - start_time
        self.stats['duration'] = str(duration)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print extraction summary with detailed statistics."""
        print("\n" + "="*60)
        print("QUALITY STANDARDS EXTRACTION SUMMARY")
        print("="*60)
        print(f"Output directory: {self.output_dir}")
        print(f"Total PDFs found: {self.stats['total_pdfs']}")
        print(f"Successfully processed: {self.stats['processed']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped (already extracted): {self.stats['skipped']}")
        print(f"Total quality statements extracted: {self.stats['total_statements']}")
        
        if self.stats.get('duration'):
            print(f"Processing time: {self.stats['duration']}")
        
        if self.stats['processed'] > 0:
            avg_statements = self.stats['total_statements'] / (self.stats['processed'] + self.stats['skipped'])
            print(f"Average statements per document: {avg_statements:.1f}")
        
        if self.stats['pdfs_with_errors']:
            print(f"\nPDFs with errors:")
            for pdf in self.stats['pdfs_with_errors']:
                print(f"  - {pdf}")
        
        print("="*60)
        
        # Save stats
        stats_path = self.output_dir / "extraction_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        print(f"Stats saved to {stats_path}")
        
        # Create summary report
        self.create_summary_report()
    
    def create_summary_report(self):
        """Create a summary report of all extracted documents."""
        summary = []
        
        for json_file in self.output_dir.glob("*.json"):
            if json_file.name == "extraction_stats.json" or "_error" in json_file.name:
                continue
            
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    
                    # Count front matter sections
                    fm = data.get('front_matter', {})
                    fm_count = sum([
                        bool(fm.get('executive_summary')),
                        bool(fm.get('scope')),
                        bool(fm.get('why_needed')),
                        bool(fm.get('how_measured')),
                        bool(fm.get('definitions')),
                        bool(fm.get('principles')),
                        bool(fm.get('for_patients')),
                        bool(fm.get('for_clinicians')),
                        bool(fm.get('system_support'))
                    ])
                    
                    summary.append({
                        'file': json_file.name,
                        'title': data.get('title', 'Unknown'),
                        'year': data.get('year'),
                        'front_matter_sections': f"{fm_count}/9",
                        'statements_count': len(data.get('statements', [])),
                        'statement_numbers': [s['number'] for s in data.get('statements', [])]
                    })
            except:
                pass
        
        # Sort by title
        summary.sort(key=lambda x: x['title'])
        
        # Save summary
        summary_path = self.output_dir / "extraction_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Summary report saved to {summary_path}")


async def main():
    """Main function to run batch extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract all Quality Standards PDFs with enhanced front matter")
    parser.add_argument('--input-dir', default="data/dr_opa_agent/raw/oh_quality_std",
                       help="Directory containing PDFs")
    parser.add_argument('--output-dir', 
                       help="Base directory for extracted files (will create timestamped subfolder)")
    parser.add_argument('--limit', type=int, help="Limit number of PDFs to process")
    parser.add_argument('--batch-size', type=int, default=2,
                       help="Number of PDFs to process concurrently (default: 2)")
    parser.add_argument('--pattern', default="*.pdf",
                       help="File pattern to match (default: *.pdf)")
    
    args = parser.parse_args()
    
    print("="*60)
    print("QUALITY STANDARDS BATCH EXTRACTION V3")
    print("Enhanced with comprehensive front matter extraction")
    print("="*60)
    
    # Create batch extractor
    extractor = BatchQualityStandardsExtractorV3(
        input_dir=args.input_dir,
        output_dir=args.output_dir
    )
    
    # Run extraction
    await extractor.extract_all(
        pattern=args.pattern,
        limit=args.limit,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    asyncio.run(main())