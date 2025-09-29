#!/usr/bin/env python3
"""Test extraction of Surgical Assistants' Services subsection (GP85-GP92)."""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dotenv import load_dotenv
load_dotenv()

import json
import asyncio
from extract_subsections_parallel import SubsectionExtractor

async def test_surgical_assistants():
    """Test extraction specifically for GP85 Surgical Assistants subsection."""
    
    TOC_FILE = 'data/processed/toc_extracted.json'
    PDF_FILE = "data/ontario/ohip/moh-schedule-benefit-2024-03-04.pdf"
    
    # Load TOC
    with open(TOC_FILE) as f:
        toc_data = json.load(f)
    
    # Find Surgical Assistants subsection
    surgical_subsections = []
    for entry in toc_data['entries']:
        if entry['level'] == 1 and entry.get('parent') == 'GP':
            if 'Surgical Assistant' in entry['title']:
                surgical_subsections.append(entry)
                print(f"Found: {entry['page_ref']} - {entry['title']}")
    
    if not surgical_subsections:
        print("No Surgical Assistants subsections found!")
        return
    
    # Create extractor
    extractor = SubsectionExtractor(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        max_concurrent=1
    )
    
    # Load ranges and build mapping
    extractor.section_ranges = extractor.load_cleaned_page_ranges()
    print("\nBuilding page mapping...")
    extractor.page_mapping = extractor.build_page_reference_mapping(PDF_FILE)
    
    # Process just the first Surgical Assistants subsection
    for subsection in surgical_subsections[:1]:
        page_range = extractor.get_subsection_page_range(
            subsection, 
            toc_data['entries'],
            extractor.page_mapping,
            extractor.section_ranges
        )
        
        if page_range:
            start_page, end_page = page_range
            print(f"\nProcessing: {subsection['title']}")
            print(f"  Page ref: {subsection['page_ref']}")
            print(f"  Pages: {start_page}-{end_page}")
            
            # Process the subsection
            result = await extractor.process_subsection(
                subsection, start_page, end_page, PDF_FILE
            )
            
            # Show results
            print(f"\nResults:")
            print(f"  Fee codes found: {len(result.get('fee_codes', []))}")
            
            # Show specific fee codes mentioned in handover
            target_codes = ['C988B', 'C998B', 'C983B', 'C999B']
            found_codes = {fc['code'] for fc in result.get('fee_codes', [])}
            
            print(f"\nTarget fee codes from handover:")
            for code in target_codes:
                status = "✓" if code in found_codes else "✗"
                print(f"  {status} {code}")
            
            if result.get('fee_codes'):
                print(f"\nSample fee codes extracted:")
                for fc in result['fee_codes'][:5]:
                    print(f"  {fc.get('code', 'N/A'):8} - {fc.get('description', '')[:60]}...")
                    if fc.get('fee'):
                        print(f"           Fee: ${fc['fee']}")
            
            # Save result
            output_file = Path('data/processed/surgical_assistants_test.json')
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull results saved to: {output_file}")
        else:
            print(f"Could not determine page range for {subsection['title']}")

if __name__ == '__main__':
    asyncio.run(test_surgical_assistants())