#!/usr/bin/env python
"""
Test script for schedule.get MCP tool
Tests OHIP Schedule of Benefits lookup with realistic clinical scenarios
Outputs detailed results to test_outputs folder for review
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, TextIO

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Activate virtual environment and load env vars
os.system('source ~/spacy_env/bin/activate')
from dotenv import load_dotenv
load_dotenv()

# Import the tool
from src.agents.dr_off_agent.mcp.tools.schedule import schedule_get

class TestLogger:
    """Logger that writes to both console and file"""
    def __init__(self, output_file: str):
        self.output_file = output_file
        self.file_handle = None
    
    def __enter__(self):
        self.file_handle = open(self.output_file, 'w')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_handle:
            self.file_handle.close()
    
    def write(self, message: str):
        """Write to both console and file"""
        print(message)
        if self.file_handle:
            self.file_handle.write(message + "\n")
            self.file_handle.flush()
    
    def write_json(self, data: Dict[str, Any], indent: int = 2):
        """Write JSON data formatted"""
        json_str = json.dumps(data, indent=indent, default=str)
        self.write(json_str)

def print_header(logger: TestLogger, title: str):
    """Print a formatted header"""
    logger.write("\n" + "="*80)
    logger.write(f"  {title}")
    logger.write("="*80)

def print_detailed_result(logger: TestLogger, name: str, result: Dict[str, Any]):
    """Print detailed test result for review"""
    logger.write(f"\n### {name}")
    logger.write(f"Timestamp: {datetime.now().isoformat()}")
    logger.write(f"Confidence Score: {result.get('confidence', 0):.3f}")
    logger.write(f"Data Sources Used: {result.get('provenance', [])}")
    
    # Items found
    items = result.get('items', [])
    logger.write(f"\n📋 Found {len(items)} items:")
    
    for i, item in enumerate(items, 1):
        logger.write(f"\n  Item #{i}:")
        logger.write(f"    Code: {item.get('code', 'N/A')}")
        logger.write(f"    Description: {item.get('description', 'N/A')}")
        logger.write(f"    Fee: ${item.get('fee', 0):.2f}")
        logger.write(f"    Page: {item.get('page_num', 'N/A')}")
        
        if item.get('requirements'):
            logger.write(f"    Requirements: {item.get('requirements')}")
        if item.get('limits'):
            logger.write(f"    Limits: {item.get('limits')}")
        if item.get('documentation'):
            logger.write(f"    Documentation: {item.get('documentation')}")
    
    # Citations
    citations = result.get('citations', [])
    if citations:
        logger.write(f"\n📚 Citations ({len(citations)} sources):")
        for cite in citations:
            logger.write(f"  - Source: {cite.get('source', 'unknown')}")
            logger.write(f"    Location: {cite.get('loc', 'N/A')}")
            logger.write(f"    Page: {cite.get('page', 'N/A')}")
    
    # Conflicts
    conflicts = result.get('conflicts', [])
    if conflicts:
        logger.write(f"\n⚠️  Conflicts Detected ({len(conflicts)}):")
        for conflict in conflicts:
            logger.write(f"  - Field: {conflict.get('field')}")
            logger.write(f"    SQL Value: {conflict.get('sql_value')}")
            logger.write(f"    Vector Value: {conflict.get('vector_value')}")
            logger.write(f"    Resolution: {conflict.get('resolution', 'N/A')}")
    
    # Raw JSON for debugging
    logger.write("\n🔍 Raw Response JSON:")
    logger.write_json(result)

def evaluate_result(logger: TestLogger, name: str, result: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate test result against expectations with detailed reporting"""
    evaluation = {
        "test": name,
        "timestamp": datetime.now().isoformat(),
        "passed": True,
        "issues": [],
        "metrics": {
            "confidence": result.get('confidence', 0),
            "items_found": len(result.get('items', [])),
            "citations_count": len(result.get('citations', [])),
            "conflicts_count": len(result.get('conflicts', [])),
            "has_dual_path": 'sql' in result.get('provenance', []) and 'vector' in result.get('provenance', [])
        }
    }
    
    logger.write("\n📊 Evaluation Results:")
    
    # Check confidence score
    confidence = result.get('confidence', 0)
    logger.write(f"  Confidence: {confidence:.3f} (threshold: 0.7)")
    if confidence < 0.7:
        evaluation["issues"].append(f"Low confidence: {confidence:.3f}")
        evaluation["passed"] = False
    
    # Check dual-path retrieval
    provenance = result.get('provenance', [])
    logger.write(f"  Dual-path retrieval: SQL={'sql' in provenance} Vector={'vector' in provenance}")
    if 'sql' not in provenance or 'vector' not in provenance:
        evaluation["issues"].append(f"Missing dual-path retrieval: {provenance}")
        evaluation["passed"] = False
    
    # Check expected codes
    items = result.get('items', [])
    found_codes = [item.get('code') for item in items]
    logger.write(f"  Expected codes: {expected.get('codes', [])}")
    logger.write(f"  Found codes: {found_codes}")
    
    for expected_code in expected.get('codes', []):
        if expected_code not in found_codes:
            evaluation["issues"].append(f"Expected code {expected_code} not found")
            evaluation["passed"] = False
    
    # Check data quality
    logger.write("  Data Quality Checks:")
    for i, item in enumerate(items[:3], 1):
        issues = []
        if not item.get('fee'):
            issues.append("missing fee")
        if not item.get('description'):
            issues.append("missing description")
        if not item.get('code'):
            issues.append("missing code")
        
        if issues:
            logger.write(f"    Item {i}: {', '.join(issues)}")
            evaluation["issues"].extend([f"Item {i}: {issue}" for issue in issues])
    
    # Check citations
    if not result.get('citations'):
        evaluation["issues"].append("No citations provided")
        evaluation["passed"] = False
        logger.write("  ❌ No citations provided")
    else:
        logger.write(f"  ✅ {len(result.get('citations', []))} citations provided")
    
    return evaluation

