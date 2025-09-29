#!/usr/bin/env python
"""
Test script for odb.get MCP tool
Tests ODB drug formulary lookups
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Activate virtual environment and load env vars
os.system('source ~/spacy_env/bin/activate')
from dotenv import load_dotenv
load_dotenv()

# Import the tool
from src.agents.dr_off_agent.mcp.tools.odb import odb_get

class TestLogger:
    """Simple test logger"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.results = []
        self.start_time = datetime.now()
        
        # Create output file
        output_dir = Path("tests/dr_off_agent/test_outputs/odb")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = output_dir / f"{test_name}_{timestamp}.json"
    
    def log(self, message):
        print(message)
    
    def save_result(self, result: Dict[str, Any]):
        """Save test result to file"""
        test_data = {
            "test_name": self.test_name,
            "timestamp": self.start_time.isoformat(),
            "elapsed_seconds": (datetime.now() - self.start_time).total_seconds(),
            "result": result
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(test_data, f, indent=2, default=str)
        
        self.log(f"Results saved to: {self.output_file}")

async def test_metformin_coverage():
    """Test 3.1: Metformin Coverage"""
    logger = TestLogger("test_3.1_metformin")
    logger.log("\n" + "="*60)
    logger.log("Test 3.1: Metformin Coverage")
    logger.log("="*60)
    
    try:
        result = await odb_get({
            "drug": "metformin",
            "check_alternatives": True,
            "include_lu": True,
            "top_k": 5
        })
        
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        logger.log(f"Provenance: {result.get('provenance', [])}")
        
        if result.get('coverage'):
            coverage = result['coverage']
            logger.log(f"Covered: {coverage.get('covered', False)}")
            logger.log(f"Generic Name: {coverage.get('generic_name', 'N/A')}")
            logger.log(f"LU Required: {coverage.get('lu_required', False)}")
        
        if result.get('interchangeable'):
            inter = result['interchangeable']
            logger.log(f"Interchangeable Options: {len(inter)} found")
            for i, opt in enumerate(inter[:3], 1):
                logger.log(f"  {i}. DIN: {opt.get('din', 'N/A')} - {opt.get('brand_name', 'N/A')}")
        
        logger.save_result(result)
        
        # Evaluate pass/fail
        passed = result.get('confidence', 0) >= 0.6 and 'coverage' in result
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Metformin coverage check")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        return False, None

async def test_ozempic_diabetes():
    """Test 3.2: Ozempic for Diabetes"""
    logger = TestLogger("test_3.2_ozempic")
    logger.log("\n" + "="*60)
    logger.log("Test 3.2: Ozempic for Type 2 Diabetes")
    logger.log("="*60)
    
    try:
        result = await odb_get({
            "drug": "Ozempic",
            "check_alternatives": True,
            "include_lu": True,
            "top_k": 5
        })
        
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        logger.log(f"Provenance: {result.get('provenance', [])}")
        
        if result.get('coverage'):
            coverage = result['coverage']
            logger.log(f"Covered: {coverage.get('covered', False)}")
            logger.log(f"Generic Name: {coverage.get('generic_name', 'N/A')}")
            logger.log(f"LU Required: {coverage.get('lu_required', False)}")
            if coverage.get('lu_criteria'):
                logger.log(f"LU Criteria: {coverage['lu_criteria'][:100]}...")
        
        if result.get('interchangeable'):
            inter = result['interchangeable']
            logger.log(f"Interchangeable Options: {len(inter)} found")
        
        logger.save_result(result)
        
        # Evaluate pass/fail
        passed = result.get('confidence', 0) >= 0.6 and 'coverage' in result
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Ozempic coverage check")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        return False, None

async def test_statin_alternatives():
    """Test 3.3: Statin Alternatives"""
    logger = TestLogger("test_3.3_statins")
    logger.log("\n" + "="*60)
    logger.log("Test 3.3: Statin Alternatives")
    logger.log("="*60)
    
    try:
        result = await odb_get({
            "drug": "atorvastatin",  # A specific statin
            "check_alternatives": True,
            "include_lu": False,
            "top_k": 8
        })
        
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        logger.log(f"Provenance: {result.get('provenance', [])}")
        
        if result.get('interchangeable'):
            inter = result['interchangeable']
            logger.log(f"Interchangeable Options: {len(inter)} found")
            for i, opt in enumerate(inter[:5], 1):
                din = opt.get('din', 'N/A')
                brand = opt.get('brand_name', 'Unknown')
                generic = opt.get('generic_name', '')
                logger.log(f"  {i}. {brand} ({generic}) - DIN: {din}")
        
        if result.get('lowest_cost'):
            lc = result['lowest_cost']
            logger.log(f"Lowest Cost Option: {lc.get('brand_name', 'N/A')} - DIN: {lc.get('din', 'N/A')}")
        
        logger.save_result(result)
        
        # Evaluate pass/fail
        passed = result.get('confidence', 0) >= 0.6 and (result.get('interchangeable') or result.get('coverage'))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Statin alternatives check")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        return False, None

async def test_januvia_generic():
    """Test 3.4: Januvia Generic Check"""
    logger = TestLogger("test_3.4_januvia")
    logger.log("\n" + "="*60)
    logger.log("Test 3.4: Januvia Generic Availability")
    logger.log("="*60)
    
    try:
        result = await odb_get({
            "drug": "Januvia",
            "check_alternatives": True,
            "include_lu": True,
            "top_k": 5
        })
        
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        logger.log(f"Provenance: {result.get('provenance', [])}")
        
        if result.get('coverage'):
            coverage = result['coverage']
            logger.log(f"Covered: {coverage.get('covered', False)}")
            logger.log(f"Generic Name: {coverage.get('generic_name', 'N/A')}")
            logger.log(f"Brand Name: {coverage.get('brand_name', 'N/A')}")
        
        if result.get('interchangeable'):
            inter = result['interchangeable']
            logger.log(f"Generic/Interchangeable Options: {len(inter)} found")
            # Check if any are generics (usually have empty brand names or contain generic name)
            generics = [opt for opt in inter if not opt.get('brand_name') or opt.get('brand_name') == opt.get('generic_name')]
            if generics:
                logger.log(f"Generic Available: Yes ({len(generics)} options)")
            else:
                logger.log(f"Generic Available: No")
        
        logger.save_result(result)
        
        # Evaluate pass/fail
        passed = result.get('confidence', 0) >= 0.6 and (result.get('interchangeable') or result.get('coverage'))
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Januvia generic check")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        return False, None

async def main():
    """Run all ODB tests"""
    print("\n" + "="*60)
    print("   ODB.GET MCP TOOL TEST SUITE")
    print("   Testing ODB Drug Formulary Lookups")
    print("="*60)
    
    # Check environment
    print("\n🔧 Environment Check:")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Working Dir: {os.getcwd()}")
    print(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    
    # Run tests
    results = []
    
    # Test 1: Metformin
    passed1, _ = await test_metformin_coverage()
    results.append(("Metformin Coverage", passed1))
    await asyncio.sleep(1)
    
    # Test 2: Ozempic
    passed2, _ = await test_ozempic_diabetes()
    results.append(("Ozempic for Diabetes", passed2))
    await asyncio.sleep(1)
    
    # Test 3: Statins
    passed3, _ = await test_statin_alternatives()
    results.append(("Statin Alternatives", passed3))
    await asyncio.sleep(1)
    
    # Test 4: Januvia
    passed4, _ = await test_januvia_generic()
    results.append(("Januvia Generic", passed4))
    
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
        f.write(f"\n\n## ODB.get Test Run - {timestamp}\n")
        f.write(f"Results: {passed}/{total} passed\n")
        for test_name, passed in results:
            f.write(f"- {test_name}: {'PASSED' if passed else 'FAILED'}\n")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)