#!/usr/bin/env python3
"""
Extract missing Choosing Wisely specialties with rate limit handling.
"""

import sys
import time
import logging
from pathlib import Path

# Import from same directory
from cw_extractor import ChoosingWiselyExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Missing specialties to extract
MISSING_SPECIALTIES = [
    "Oncology",
    "Paediatrics", 
    "Psychiatry",
    "Public Health",
    "Respiratory Medicine",
    "Rheumatology",
    "Spine",
    "Sport and Exercise Medicine",
    "Trauma",
    "Urology"
]

def main():
    # Use absolute paths
    base_path = Path("/Users/liammckendry/health_assistant_cw_integration")
    pdf_path = base_path / "data" / "dr_opa_agent" / "raw" / "choosing_wisely" / "Choosing-Wisely-Canada-collection-of-lists-July-6-2022.pdf"
    csv_path = base_path / "data" / "dr_opa_agent" / "raw" / "choosing_wisely" / "section_map.csv"
    output_dir = base_path / "data" / "dr_opa_agent" / "processed" / "choosing_wisely"
    
    logger.info(f"Initializing extractor with PDF: {pdf_path}")
    extractor = ChoosingWiselyExtractor(pdf_path=str(pdf_path), mapping_csv_path=str(csv_path))
    
    logger.info(f"Extracting {len(MISSING_SPECIALTIES)} missing specialties...")
    
    # Process one at a time with delays to avoid rate limits
    for i, specialty_name in enumerate(MISSING_SPECIALTIES, 1):
        logger.info(f"[{i}/{len(MISSING_SPECIALTIES)}] Processing {specialty_name}...")
        
        # Check if already exists
        filename = output_dir / f"{specialty_name.lower().replace(' ', '_').replace('&', 'and')}.json"
        if filename.exists():
            logger.info(f"  Already exists: {filename}")
            continue
        
        # Get page range from mappings
        if specialty_name not in extractor.specialty_pages:
            logger.warning(f"  No mapping found for {specialty_name}, skipping")
            continue
            
        start_page, end_page = extractor.specialty_pages[specialty_name]
        logger.info(f"  Pages {start_page}-{end_page}")
        
        try:
            # Extract pages
            pages = extractor.extract_pdf_pages(start_page, end_page)
            
            # Extract specialty
            section = extractor.extract_specialty(specialty_name, pages)
            
            # Save if successful
            if section.recommendations:
                import json
                with open(filename, 'w') as f:
                    json.dump(section.to_dict(), f, indent=2)
                logger.info(f"  Saved {len(section.recommendations)} recommendations to {filename}")
            else:
                logger.warning(f"  No recommendations extracted for {specialty_name}")
                
        except Exception as e:
            logger.error(f"  Failed to extract {specialty_name}: {e}")
        
        # Wait between extractions to avoid rate limits (30 seconds)
        if i < len(MISSING_SPECIALTIES):
            logger.info("  Waiting 30 seconds before next extraction...")
            time.sleep(30)
    
    logger.info("Extraction complete!")
    
    # Summary
    extracted = sum(1 for spec in MISSING_SPECIALTIES 
                   if (output_dir / f"{spec.lower().replace(' ', '_').replace('&', 'and')}.json").exists())
    logger.info(f"Successfully extracted {extracted}/{len(MISSING_SPECIALTIES)} specialties")

if __name__ == "__main__":
    main()