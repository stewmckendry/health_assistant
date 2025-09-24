#!/usr/bin/env python3
"""
Quick test of ADP extraction with LLM - processes only first 5 sections
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
    # Test with mobility devices PDF 
    pdf_path = Path("data/dr_off_agent/ontario/adp/moh-adp-policy-and-administration-manual-mobility-devices-2023-07-01.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"Quick test extraction on: {pdf_path.name}")
    print("(Processing first 10 sections only)")
    print("=" * 60)
    
    # Initialize extractor with LLM support
    print("\nInitializing extractor with LLM support...")
    extractor = EnhancedADPExtractor(use_llm=True)
    
    # Extract just the first 10 sections for quick test
    print("\nExtracting sections...")
    all_sections = extractor.extract(str(pdf_path), adp_doc="mobility")
    sections = all_sections[:10]  # Just process first 10
    
    print(f"\n✅ Processing {len(sections)} sections (out of {len(all_sections)} total)")
    
    # Count statistics  
    total_exclusions = sum(len(s.exclusions) for s in sections)
    total_funding = sum(len(s.funding) for s in sections)
    
    print(f"Exclusions found: {total_exclusions}")
    print(f"Funding rules found: {total_funding}")
    
    # Show sections with exclusions
    print("\nSections with exclusions:")
    for section in sections:
        if section.exclusions:
            print(f"\n  Section {section.section_id}: {section.title}")
            for exc in section.exclusions:
                print(f"    - {exc['phrase']}")
                if exc.get('llm_extracted'):
                    print("      [LLM extracted]")
    
    # Show sections with funding rules
    print("\nSections with funding rules:")
    for section in sections:
        if section.funding:
            print(f"\n  Section {section.section_id}: {section.title}")
            for rule in section.funding:
                scenario = rule['scenario']
                share = rule.get('client_share_percent', 'N/A')
                print(f"    - {scenario}: client pays {share}%")
                if rule.get('llm_extracted'):
                    print("      [LLM extracted]")
    
    # Save sample for inspection
    output_file = Path("tests/dr_off_agent/test_outputs/adp_quick_test.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    sample_data = {
        "pdf_file": str(pdf_path),
        "sections_processed": len(sections),
        "total_sections": len(all_sections),
        "exclusions": total_exclusions,
        "funding_rules": total_funding,
        "sections": [s.to_dict() for s in sections]
    }
    
    with open(output_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    # Check success
    has_exclusions = total_exclusions > 0
    has_funding = total_funding > 0
    
    if has_exclusions and has_funding:
        print("\n" + "=" * 60)
        print("✅ SUCCESS: LLM-enhanced extraction is working!")
        print(f"   Found {total_exclusions} exclusions and {total_funding} funding rules")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  WARNING: Low extraction counts")
        print(f"   Exclusions: {total_exclusions}, Funding: {total_funding}")
        print("=" * 60)


if __name__ == "__main__":
    main()