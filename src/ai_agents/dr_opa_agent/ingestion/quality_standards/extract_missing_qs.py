"""
Extract missing Quality Standards PDFs that failed in the initial batch.

This script specifically targets the 5 PDFs that failed extraction.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from src.ai_agents.dr_opa_agent.ingestion.quality_standards.qs_extractor_v3 import QualityStandardsExtractorV3

async def extract_missing_pdfs():
    """Extract the 5 PDFs that failed in the batch extraction."""
    
    # List of PDFs that failed
    failed_pdfs = [
        "qs-eating-disorders-quality-standard-en.pdf",
        "qs-schizophrenia-care-in-hospitals-quality-standard-en.pdf",
        "qs-schizophrenia-care-in-the-community-quality-standard-en.pdf",
        "qs-sickle-cell-disease-quality-standard-en.pdf",
        "qs-surgical-site-infections-quality-standard-en.pdf"
    ]
    
    input_dir = Path("data/dr_opa_agent/raw/oh_quality_std")
    output_dir = Path("data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304")
    
    extractor = QualityStandardsExtractorV3()
    
    print(f"Attempting to extract {len(failed_pdfs)} previously failed PDFs...")
    print("=" * 60)
    
    success_count = 0
    
    for pdf_name in failed_pdfs:
        pdf_path = input_dir / pdf_name
        output_path = output_dir / f"{pdf_path.stem}.json"
        
        print(f"\nProcessing: {pdf_name}")
        
        try:
            # Try extraction with increased timeout
            document = await extractor.extract_document(
                str(pdf_path),
                str(output_path)
            )
            
            print(f"✓ Successfully extracted {pdf_name}")
            print(f"  - Front matter sections: {sum(bool(getattr(document.front_matter, field, None)) for field in ['executive_summary', 'scope', 'why_needed', 'how_measured', 'definitions', 'principles', 'for_patients', 'for_clinicians', 'system_support'])}/9")
            print(f"  - Quality statements: {len(document.statements)}")
            success_count += 1
            
        except Exception as e:
            print(f"✗ Failed again: {pdf_name}")
            print(f"  Error: {str(e)[:200]}")
            
            # Save error details
            import json
            error_path = output_dir / f"{pdf_path.stem}_error_retry.json"
            with open(error_path, 'w') as f:
                json.dump({
                    'pdf': str(pdf_path),
                    'error': str(e),
                    'type': type(e).__name__
                }, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"Extraction complete: {success_count}/{len(failed_pdfs)} PDFs successfully extracted")
    
    if success_count < len(failed_pdfs):
        print(f"Still failed: {len(failed_pdfs) - success_count} PDFs could not be extracted")

if __name__ == "__main__":
    asyncio.run(extract_missing_pdfs())