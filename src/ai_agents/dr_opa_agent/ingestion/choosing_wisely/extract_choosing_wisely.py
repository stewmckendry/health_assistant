#!/usr/bin/env python3
"""
Script to extract Choosing Wisely Canada recommendations from PDF.

This script uses the ChoosingWiselyExtractor to process the PDF and extract
structured recommendations for each specialty section.
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
from datetime import datetime
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from cw_extractor import ChoosingWiselyExtractor

# Load environment variables from project root
project_root = Path("/Users/liammckendry/health_assistant_cw_integration")
load_dotenv(project_root / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'choosing_wisely_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def extract_single_specialty(extractor: ChoosingWiselyExtractor, specialty: str, start: int, end: int):
    """
    Extract a single specialty for testing.
    
    Args:
        extractor: The extractor instance
        specialty: Name of the specialty
        start: Start page
        end: End page
    """
    logger.info(f"Extracting {specialty} (pages {start}-{end})")
    
    pages = extractor.extract_pdf_pages(start, end)
    section = extractor.extract_specialty(specialty, pages)
    
    logger.info(f"Extracted {len(section.recommendations)} recommendations for {specialty}")
    
    # Save to file
    project_root = Path("/Users/liammckendry/health_assistant_cw_integration")
    output_path = project_root / f"data/dr_opa_agent/processed/choosing_wisely/{specialty.lower().replace(' ', '_').replace('&', 'and')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(section.to_dict(), f, indent=2)
    
    return section


def extract_all_specialties():
    """
    Extract all specialties from the PDF.
    """
    # Use absolute paths from project root
    project_root = Path("/Users/liammckendry/health_assistant_cw_integration")
    pdf_path = project_root / "data/dr_opa_agent/raw/choosing_wisely/Choosing-Wisely-Canada-collection-of-lists-July-6-2022.pdf"
    csv_path = project_root / "data/dr_opa_agent/raw/choosing_wisely/section_map.csv"
    output_dir = project_root / "data/dr_opa_agent/processed/choosing_wisely"
    
    # Check if files exist
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    if not Path(csv_path).exists():
        logger.error(f"CSV mapping not found: {csv_path}")
        return
    
    # Initialize extractor
    try:
        extractor = ChoosingWiselyExtractor(pdf_path, csv_path)
        logger.info(f"Initialized extractor with {len(extractor.specialty_pages)} specialties")
    except Exception as e:
        logger.error(f"Failed to initialize extractor: {e}")
        return
    
    # Extract all specialties
    logger.info("Starting extraction of all specialties...")
    
    try:
        # Configure batch processing
        # GPT-4o-mini rate limits: 500 RPM, 30,000,000 TPM
        # Process in batches of 3 with sync calls
        batch_size = 3  # Process 3 at a time
        
        logger.info(f"Processing {len(extractor.specialty_pages)} specialties in batches of {batch_size}")
        
        sections = extractor.extract_all_specialties(
            batch_size=batch_size,
            output_dir=output_dir
        )
        
        # Validate extraction
        report = extractor.validate_extraction(sections)
        
        # Save combined results
        combined_output = {
            "extraction_date": datetime.now().isoformat(),
            "pdf_path": str(pdf_path),  # Convert PosixPath to string for JSON serialization
            "total_sections": len(sections),
            "validation_report": report,
            "sections": [section.to_dict() for section in sections]
        }
        
        combined_path = output_dir / "all_sections_combined.json"
        with open(combined_path, 'w') as f:
            json.dump(combined_output, f, indent=2)
        
        # Save extraction report
        extractor.save_extraction_report(sections, str(output_dir / "extraction_report.json"))
        
        # Print summary
        print("\n" + "="*60)
        print("EXTRACTION COMPLETE")
        print("="*60)
        print(f"Total specialties expected: {report['total_specialties_expected']}")
        print(f"Total specialties extracted: {report['total_specialties_extracted']}")
        print(f"Specialties with recommendations: {report['specialties_with_recommendations']}")
        print(f"Total recommendations: {report['total_recommendations']}")
        print(f"Extraction rate: {report['extraction_rate']:.1f}%")
        print(f"Average recommendations per specialty: {report['average_recommendations_per_specialty']:.1f}")
        
        if report['specialties_missing_data']:
            print(f"\nSpecialties with missing data: {', '.join(report['specialties_missing_data'])}")
        
        print(f"\nResults saved to: {output_dir}")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)


def test_extraction():
    """
    Test extraction with a few specialties.
    """
    # Use absolute paths from project root
    project_root = Path("/Users/liammckendry/health_assistant_cw_integration")
    pdf_path = project_root / "data/dr_opa_agent/raw/choosing_wisely/Choosing-Wisely-Canada-collection-of-lists-July-6-2022.pdf"
    csv_path = project_root / "data/dr_opa_agent/raw/choosing_wisely/section_map.csv"
    
    try:
        extractor = ChoosingWiselyExtractor(pdf_path, csv_path)
        
        # Test with first 3 specialties
        test_specialties = list(extractor.specialty_pages.items())[:3]
        
        for specialty, (start, end) in test_specialties:
            section = extract_single_specialty(extractor, specialty, start, end)
            
            print(f"\n{'='*60}")
            print(f"Specialty: {section.specialty}")
            print(f"Organization: {section.organization}")
            print(f"Last Updated: {section.last_updated}")
            print(f"Number of Recommendations: {len(section.recommendations)}")
            
            if section.recommendations:
                print(f"\nFirst Recommendation:")
                rec = section.recommendations[0]
                print(f"  #{rec.number}: {rec.title}")
                print(f"  Description: {rec.description[:200]}...")
                if rec.pmids:
                    print(f"  PMIDs: {', '.join(rec.pmids[:3])}")
        
    except Exception as e:
        logger.error(f"Test extraction failed: {e}", exc_info=True)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract Choosing Wisely Canada recommendations")
    parser.add_argument("--test", action="store_true", help="Run test extraction with a few specialties")
    parser.add_argument("--specialty", help="Extract a single specialty")
    parser.add_argument("--all", action="store_true", help="Extract all specialties")
    
    args = parser.parse_args()
    
    if args.test:
        test_extraction()
    elif args.specialty:
        # Extract single specialty
        project_root = Path(__file__).parent.parent.parent.parent.parent
        pdf_path = project_root / "data/dr_opa_agent/raw/choosing_wisely/Choosing-Wisely-Canada-collection-of-lists-July-6-2022.pdf"
        csv_path = project_root / "data/dr_opa_agent/raw/choosing_wisely/section_map.csv"
        
        extractor = ChoosingWiselyExtractor(pdf_path, csv_path)
        
        if args.specialty in extractor.specialty_pages:
            start, end = extractor.specialty_pages[args.specialty]
            extract_single_specialty(extractor, args.specialty, start, end)
        else:
            print(f"Specialty '{args.specialty}' not found in mappings")
            print(f"Available specialties: {', '.join(sorted(extractor.specialty_pages.keys()))}")
    else:
        # Default to extracting all
        extract_all_specialties()


if __name__ == "__main__":
    main()