#!/usr/bin/env python3
"""
Test the enhanced ADP extractor with LLM support
"""

import os
import sys
import json
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.agents.dr_off_agent.ingestion.extractors.adp_extractor import EnhancedADPExtractor

def test_battery_exclusion():
    """Test if the battery exclusion is properly detected"""
    
    # Initialize extractor with LLM support
    extractor = EnhancedADPExtractor(use_llm=True)
    
    # Test text that contains battery exclusion
    test_text = """
    ADP does not provide funding towards the cost of repairs and/or maintenance and/or batteries.
    
    The client is responsible for routine maintenance and battery replacement costs.
    """
    
    # Test regex extraction first
    regex_exclusions = extractor.harvest_exclusions_regex(test_text)
    print("Regex exclusions found:")
    for exc in regex_exclusions:
        print(f"  - {exc['phrase']}: {exc.get('applies_to', 'general')}")
    
    # Test full hybrid extraction (regex + LLM)
    exclusions = extractor.harvest_exclusions(test_text, "502.01", "Power Wheelchairs")
    print("\nHybrid exclusions found:")
    for exc in exclusions:
        print(f"  - {exc['phrase']}: {exc.get('applies_to', 'general')}")
        if exc.get('llm_extracted'):
            print("    (extracted by LLM)")
    
    # Check if battery exclusion was found
    battery_found = any('batter' in str(exc).lower() for exc in exclusions)
    print(f"\nBattery exclusion detected: {battery_found}")
    
    return battery_found

def test_full_extraction():
    """Test full extraction on actual ADP mobility document"""
    
    # Path to ADP mobility PDF
    pdf_path = Path("data/dr_off_agent/ontario/adp/adp_mobility_aids_and_equipment_manual_feb_2025.pdf")
    
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    print(f"\nExtracting from: {pdf_path.name}")
    
    # Initialize extractor with LLM support
    extractor = EnhancedADPExtractor(use_llm=True)
    
    # Extract sections
    sections = extractor.extract(str(pdf_path), adp_doc="mobility")
    
    print(f"\nExtracted {len(sections)} sections")
    
    # Look for sections with battery/repair exclusions
    battery_sections = []
    for section in sections:
        if section.exclusions:
            for exc in section.exclusions:
                if 'batter' in str(exc).lower() or 'repair' in str(exc).lower():
                    battery_sections.append(section)
                    break
    
    print(f"\nSections with battery/repair exclusions: {len(battery_sections)}")
    
    # Show details of first few sections with exclusions
    for section in battery_sections[:3]:
        print(f"\nSection {section.section_id}: {section.title}")
        print(f"  Exclusions found: {len(section.exclusions)}")
        for exc in section.exclusions[:3]:
            print(f"    - {exc['phrase']}")
            if exc.get('llm_extracted'):
                print("      (extracted by LLM)")
    
    # Save results for inspection
    output_dir = Path("tests/dr_off_agent/test_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "adp_llm_extraction_test.json"
    extractor.save_results(sections[:10], str(output_file))  # Save first 10 sections for review
    
    print(f"\nTest results saved to: {output_file}")
    
    return len(battery_sections) > 0

if __name__ == "__main__":
    print("Testing ADP Extractor with LLM Enhancement")
    print("=" * 50)
    
    # Test 1: Simple text extraction
    print("\nTest 1: Battery exclusion detection from text")
    test1_passed = test_battery_exclusion()
    
    # Test 2: Full PDF extraction
    print("\n" + "=" * 50)
    print("\nTest 2: Full PDF extraction with LLM")
    test2_passed = test_full_extraction()
    
    # Summary
    print("\n" + "=" * 50)
    print("\nTest Summary:")
    print(f"  Test 1 (Text extraction): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"  Test 2 (PDF extraction): {'PASSED' if test2_passed else 'FAILED'}")