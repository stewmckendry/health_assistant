"""
Batch extraction script for all Quality Standards PDFs.

Processes all PDFs in the Quality Standards directory and extracts
quality statements using the TOC-based extractor.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from src.ai_agents.dr_opa_agent.ingestion.quality_standards.qs_extractor_v2 import (
    QualityStandardsExtractorV2,
    QualityStandardDocument
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quality_standards_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BatchQualityStandardsExtractor:
    """Batch processor for Quality Standards extraction."""
    
    def __init__(self, 
                 input_dir: str = "data/dr_opa_agent/raw/oh_quality_std",
                 output_dir: str = "data/dr_opa_agent/processed/quality_standards/extracted"):
        """
        Initialize batch extractor.
        
        Args:
            input_dir: Directory containing Quality Standards PDFs
            output_dir: Directory to save extracted JSON files
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.extractor = QualityStandardsExtractorV2()
        
        # Track processing stats
        self.stats = {
            'total_pdfs': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'total_statements': 0
        }
    
    async def extract_single_pdf(self, pdf_path: Path, skip_existing: bool = True) -> Optional[QualityStandardDocument]:
        """
        Extract a single PDF.
        
        Args:
            pdf_path: Path to the PDF file
            skip_existing: Skip if output already exists
            
        Returns:
            Extracted document or None if failed/skipped
        """
        output_path = self.output_dir / f"{pdf_path.stem}_extracted.json"
        
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
            # Extract document
            document = await self.extractor.extract_document(
                str(pdf_path),
                str(output_path)
            )
            
            self.stats['processed'] += 1
            self.stats['total_statements'] += len(document.statements)
            
            logger.info(f"✓ Successfully extracted {len(document.statements)} statements from {pdf_path.name}")
            
            return document
            
        except Exception as e:
            logger.error(f"✗ Failed to extract {pdf_path.name}: {e}")
            self.stats['failed'] += 1
            
            # Save error info
            error_path = self.output_dir / f"{pdf_path.stem}_error.json"
            with open(error_path, 'w') as f:
                json.dump({
                    'pdf': str(pdf_path),
                    'error': str(e),
                    'type': type(e).__name__
                }, f, indent=2)
            
            return None
    
    async def extract_batch(self, pdf_files: List[Path], batch_size: int = 3):
        """
        Extract PDFs in batches to avoid overwhelming API.
        
        Args:
            pdf_files: List of PDF files to process
            batch_size: Number of PDFs to process concurrently
        """
        for i in range(0, len(pdf_files), batch_size):
            batch = pdf_files[i:i+batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} PDFs)")
            
            # Process batch concurrently
            tasks = [self.extract_single_pdf(pdf) for pdf in batch]
            await asyncio.gather(*tasks)
            
            # Delay between batches to avoid rate limits
            if i + batch_size < len(pdf_files):
                logger.info("Waiting 5 seconds before next batch...")
                await asyncio.sleep(5)
    
    async def extract_all(self, 
                         pattern: str = "*.pdf",
                         limit: Optional[int] = None,
                         batch_size: int = 2):
        """
        Extract all Quality Standards PDFs.
        
        Args:
            pattern: File pattern to match
            limit: Maximum number of PDFs to process
            batch_size: Number of PDFs to process concurrently
        """
        # Find all PDFs
        pdf_files = sorted(self.input_dir.glob(pattern))
        self.stats['total_pdfs'] = len(pdf_files)
        
        if limit:
            pdf_files = pdf_files[:limit]
        
        logger.info(f"Found {len(pdf_files)} PDFs to process")
        
        # Process in batches
        await self.extract_batch(pdf_files, batch_size)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print extraction summary."""
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        print(f"Total PDFs found: {self.stats['total_pdfs']}")
        print(f"Successfully processed: {self.stats['processed']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped (already extracted): {self.stats['skipped']}")
        print(f"Total quality statements extracted: {self.stats['total_statements']}")
        
        if self.stats['processed'] > 0:
            avg_statements = self.stats['total_statements'] / (self.stats['processed'] + self.stats['skipped'])
            print(f"Average statements per document: {avg_statements:.1f}")
        
        print("="*60)
        
        # Save stats
        stats_path = self.output_dir / "extraction_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        print(f"Stats saved to {stats_path}")


async def main():
    """Main function to run batch extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract Quality Standards PDFs")
    parser.add_argument('--input-dir', default="data/dr_opa_agent/raw/oh_quality_std",
                       help="Directory containing PDFs")
    parser.add_argument('--output-dir', default="data/dr_opa_agent/processed/quality_standards/extracted",
                       help="Directory for extracted JSON files")
    parser.add_argument('--limit', type=int, help="Limit number of PDFs to process")
    parser.add_argument('--batch-size', type=int, default=2,
                       help="Number of PDFs to process concurrently (default: 2)")
    parser.add_argument('--pattern', default="*.pdf",
                       help="File pattern to match (default: *.pdf)")
    parser.add_argument('--no-skip', action='store_true',
                       help="Re-extract even if output exists")
    
    args = parser.parse_args()
    
    # Create batch extractor
    extractor = BatchQualityStandardsExtractor(
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