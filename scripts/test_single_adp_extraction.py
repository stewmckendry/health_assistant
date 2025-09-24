#!/usr/bin/env python3
"""
Test extraction of a single ADP PDF with LLM enhancement
"""

import os
import sys
import json
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import directly without using __init__.py
import importlib.util

# Load ADP extractor module directly
spec = importlib.util.spec_from_file_location(
    "adp_extractor", 
    Path(__file__).parent.parent / "src/agents/dr_off_agent/ingestion/extractors/adp_extractor.py"
)
adp_extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adp_extractor)

EnhancedADPExtractor = adp_extractor.EnhancedADPExtractor


def main():
    # Test with mobility devices PDF (where battery exclusions should be found)
    pdf_path = Path("data/dr_off_agent/ontario/adp/moh-adp-policy-and-administration-manual-mobility-devices-2023-07-01.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"Testing extraction on: {pdf_path.name}")
    print("=" * 60)
    
    # Initialize extractor with LLM support
    print("\nInitializing extractor with LLM support...")
    extractor = EnhancedADPExtractor(use_llm=True)
    
    # Extract sections
    print("\nExtracting sections...")
    sections = extractor.extract(str(pdf_path), adp_doc="mobility")
    
    print(f"\n✅ Extracted {len(sections)} sections")
    
    # Count statistics
    total_exclusions = sum(len(s.exclusions) for s in sections)
    total_funding = sum(len(s.funding) for s in sections)
    
    print(f"Total exclusions found: {total_exclusions}")
    print(f"Total funding rules found: {total_funding}")
    
    # Look for battery exclusions specifically
    battery_sections = []
    repair_sections = []
    
    for section in sections:
        for exc in section.exclusions:
            exc_str = str(exc).lower()
            if 'batter' in exc_str:
                battery_sections.append((section, exc))
            if 'repair' in exc_str:
                repair_sections.append((section, exc))
    
    print(f"\nBattery exclusions found in {len(battery_sections)} places")
    print(f"Repair exclusions found in {len(repair_sections)} places")
    
    # Show examples
    if battery_sections:
        print("\nExample battery exclusions:")
        for section, exc in battery_sections[:3]:
            print(f"\n  Section {section.section_id}: {section.title}")
            print(f"    Exclusion: {exc['phrase']}")
            if exc.get('llm_extracted'):
                print("    [Extracted by LLM]")
    
    if repair_sections:
        print("\nExample repair exclusions:")
        for section, exc in repair_sections[:3]:
            print(f"\n  Section {section.section_id}: {section.title}")
            print(f"    Exclusion: {exc['phrase']}")
            if exc.get('llm_extracted'):
                print("    [Extracted by LLM]")
    
    # Save results for inspection
    output_file = Path("tests/dr_off_agent/test_outputs/mobility_extraction_llm.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save first 5 sections as sample
    sample_data = {
        "pdf_file": str(pdf_path),
        "total_sections": len(sections),
        "total_exclusions": total_exclusions,
        "total_funding": total_funding,
        "battery_exclusion_count": len(battery_sections),
        "repair_exclusion_count": len(repair_sections),
        "sample_sections": [s.to_dict() for s in sections[:5]]
    }
    
    with open(output_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    # Test result
    if battery_sections and repair_sections:
        print("\n" + "=" * 60)
        print("✅ SUCCESS: Battery and repair exclusions detected with LLM!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED: Battery or repair exclusions not found")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = main()