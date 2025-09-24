#!/usr/bin/env python3
"""
Simple test of the enhanced ADP extractor with LLM support
"""

import os
import sys
import json
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import directly without going through __init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "adp_extractor", 
    Path(__file__).parent.parent.parent.parent / "src/agents/dr_off_agent/ingestion/extractors/adp_extractor.py"
)
adp_extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adp_extractor)

EnhancedADPExtractor = adp_extractor.EnhancedADPExtractor

def test_battery_exclusion():
    """Test if the battery exclusion is properly detected"""
    
    print("\nInitializing extractor with LLM support...")
    extractor = EnhancedADPExtractor(use_llm=True)
    
    # Test text that contains battery exclusion
    test_text = """
    502.01 Power Wheelchairs
    
    ADP does not provide funding towards the cost of repairs and/or maintenance and/or batteries.
    
    The client is responsible for routine maintenance and battery replacement costs.
    
    Additional exclusions include backup devices and cosmetic modifications.
    """
    
    print("\nTesting regex extraction...")
    regex_exclusions = extractor.harvest_exclusions_regex(test_text)
    print(f"Regex exclusions found: {len(regex_exclusions)}")
    for exc in regex_exclusions:
        print(f"  - {exc['phrase']}: {exc.get('applies_to', 'general')}")
    
    print("\nTesting hybrid extraction (regex + LLM)...")
    exclusions = extractor.harvest_exclusions(test_text, "502.01", "Power Wheelchairs")
    print(f"Total exclusions found: {len(exclusions)}")
    for exc in exclusions:
        print(f"  - {exc['phrase']}: {exc.get('applies_to', 'general')}")
        if exc.get('llm_extracted'):
            print("    [Extracted by LLM]")
    
    # Check if battery exclusion was found
    battery_found = any('batter' in str(exc).lower() for exc in exclusions)
    repair_found = any('repair' in str(exc).lower() for exc in exclusions)
    
    print(f"\nResults:")
    print(f"  Battery exclusion detected: {battery_found}")
    print(f"  Repair exclusion detected: {repair_found}")
    
    return battery_found and repair_found

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Enhanced ADP Extractor with LLM Support")
    print("=" * 60)
    
    try:
        test_passed = test_battery_exclusion()
        
        print("\n" + "=" * 60)
        print(f"Test Result: {'✅ PASSED' if test_passed else '❌ FAILED'}")
        print("=" * 60)
        
        if test_passed:
            print("\nThe enhanced ADP extractor successfully detects battery")
            print("and repair exclusions using hybrid regex+LLM extraction.")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()