#!/usr/bin/env python3
"""Test enhanced extraction specifically on GP21 Assessment subsection."""

import sys
import os
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

import json
import asyncio
from src.agents.ontario_orchestrator.ingestion.extractors.ohip_extractor import EnhancedSubsectionExtractor

async def test_assessment_subsection():
    """Test extraction specifically for GP21 Assessment subsection with complex tables."""
    
    TOC_FILE = 'data/processed/toc_extracted.json'
    PDF_FILE = "data/ontario/ohip/moh-schedule-benefit-2024-03-04.pdf"
    
    # Load TOC
    with open(TOC_FILE) as f:
        toc_data = json.load(f)
    
    # Find GP21 Assessment subsection
    assessment_subsection = None
    for entry in toc_data['entries']:
        if entry['level'] == 1 and entry.get('parent') == 'GP':
            if entry['page_ref'] == 'GP21' and 'Assessment' in entry['title']:
                assessment_subsection = entry
                print(f"Found Assessment subsection: {entry['page_ref']} - {entry['title']}")
                break
    
    if not assessment_subsection:
        print("GP21 Assessment subsection not found!")
        return
    
    # Create extractor
    extractor = EnhancedSubsectionExtractor(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        max_concurrent=1
    )
    
    # Load ranges and build mapping
    extractor.section_ranges = extractor.load_cleaned_page_ranges()
    print("\nBuilding page mapping...")
    extractor.page_mapping = extractor.build_page_reference_mapping(PDF_FILE)
    
    # Get page range for Assessment subsection
    page_range = extractor.get_subsection_page_range(
        assessment_subsection, 
        toc_data['entries'],
        extractor.page_mapping,
        extractor.section_ranges
    )
    
    if page_range:
        start_page, end_page = page_range
        print(f"\nProcessing Assessment subsection:")
        print(f"  Title: {assessment_subsection['title']}")
        print(f"  Page ref: {assessment_subsection['page_ref']}")
        print(f"  Pages: {start_page}-{end_page} ({end_page - start_page + 1} pages)")
        
        # Process the subsection
        result = await extractor.process_subsection(
            assessment_subsection, start_page, end_page, PDF_FILE
        )
        
        # Show results
        print(f"\nResults:")
        print(f"  Fee codes found: {len(result.get('fee_codes', []))}")
        print(f"  Chunks processed: {result.get('chunks_processed', 1)}")
        print(f"  Table structures detected: {result.get('table_structures_detected', {})}")
        
        # Look for specific codes that should be there
        target_codes = ['K001', 'K017', 'K130', 'K131', 'K132', 'K133', 'K267', 'K269', 'E080']
        found_codes = {fc['code'] for fc in result.get('fee_codes', [])}
        
        print(f"\nExpected fee codes:")
        for code in target_codes:
            status = "✓" if code in found_codes else "✗"
            print(f"  {status} {code}")
        
        # Show detention table extraction
        k001_found = False
        for fc in result.get('fee_codes', []):
            if fc.get('code') == 'K001':
                k001_found = True
                print(f"\nK001 Detention extracted:")
                print(f"  Description: {fc.get('description', '')}")
                print(f"  Fee: ${fc.get('fee', 'NOT FOUND')}")
                print(f"  Units: {fc.get('units', '')}")
                print(f"  Conditions: {fc.get('conditions', '')[:100]}...")
                break
        
        if not k001_found:
            print("\n✗ K001 detention code NOT extracted (should be $21.10 per quarter hour)")
        
        # Show sample fee codes
        if result.get('fee_codes'):
            print(f"\nSample fee codes extracted:")
            for fc in result['fee_codes'][:10]:
                fee_str = ""
                if fc.get('fee'):
                    fee_str = f"${fc['fee']}"
                elif fc.get('h_fee') and fc.get('p_fee'):
                    fee_str = f"H: ${fc['h_fee']} / P: ${fc['p_fee']}"
                
                desc = fc.get('description', '')[:50]
                print(f"  {fc.get('code', 'N/A'):8} - {desc:50} {fee_str}")
        
        # Check if time requirement table was captured
        print("\nTime requirement table detection:")
        for fc in result.get('fee_codes', []):
            if 'minutes' in str(fc.get('conditions', '')).lower():
                print(f"  Found time requirement for {fc['code']}: {fc.get('conditions', '')[:80]}...")
                break
        
        # Save result
        output_file = Path('data/processed/assessment_enhanced_test.json')
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nFull results saved to: {output_file}")
    else:
        print(f"Could not determine page range for Assessment subsection")

if __name__ == '__main__':
    asyncio.run(test_assessment_subsection())