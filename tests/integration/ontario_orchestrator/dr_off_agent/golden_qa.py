"""
Golden QA Test Suite for Dr. OFF - Real Clinical Scenarios
These are the MUST-PASS tests that validate Dr. OFF serves clinicians effectively.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Import the coverage.answer orchestrator (main entry point)
from src.agents.ontario_orchestrator.mcp.tools.coverage import CoverageAnswerTool
from src.agents.ontario_orchestrator.mcp.models.request import CoverageRequest


@dataclass
class GoldenTestCase:
    """Structure for a golden test case."""
    name: str
    query: str
    expected: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    category: str = "general"
    priority: str = "high"  # high, medium, low
    

class TestDrOFFGoldenScenarios:
    """
    Golden test cases representing real questions Ontario clinicians ask daily.
    These MUST all pass for Dr. OFF to be considered functional.
    """
    
    @pytest.fixture
    def coverage_tool(self):
        """Create the main coverage.answer tool."""
        return CoverageAnswerTool()
    
    @pytest.fixture
    def golden_cases(self) -> List[GoldenTestCase]:
        """Define all golden test cases."""
        return [
            # === COMPLEX DISCHARGE SCENARIOS ===
            GoldenTestCase(
                name="Complex Discharge with Multiple Needs",
                query="72yo CHF patient admitted Mon 3pm, discharged Thu 11am. I'm MRP. Can I bill C124? Needs walker and furosemide refill.",
                expected={
                    "decision": "billable",
                    "highlights_contain": [
                        "C124 eligible - 72hr admission as MRP",
                        "Walker 75% ADP funded",
                        "Furosemide covered - generic available"
                    ],
                    "confidence": ">0.9",
                    "citations_required": True
                },
                category="discharge",
                priority="high"
            ),
            
            GoldenTestCase(
                name="Short Stay Discharge Billing",
                query="Patient admitted Tuesday 9pm, discharged Wednesday 4pm. Can I bill discharge code?",
                expected={
                    "decision": "not_billable",
                    "highlights_contain": [
                        "Less than 48 hours",
                        "C122 or C123 may apply instead"
                    ],
                    "confidence": ">0.85"
                },
                category="discharge",
                priority="high"
            ),
            
            # === POWER MOBILITY & CEP ===
            GoldenTestCase(
                name="Power Mobility CEP Eligibility",
                query="MS patient EDSS 7.0, needs power wheelchair. Income $19,000/year single. What's covered?",
                expected={
                    "decision": "eligible",
                    "highlights_contain": [
                        "CEP eligible - income below threshold",
                        "100% funding available",
                        "Authorization form required"
                    ],
                    "cep_details": {
                        "threshold_single": 28000,
                        "patient_qualifies": True
                    },
                    "confidence": ">0.9"
                },
                category="adp_mobility",
                priority="high"
            ),
            
            GoldenTestCase(
                name="Scooter Repair Exclusions",
                query="3-year-old scooter needs batteries and motor repair. What does ADP cover?",
                expected={
                    "decision": "conditional",
                    "highlights_contain": [
                        "Batteries NOT covered",
                        "Repairs NOT funded",
                        "May qualify for replacement after 5 years"
                    ],
                    "exclusions_found": ["batteries", "repairs"],
                    "citations_present": True,
                    "confidence": ">0.85"
                },
                category="adp_mobility",
                priority="high"
            ),
            
            GoldenTestCase(
                name="Walker vs Rollator Coverage",
                query="85yo needs mobility aid, can walk 50m. Walker or rollator - what's covered?",
                expected={
                    "decision": "eligible",
                    "highlights_contain": [
                        "Both walker and rollator eligible",
                        "75% ADP funding",
                        "25% client contribution"
                    ],
                    "funding_percentage": 75,
                    "confidence": ">0.85"
                },
                category="adp_mobility",
                priority="medium"
            ),
            
            # === DRUG COVERAGE SCENARIOS ===
            GoldenTestCase(
                name="Statin Optimization",
                query="Patient can't afford Lipitor. Cheapest equivalent statin?",
                expected={
                    "highlights_contain": [
                        "Generic atorvastatin",
                        "Price comparison",
                        "Interchangeable"
                    ],
                    "drug_alternatives_present": True,
                    "price_info_included": True,
                    "confidence": ">0.85"
                },
                category="odb",
                priority="high"
            ),
            
            GoldenTestCase(
                name="Diabetes Drug with LU Requirements",
                query="Can I prescribe Jardiance for T2DM? What are the LU requirements?",
                expected={
                    "decision": "covered_with_lu",
                    "highlights_contain": [
                        "Limited Use code required",
                        "Must try metformin first",
                        "Documentation needed"
                    ],
                    "lu_code_present": True,
                    "confidence": ">0.85"
                },
                category="odb",
                priority="high"
            ),
            
            GoldenTestCase(
                name="Generic Substitution",
                query="Is there a generic for Januvia that's covered?",
                expected={
                    "highlights_contain": [
                        "Generic sitagliptin available",
                        "Interchangeable",
                        "Cost savings"
                    ],
                    "interchangeable_found": True,
                    "confidence": ">0.8"
                },
                category="odb",
                priority="medium"
            ),
            
            # === OHIP BILLING SCENARIOS ===
            GoldenTestCase(
                name="Virtual Care Billing",
                query="Can I bill virtual follow-up for COPD patient seen last week?",
                expected={
                    "highlights_contain": [
                        "Virtual care codes",
                        "Time requirements"
                    ],
                    "billing_codes_present": True,
                    "confidence": ">0.75"
                },
                category="ohip",
                priority="medium"
            ),
            
            GoldenTestCase(
                name="ER Consultation as Internist",
                query="Called to ER for consult as internist. Which code?",
                expected={
                    "decision": "billable",
                    "highlights_contain": [
                        "A135",  # or appropriate consultation code
                        "Emergency consultation"
                    ],
                    "fee_code_present": True,
                    "confidence": ">0.85"
                },
                category="ohip",
                priority="high"
            ),
            
            GoldenTestCase(
                name="House Call Premium",
                query="House call for 89yo homebound patient. What premiums apply?",
                expected={
                    "highlights_contain": [
                        "House call premium",
                        "Additional fees",
                        "Documentation requirements"
                    ],
                    "premium_codes_present": True,
                    "confidence": ">0.8"
                },
                category="ohip",
                priority="medium"
            ),
            
            # === COMMUNICATION AIDS ===
            GoldenTestCase(
                name="AAC Device for ALS",
                query="ALS patient losing speech. AAC device funding?",
                expected={
                    "decision": "eligible",
                    "highlights_contain": [
                        "Communication aid eligible",
                        "75% ADP funding",
                        "SLP assessment required"
                    ],
                    "requires_assessment": True,
                    "confidence": ">0.85"
                },
                category="adp_comm",
                priority="high"
            ),
            
            GoldenTestCase(
                name="SGD Fast Track Eligibility",
                query="Progressive MS, rapid speech decline. Qualifies for SGD fast-track?",
                expected={
                    "decision": "eligible",
                    "highlights_contain": [
                        "Fast-track criteria",
                        "Progressive condition",
                        "Expedited processing"
                    ],
                    "confidence": ">0.8"
                },
                category="adp_comm",
                priority="medium"
            ),
            
            # === EDGE CASES & CONFLICTS ===
            GoldenTestCase(
                name="Conflicting Coverage Information",
                query="Is pregabalin covered for neuropathic pain?",
                expected={
                    "highlights_contain": [
                        "Limited coverage",
                        "Specific criteria"
                    ],
                    "conflicts_if_any": "handled_appropriately",
                    "confidence": ">0.7"  # Lower due to complexity
                },
                category="odb",
                priority="medium"
            ),
            
            GoldenTestCase(
                name="Multiple Funding Sources",
                query="Patient has private insurance and ODB. How does ADP coordinate for wheelchair?",
                expected={
                    "highlights_contain": [
                        "ADP is payer of last resort",
                        "Private insurance first",
                        "Coordination of benefits"
                    ],
                    "confidence": ">0.8"
                },
                category="adp_mobility", 
                priority="low"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_all_golden_cases(self, coverage_tool, golden_cases):
        """Run all golden test cases and report results."""
        results = []
        failures = []
        
        for case in golden_cases:
            try:
                # Build request
                request = CoverageRequest(
                    question=case.query,
                    patient=case.context.get("patient") if case.context else None,
                    hints=case.context.get("hints") if case.context else None
                )
                
                # Execute query
                response = await coverage_tool.answer(request)
                
                # Validate response
                passed = self._validate_response(response, case.expected)
                
                results.append({
                    "name": case.name,
                    "category": case.category,
                    "priority": case.priority,
                    "passed": passed,
                    "confidence": response.confidence
                })
                
                if not passed:
                    failures.append(case.name)
                    
            except Exception as e:
                results.append({
                    "name": case.name,
                    "category": case.category,
                    "error": str(e),
                    "passed": False
                })
                failures.append(f"{case.name} (ERROR)")
        
        # Generate report
        self._generate_report(results, failures)
        
        # Assert no failures for CI/CD
        assert len(failures) == 0, f"Failed cases: {failures}"
    
    def _validate_response(self, response, expected) -> bool:
        """Validate response against expected outcomes."""
        passed = True
        
        # Check decision if specified
        if "decision" in expected:
            if response.decision != expected["decision"]:
                passed = False
        
        # Check highlights contain expected text
        if "highlights_contain" in expected:
            response_text = " ".join([h.point for h in response.highlights])
            for expected_text in expected["highlights_contain"]:
                if expected_text.lower() not in response_text.lower():
                    passed = False
        
        # Check confidence threshold
        if "confidence" in expected:
            threshold = float(expected["confidence"].replace(">", "").replace(">=", ""))
            if response.confidence < threshold:
                passed = False
        
        # Check citations present
        if expected.get("citations_required") or expected.get("citations_present"):
            if len(response.citations) == 0:
                passed = False
        
        # Check for specific fields
        if expected.get("drug_alternatives_present"):
            if not hasattr(response, 'alternatives') or not response.alternatives:
                passed = False
        
        if expected.get("billing_codes_present"):
            # Check if any highlights mention fee codes (pattern: letter + numbers)
            import re
            code_pattern = r'[A-Z]\d{3}'
            response_text = " ".join([h.point for h in response.highlights])
            if not re.search(code_pattern, response_text):
                passed = False
        
        return passed
    
    def _generate_report(self, results: List[Dict], failures: List[str]):
        """Generate test report for analysis."""
        total = len(results)
        passed = sum(1 for r in results if r.get("passed", False))
        
        print("\n" + "="*60)
        print("DR. OFF GOLDEN QA TEST REPORT")
        print("="*60)
        
        # Summary
        print(f"\nSUMMARY:")
        print(f"  Total Tests: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {total - passed}")
        print(f"  Success Rate: {(passed/total)*100:.1f}%")
        
        # By category
        print(f"\nBY CATEGORY:")
        categories = {}
        for r in results:
            cat = r.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {"passed": 0, "total": 0}
            categories[cat]["total"] += 1
            if r.get("passed", False):
                categories[cat]["passed"] += 1
        
        for cat, stats in categories.items():
            rate = (stats["passed"]/stats["total"])*100
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")
        
        # Failures detail
        if failures:
            print(f"\nFAILED TESTS:")
            for f in failures:
                print(f"  ❌ {f}")
        
        # Confidence distribution
        confidences = [r.get("confidence", 0) for r in results if "confidence" in r]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            print(f"\nCONFIDENCE METRICS:")
            print(f"  Average: {avg_confidence:.3f}")
            print(f"  Min: {min(confidences):.3f}")
            print(f"  Max: {max(confidences):.3f}")
        
        print("\n" + "="*60)


class TestGoldenQAByCategory:
    """Test individual categories for targeted debugging."""
    
    @pytest.fixture
    def coverage_tool(self):
        return CoverageAnswerTool()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("category", ["discharge", "adp_mobility", "odb", "ohip"])
    async def test_category(self, coverage_tool, category):
        """Test a specific category of golden cases."""
        # This allows running: pytest -k "test_category[discharge]"
        test_suite = TestDrOFFGoldenScenarios()
        cases = test_suite.golden_cases()
        
        category_cases = [c for c in cases if c.category == category]
        assert len(category_cases) > 0, f"No test cases for category: {category}"
        
        for case in category_cases:
            request = CoverageRequest(
                question=case.query,
                patient=case.context.get("patient") if case.context else None
            )
            
            response = await coverage_tool.answer(request)
            
            # Basic assertion - should get a response
            assert response is not None
            assert response.decision in ["billable", "eligible", "covered", 
                                        "not_billable", "not_eligible", 
                                        "not_covered", "conditional", 
                                        "needs_more_info"]
            assert response.confidence > 0
            assert len(response.highlights) > 0


class TestGoldenQAPerformance:
    """Test performance requirements for golden cases."""
    
    @pytest.fixture
    def coverage_tool(self):
        return CoverageAnswerTool()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_p95_latency_under_1500ms(self, coverage_tool):
        """P95 latency should be under 1.5 seconds."""
        import time
        
        queries = [
            "Can I bill C124 for 3-day admission?",
            "Is metformin covered?",
            "Power wheelchair funding for low income?",
            "Generic alternatives to Lipitor?",
            "Virtual care billing codes?"
        ]
        
        latencies = []
        for query in queries * 3:  # Run each 3 times
            start = time.time()
            request = CoverageRequest(question=query)
            await coverage_tool.answer(request)
            latencies.append((time.time() - start) * 1000)
        
        # Calculate P95
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]
        
        assert p95_latency < 1500, f"P95 latency {p95_latency}ms exceeds 1500ms"
    
    @pytest.mark.asyncio 
    @pytest.mark.performance
    async def test_dual_path_always_runs(self, coverage_tool):
        """Verify SQL and vector always run in parallel."""
        request = CoverageRequest(
            question="Metformin coverage and alternatives"
        )
        
        response = await coverage_tool.answer(request)
        
        # Check provenance shows both paths
        assert "sql" in response.provenance_summary
        assert "vector" in response.provenance_summary
        
        # Should have citations even with SQL hit
        assert len(response.citations) > 0


if __name__ == "__main__":
    # Allow running as script for quick testing
    import sys
    pytest.main([__file__, "-v", "--tb=short"] + sys.argv[1:])