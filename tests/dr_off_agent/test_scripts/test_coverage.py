#!/usr/bin/env python
"""
Test script for coverage.answer MCP tool
Tests the main orchestrator that routes queries to appropriate tools
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
from src.agents.dr_off_agent.mcp.tools.coverage import coverage_answer

class TestLogger:
    """Simple test logger"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.results = []
        self.start_time = datetime.now()
        
        # Create output file
        output_dir = Path("tests/dr_off_agent/test_outputs/coverage")
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

async def test_complex_multi_domain():
    """Test 4.1: Complex Multi-Domain Query"""
    logger = TestLogger("test_4.1_multi_domain")
    logger.log("\n" + "="*60)
    logger.log("Test 4.1: Complex Multi-Domain Query")
    logger.log("="*60)
    
    query = "75yo patient discharged after 3 days, can I bill C124 as MRP? Also needs walker - what's covered?"
    logger.log(f"Query: {query}")
    
    try:
        result = await coverage_answer({
            "question": query,
            "context": {
                "patient_age": 75,
                "admission_duration": "3 days",
                "role": "physician"
            },
            "include_sources": True
        })
        
        logger.log(f"\nProvenance: {result.get('provenance', [])}")
        logger.log(f"Tools Used: {result.get('tools_used', [])}")
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        
        if result.get('answer'):
            logger.log(f"\nAnswer Preview:")
            logger.log(result['answer'][:500] + "..." if len(result.get('answer', '')) > 500 else result['answer'])
        
        if result.get('evidence'):
            logger.log(f"\nEvidence Items: {len(result['evidence'])}")
            for i, ev in enumerate(result['evidence'][:3], 1):
                logger.log(f"  {i}. {ev.get('type', 'unknown')}: {str(ev.get('data', ''))[:100]}...")
        
        logger.save_result(result)
        
        # Evaluate
        passed = result.get('confidence', 0) >= 0.6 and len(result.get('tools_used', [])) >= 2
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Multi-domain orchestration")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None

async def test_ambiguous_billing():
    """Test 4.2: Ambiguous Billing Query"""
    logger = TestLogger("test_4.2_ambiguous")
    logger.log("\n" + "="*60)
    logger.log("Test 4.2: Ambiguous Billing Query")
    logger.log("="*60)
    
    query = "Which discharge codes apply for Thursday discharge?"
    logger.log(f"Query: {query}")
    
    try:
        result = await coverage_answer({
            "question": query,
            "context": {
                "day_of_week": "Thursday",
                "role": "physician"
            },
            "include_sources": True
        })
        
        logger.log(f"\nProvenance: {result.get('provenance', [])}")
        logger.log(f"Tools Used: {result.get('tools_used', [])}")
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        
        if result.get('answer'):
            logger.log(f"\nAnswer Preview:")
            logger.log(result['answer'][:500] + "..." if len(result.get('answer', '')) > 500 else result['answer'])
        
        if result.get('clarifications'):
            logger.log(f"\nClarifications Requested: {result['clarifications']}")
        
        logger.save_result(result)
        
        # Evaluate
        passed = result.get('confidence', 0) >= 0.5 and 'schedule' in result.get('tools_used', [])
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Billing query handling")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None

async def test_drug_alternatives():
    """Test 4.3: Drug Coverage with Alternatives"""
    logger = TestLogger("test_4.3_drug_alternatives")
    logger.log("\n" + "="*60)
    logger.log("Test 4.3: Drug Coverage with Alternatives")
    logger.log("="*60)
    
    query = "Is Jardiance covered? What are cheaper alternatives?"
    logger.log(f"Query: {query}")
    
    try:
        result = await coverage_answer({
            "question": query,
            "context": {
                "role": "physician",
                "looking_for": "cost_effective_options"
            },
            "include_sources": True
        })
        
        logger.log(f"\nProvenance: {result.get('provenance', [])}")
        logger.log(f"Tools Used: {result.get('tools_used', [])}")
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        
        if result.get('answer'):
            logger.log(f"\nAnswer Preview:")
            logger.log(result['answer'][:500] + "..." if len(result.get('answer', '')) > 500 else result['answer'])
        
        if result.get('evidence'):
            logger.log(f"\nEvidence Items: {len(result['evidence'])}")
            for i, ev in enumerate(result['evidence'][:3], 1):
                if ev.get('type') == 'drug_coverage':
                    logger.log(f"  Drug: {ev.get('data', {}).get('drug', 'N/A')}")
                    logger.log(f"  Covered: {ev.get('data', {}).get('covered', 'Unknown')}")
        
        logger.save_result(result)
        
        # Evaluate
        passed = result.get('confidence', 0) >= 0.6 and 'odb' in result.get('tools_used', [])
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Drug alternatives query")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None

async def test_simple_query():
    """Test 4.4: Simple Single-Tool Query"""
    logger = TestLogger("test_4.4_simple")
    logger.log("\n" + "="*60)
    logger.log("Test 4.4: Simple Single-Tool Query")
    logger.log("="*60)
    
    query = "What's the fee for code A135?"
    logger.log(f"Query: {query}")
    
    try:
        result = await coverage_answer({
            "question": query,
            "include_sources": False
        })
        
        logger.log(f"\nProvenance: {result.get('provenance', [])}")
        logger.log(f"Tools Used: {result.get('tools_used', [])}")
        logger.log(f"Confidence: {result.get('confidence', 0):.2f}")
        
        if result.get('answer'):
            logger.log(f"\nAnswer: {result['answer']}")
        
        logger.save_result(result)
        
        # Evaluate
        passed = result.get('confidence', 0) >= 0.8 and 'schedule' in result.get('tools_used', [])
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.log(f"\n{status}: Simple query routing")
        
        return passed, result
        
    except Exception as e:
        logger.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None

async def main():
    """Run all coverage.answer tests"""
    print("\n" + "="*60)
    print("   COVERAGE.ANSWER MCP TOOL TEST SUITE")
    print("   Testing Main Orchestrator")
    print("="*60)
    
    # Check environment
    print("\n🔧 Environment Check:")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Working Dir: {os.getcwd()}")
    print(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    
    # Run tests
    results = []
    
    # Test 1: Multi-domain
    passed1, _ = await test_complex_multi_domain()
    results.append(("Complex Multi-Domain", passed1))
    await asyncio.sleep(1)
    
    # Test 2: Ambiguous billing
    passed2, _ = await test_ambiguous_billing()
    results.append(("Ambiguous Billing", passed2))
    await asyncio.sleep(1)
    
    # Test 3: Drug alternatives
    passed3, _ = await test_drug_alternatives()
    results.append(("Drug Alternatives", passed3))
    await asyncio.sleep(1)
    
    # Test 4: Simple query
    passed4, _ = await test_simple_query()
    results.append(("Simple Query", passed4))
    
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
        f.write(f"\n\n## coverage.answer Test Run - {timestamp}\n")
        f.write(f"Results: {passed}/{total} passed\n")
        for test_name, passed in results:
            f.write(f"- {test_name}: {'PASSED' if passed else 'FAILED'}\n")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)