async def test_mrp_discharge(logger: TestLogger):
    """Test 1.1: MRP Discharge Billing"""
    print_header(logger, "Test 1.1: MRP Discharge Billing (C124)")
    
    logger.write("\n📝 Test Description:")
    logger.write("  Scenario: MRP billing on day of discharge after 72+ hour admission")
    logger.write("  Expected: Should find C124 fee code with requirements and documentation")
    logger.write("  Codes to check: C124, C122, C123")
    
    try:
        logger.write("\n🚀 Executing query...")
        start = datetime.now()
        result = await schedule_get({
            "q": "MRP billing day of discharge after 72hr admission",
            "codes": ["C124", "C122", "C123"],
            "include": ["codes", "fee", "limits", "documentation"],
            "top_k": 5
        })
        duration = (datetime.now() - start).total_seconds()
        
        logger.write(f"⏱️  Response time: {duration:.3f} seconds")
        
        print_detailed_result(logger, "MRP Discharge Billing", result)
        
        # Evaluate
        expected = {
            "codes": ["C124"],
            "min_confidence": 0.7
        }
        evaluation = evaluate_result(logger, "MRP Discharge", result, expected)
        
        if evaluation["passed"]:
            logger.write("\n✅ TEST PASSED")
        else:
            logger.write("\n❌ TEST FAILED")
            logger.write("Issues found:")
            for issue in evaluation["issues"]:
                logger.write(f"  - {issue}")
        
        return evaluation
        
    except Exception as e:
        logger.write(f"\n❌ TEST FAILED WITH ERROR: {str(e)}")
        import traceback
        logger.write(f"Traceback:\n{traceback.format_exc()}")
        return {"test": "MRP Discharge", "passed": False, "issues": [str(e)]}

async def test_emergency_consultation(logger: TestLogger):
    """Test 1.2: Emergency Department Consultation"""
    print_header(logger, "Test 1.2: Emergency Department Consultation")
    
    logger.write("\n📝 Test Description:")
    logger.write("  Scenario: Internist consultation in emergency department")
    logger.write("  Expected: Should find consultation codes with specialty restrictions")
    logger.write("  Codes to check: A135, A935")
    
    try:
        logger.write("\n🚀 Executing query...")
        start = datetime.now()
        result = await schedule_get({
            "q": "internist consultation in emergency department",
            "codes": ["A135", "A935"],
            "include": ["codes", "fee", "limits", "documentation"],
            "top_k": 5
        })
        duration = (datetime.now() - start).total_seconds()
        
        logger.write(f"⏱️  Response time: {duration:.3f} seconds")
        
        print_detailed_result(logger, "Emergency Consultation", result)
        
        expected = {
            "codes": ["A135"],  # At least one should be found
            "min_confidence": 0.7
        }
        evaluation = evaluate_result(logger, "Emergency Consultation", result, expected)
        
        if evaluation["passed"]:
            logger.write("\n✅ TEST PASSED")
        else:
            logger.write("\n❌ TEST FAILED")
            logger.write("Issues found:")
            for issue in evaluation["issues"]:
                logger.write(f"  - {issue}")
        
        return evaluation
        
    except Exception as e:
        logger.write(f"\n❌ TEST FAILED WITH ERROR: {str(e)}")
        import traceback
        logger.write(f"Traceback:\n{traceback.format_exc()}")
        return {"test": "Emergency Consultation", "passed": False, "issues": [str(e)]}

