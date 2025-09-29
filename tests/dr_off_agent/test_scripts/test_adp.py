#!/usr/bin/env python
"""
Test script for adp.get MCP tool
Tests ADP device eligibility and funding determinations
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Activate virtual environment and load env vars
os.system('source ~/spacy_env/bin/activate')
from dotenv import load_dotenv
load_dotenv()

# Import the tool
from src.agents.dr_off_agent.mcp.tools.adp import adp_get

class TestLogger:
    """Simple test logger"""
    def __init__(self):
        self.results = []
    
    def log(self, message):
        print(message)
    
    def log_result(self, test_name, result, expected):
        passed = self._evaluate(result, expected)
        status = "✅ PASS" if passed else "❌ FAIL"
        self.log(f"\n{status}: {test_name}")
        self.results.append((test_name, passed))
        return passed
    
    def _evaluate(self, result, expected):
        """Basic evaluation of results"""
        if 'confidence' in result and result['confidence'] < 0.6:
            return False
        if 'eligibility' in expected and 'eligibility' not in result:
            return False
        return True

async def test_power_wheelchair_cep():
    """Test 2.1: Power Wheelchair with CEP Check"""
    logger = TestLogger()
    logger.log("\n" + "="*60)
    logger.log("Test 2.1: Power Wheelchair with CEP Eligibility")
    logger.log("="*60)
    
    try:
        result = await adp_get({
            "device": {"category": "mobility", "type": "power_wheelchair"},
            "check": ["eligibility", "funding", "cep"],
            "patient_income": 19000
        })
        
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        logger.log(f"Provenance: {result.get('provenance', [])}")
        
        if result.get('funding'):
            funding = result['funding']
            logger.log(f"Funding: {funding.get('adp_contribution', 0)}% ADP, {funding.get('client_share_percent', 0)}% client")
        
        if result.get('cep'):
            cep = result['cep']
            logger.log(f"CEP Eligible: {cep.get('eligible', False)} (income ${19000} < threshold ${cep.get('income_threshold', 0)})")
        
        expected = {
            'eligibility': True,
            'funding': {'adp_contribution': 75}
        }
        
        return logger.log_result("Power Wheelchair CEP", result, expected), result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        return False, None

async def test_scooter_battery_exclusion():
    """Test 2.2: Scooter Battery Exclusion"""
    logger = TestLogger()
    logger.log("\n" + "="*60)
    logger.log("Test 2.2: Scooter Battery Exclusion")
    logger.log("="*60)
    
    try:
        result = await adp_get({
            "device": {"category": "mobility", "type": "scooter_batteries"},
            "check": ["exclusions", "funding"]
        })
        
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        logger.log(f"Provenance: {result.get('provenance', [])}")
        
        exclusions = result.get('exclusions', [])
        if exclusions:
            logger.log(f"Exclusions found: {len(exclusions)}")
            for exc in exclusions[:2]:
                logger.log(f"  - {exc}")
        
        expected = {
            'exclusions': ['batteries']
        }
        
        passed = len(exclusions) > 0 and any('batter' in str(exc).lower() for exc in exclusions)
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Battery exclusion detection")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        return False, None

async def test_walker_elderly():
    """Test 2.3: Walker for Elderly Patient"""
    logger = TestLogger()
    logger.log("\n" + "="*60)
    logger.log("Test 2.3: Walker for Elderly Patient")
    logger.log("="*60)
    
    try:
        result = await adp_get({
            "device": {"category": "mobility", "type": "walker"},
            "check": ["eligibility", "funding"],
            "use_case": {"age": 85, "mobility_limited": True}
        })
        
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        logger.log(f"Provenance: {result.get('provenance', [])}")
        
        if result.get('eligibility'):
            elig = result['eligibility']
            logger.log(f"Basic mobility need: {elig.get('basic_mobility', False)}")
            logger.log(f"Ontario resident: {elig.get('ontario_resident', False)}")
        
        if result.get('funding'):
            funding = result['funding']
            logger.log(f"Funding: {funding.get('adp_contribution', 0)}% ADP, {funding.get('client_share_percent', 0)}% client")
        
        expected = {
            'eligibility': {'basic_mobility': True},
            'funding': {'adp_contribution': 75, 'client_share_percent': 25}
        }
        
        return logger.log_result("Walker Elderly", result, expected), result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        return False, None

async def main():
    """Run all ADP tests"""
    print("\n" + "="*60)
    print("   ADP.GET MCP TOOL TEST SUITE")
    print("   Testing ADP Device Eligibility & Funding")
    print("="*60)
    
    # Check environment
    print("\n🔧 Environment Check:")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Working Dir: {os.getcwd()}")
    print(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    
    # Run tests
    results = []
    
    # Test 1: Power Wheelchair with CEP
    passed1, _ = await test_power_wheelchair_cep()
    results.append(("Power Wheelchair CEP", passed1))
    await asyncio.sleep(1)
    
    # Test 2: Battery Exclusion
    passed2, _ = await test_scooter_battery_exclusion()
    results.append(("Scooter Battery Exclusion", passed2))
    await asyncio.sleep(1)
    
    # Test 3: Walker for Elderly
    passed3, _ = await test_walker_elderly()
    results.append(("Walker Elderly", passed3))
    
    # Summary
    print("\n" + "="*60)
    print("   TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    for test_name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
    
    # Update results file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("scratch_pad/mcp_tools_test_results.md", "a") as f:
        f.write(f"\n\n## ADP.get Test Run - {timestamp}\n")
        f.write(f"Results: {passed}/{total} passed\n")
        for test_name, passed in results:
            f.write(f"- {test_name}: {'PASSED' if passed else 'FAILED'}\n")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)