async def test_house_call_premiums(logger: TestLogger):
    """Test 1.3: House Call with Premiums"""
    print_header(logger, "Test 1.3: House Call with Premiums")
    
    logger.write("\n📝 Test Description:")
    logger.write("  Scenario: House call assessment for elderly patient with time premiums")
    logger.write("  Expected: Should find house call codes with premium information")
    logger.write("  Codes to check: B998, B992, B994")
    
    try:
        logger.write("\n🚀 Executing query...")
        start = datetime.now()
        result = await schedule_get({
            "q": "house call assessment elderly patient with premium",
            "codes": ["B998", "B992", "B994"],
            "include": ["codes", "fee", "limits", "documentation"],
            "top_k": 5
        })
        duration = (datetime.now() - start).total_seconds()
        
        logger.write(f"⏱️  Response time: {duration:.3f} seconds")
        
        print_detailed_result(logger, "House Call Premiums", result)
        
        expected = {
            "codes": [],  # May not find specific codes but should have results
            "min_confidence": 0.6
        }
        evaluation = evaluate_result(logger, "House Call Premiums", result, expected)
        
        if evaluation["passed"]:
            logger.write("\n✅ TEST PASSED")
        else:
            logger.write("\n❌ TEST FAILED")
            logger.write("Issues found:")
            for issue in evaluation["issues"]:
                logger.write(f"  - {issue}")
        
        return evaluation
        
    except Exception as e:
        logger.write(f"\n❌ TEST FAILED WITH ERROR: {str(e)}")
        import traceback
        logger.write(f"Traceback:\n{traceback.format_exc()}")
        return {"test": "House Call Premiums", "passed": False, "issues": [str(e)]}

async def main():
    """Run all schedule.get tests"""
    
    # Create output file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"tests/dr_off_agent/test_outputs/schedule_test_{timestamp}.txt"
    
    with TestLogger(output_file) as logger:
        logger.write("="*80)
        logger.write("   SCHEDULE.GET MCP TOOL TEST SUITE")
        logger.write("   Testing OHIP Schedule of Benefits Lookup")
        logger.write(f"   Output File: {output_file}")
        logger.write("="*80)
        
        # Environment check
        logger.write("\n🔧 ENVIRONMENT CHECK:")
        logger.write(f"  Python: {sys.version.split()[0]}")
        logger.write(f"  Working Dir: {os.getcwd()}")
        logger.write(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
        logger.write(f"  Output File: {output_file}")
        
        # Run tests
        results = []
        
        # Test 1: MRP Discharge
        logger.write("\n" + "-"*80)
        results.append(await test_mrp_discharge(logger))
        await asyncio.sleep(1)
        
        # Test 2: Emergency Consultation  
        logger.write("\n" + "-"*80)
        results.append(await test_emergency_consultation(logger))
        await asyncio.sleep(1)
        
        # Test 3: House Call Premiums
        logger.write("\n" + "-"*80)
        results.append(await test_house_call_premiums(logger))
        
        # Summary
        logger.write("\n" + "="*80)
        logger.write("   TEST SUMMARY")
        logger.write("="*80)
        
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        
        logger.write(f"\n📊 Overall Results: {passed}/{total} tests passed")
        logger.write(f"📁 Full output saved to: {output_file}")
        
        logger.write("\nTest Status:")
        for result in results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            logger.write(f"  {status} - {result['test']}")
            if not result["passed"] and result["issues"]:
                for issue in result["issues"][:3]:
                    logger.write(f"       - {issue}")
        
        # Performance summary
        logger.write("\n⏱️  Performance Metrics:")
        for result in results:
            if 'metrics' in result:
                metrics = result['metrics']
                logger.write(f"  {result['test']}:")
                logger.write(f"    - Confidence: {metrics.get('confidence', 0):.3f}")
                logger.write(f"    - Items: {metrics.get('items_found', 0)}")
                logger.write(f"    - Dual-path: {metrics.get('has_dual_path', False)}")
        
        logger.write(f"\n✅ Test output saved to: {output_file}")
        
        return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\n{'='*60}")
    print(f"Test {'completed successfully' if success else 'had failures'}")
    print(f"Check test_outputs folder for detailed results")
    print(f"{'='*60}")
    sys.exit(0 if success else 1)