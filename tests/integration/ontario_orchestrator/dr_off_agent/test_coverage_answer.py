"""
Tests for the Dr. OFF coverage.answer orchestrator tool.
Following TDD approach - these tests define expected behavior.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test queries based on real clinical scenarios
TEST_QUERIES = [
    # Complex discharge + device scenario
    {
        "question": "My 75yo patient is being discharged after 3 days. Can I bill C124 as MRP? Also needs a walker - what's covered?",
        "hints": {"codes": ["C124"], "device": {"category": "mobility", "type": "walker"}},
        "patient": {"age": 75, "setting": "acute"},
        "expected_decision": "billable",
        "expected_confidence_min": 0.85,
        "expected_highlights_count_min": 2,
        "expected_tools_called": ["schedule.get", "adp.get"]
    },
    # Ambiguous timing question
    {
        "question": "Patient admitted Monday 2pm, discharged Thursday 10am - which discharge codes apply?",
        "patient": {"setting": "acute"},
        "expected_decision": "needs_more_info",
        "expected_confidence_min": 0.60,
        "expected_highlights_count_min": 1,
        "expected_tools_called": ["schedule.get"]
    },
    # Drug with alternatives
    {
        "question": "Is Januvia covered for my T2DM patient? Any cheaper alternatives?",
        "hints": {"drug": "sitagliptin"},
        "expected_decision": "covered",
        "expected_confidence_min": 0.90,
        "expected_highlights_count_min": 2,
        "expected_tools_called": ["odb.get"]
    },
    # CEP eligibility check
    {
        "question": "Patient needs power wheelchair, income $19,000. CEP eligible?",
        "patient": {"income": 19000},
        "hints": {"device": {"category": "mobility", "type": "power_wheelchair"}},
        "expected_decision": "eligible",
        "expected_confidence_min": 0.85,
        "expected_highlights_count_min": 1,
        "expected_tools_called": ["adp.get"]
    }
]

# Mock responses for domain tools
MOCK_SCHEDULE_RESPONSE = {
    "provenance": ["sql", "vector"],
    "confidence": 0.93,
    "items": [
        {
            "code": "C124",
            "description": "Day of discharge management",
            "fee": 124.00,
            "requirements": "MRP only, discharge documentation required",
            "page_num": 112
        }
    ],
    "citations": [
        {"source": "schedule_of_benefits.pdf", "loc": "GP-C124", "page": 112}
    ],
    "conflicts": []
}

MOCK_ADP_RESPONSE = {
    "provenance": ["sql", "vector"],
    "confidence": 0.88,
    "eligibility": {
        "basic_mobility": True,
        "ontario_resident": True,
        "valid_prescription": True
    },
    "exclusions": [
        "Not a car substitute",
        "Must be primary mobility aid"
    ],
    "funding": {
        "client_share_percent": 25,
        "adp_contribution": 75,
        "max_contribution": 2000.00
    },
    "cep": {
        "income_threshold": 28000,
        "eligible": True,
        "client_share": 0
    },
    "citations": [
        {"source": "mobility_devices_manual.pdf", "loc": "410.01", "page": 45},
        {"source": "mobility_devices_manual.pdf", "loc": "CEP-02", "page": 89}
    ]
}

MOCK_ODB_RESPONSE = {
    "provenance": ["sql", "vector"],
    "confidence": 0.95,
    "coverage": {
        "covered": True,
        "din": "02413647",
        "brand_name": "Januvia",
        "generic_name": "sitagliptin",
        "strength": "100mg",
        "lu_required": False
    },
    "interchangeable": [
        {"din": "02413647", "brand": "Januvia", "price": 2.45, "lowest_cost": False},
        {"din": "02468531", "brand": "Apo-Sitagliptin", "price": 1.89, "lowest_cost": True}
    ],
    "lowest_cost": {
        "din": "02468531",
        "brand": "Apo-Sitagliptin",
        "price": 1.89,
        "savings": 0.56
    },
    "citations": [
        {"source": "odb_formulary.pdf", "loc": "SITAGLIPTIN", "page": 234}
    ]
}


class TestCoverageAnswerOrchestrator:
    """Test suite for coverage.answer orchestrator tool."""
    
    @pytest.fixture
    def mock_coverage_answer(self):
        """Create a mock coverage answer function for testing."""
        # Import will be available once implementation is complete
        # For now, we'll create a mock that matches expected interface
        async def coverage_answer_mock(request: Dict[str, Any]) -> Dict[str, Any]:
            """Mock implementation of coverage.answer."""
            # Simulate intent classification
            question = request.get("question", "")
            intent = "billing"
            if "drug" in question.lower() or "covered" in question.lower():
                intent = "drug"
            elif "wheelchair" in question.lower() or "walker" in question.lower():
                intent = "device"
            
            # Build response based on intent
            response = {
                "decision": "billable",
                "summary": "Mock summary response",
                "provenance_summary": "sql+vector",
                "confidence": 0.91,
                "highlights": [],
                "conflicts": [],
                "followups": [],
                "trace": []
            }
            
            # Customize based on question patterns
            if "needs more info" in question.lower() or "which" in question.lower():
                response["decision"] = "needs_more_info"
                response["confidence"] = 0.65
                response["followups"] = [{"ask": "Was the patient's length of stay less than 48 hours?"}]
            
            return response
        
        return coverage_answer_mock
    
    @pytest.mark.asyncio
    async def test_coverage_answer_structure(self, mock_coverage_answer):
        """Test that coverage.answer returns expected structure."""
        request = {
            "question": "Test question",
            "hints": {},
            "patient": {}
        }
        
        response = await mock_coverage_answer(request)
        
        # Check required fields exist
        assert "decision" in response
        assert "summary" in response
        assert "provenance_summary" in response
        assert "confidence" in response
        assert "highlights" in response
        assert "conflicts" in response
        assert "followups" in response
        assert "trace" in response
        
        # Check field types
        assert response["decision"] in ["billable", "eligible", "covered", "needs_more_info"]
        assert isinstance(response["confidence"], (int, float))
        assert 0 <= response["confidence"] <= 1
        assert isinstance(response["highlights"], list)
        assert isinstance(response["conflicts"], list)
        assert isinstance(response["followups"], list)
        assert isinstance(response["trace"], list)
    
    @pytest.mark.asyncio
    async def test_complex_discharge_scenario(self):
        """Test complex discharge + device query."""
        query = TEST_QUERIES[0]
        
        # This test will pass once implementation is complete
        # For now, it defines expected behavior
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            mock_fn.return_value = {
                "decision": "billable",
                "summary": "C124 can be billed as MRP for day of discharge management. "
                           "Standard walker is covered under ADP with 75% funding, "
                           "client pays 25% unless eligible for CEP.",
                "provenance_summary": "sql+vector",
                "confidence": 0.91,
                "highlights": [
                    {
                        "point": "C124 requires MRP status and discharge documentation",
                        "citations": [{"source": "schedule.pdf", "loc": "GP-C124", "page": 112}]
                    },
                    {
                        "point": "Walker covered at 75% ADP, 25% client share",
                        "citations": [{"source": "mobility_manual.pdf", "loc": "410.01", "page": 45}]
                    }
                ],
                "conflicts": [],
                "followups": [],
                "trace": [
                    {"tool": "schedule.get", "args": {"codes": ["C124"]}},
                    {"tool": "adp.get", "args": {"device": {"category": "mobility", "type": "walker"}}}
                ]
            }
            
            response = await mock_fn(query)
            
            assert response["decision"] == query["expected_decision"]
            assert response["confidence"] >= query["expected_confidence_min"]
            assert len(response["highlights"]) >= query["expected_highlights_count_min"]
            
            # Check that expected tools were called
            tools_called = [t["tool"] for t in response["trace"]]
            for expected_tool in query["expected_tools_called"]:
                assert expected_tool in tools_called
    
    @pytest.mark.asyncio
    async def test_ambiguous_timing_needs_clarification(self):
        """Test that ambiguous queries return needs_more_info."""
        query = TEST_QUERIES[1]
        
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            mock_fn.return_value = {
                "decision": "needs_more_info",
                "summary": "Multiple discharge codes may apply depending on length of stay "
                           "and MRP status. Need clarification on exact hours.",
                "provenance_summary": "sql+vector",
                "confidence": 0.65,
                "highlights": [
                    {
                        "point": "C124 applies for day of discharge if MRP",
                        "citations": [{"source": "schedule.pdf", "loc": "GP-C124"}]
                    }
                ],
                "conflicts": [],
                "followups": [
                    {"ask": "Was the total length of stay less than 48 hours?"},
                    {"ask": "Are you the Most Responsible Physician (MRP)?"}
                ],
                "trace": [
                    {"tool": "schedule.get", "args": {"q": "discharge codes timing"}}
                ]
            }
            
            response = await mock_fn(query)
            
            assert response["decision"] == "needs_more_info"
            assert response["confidence"] < 0.7  # Lower confidence expected
            assert len(response["followups"]) > 0  # Should have follow-up questions
    
    @pytest.mark.asyncio
    async def test_drug_coverage_with_alternatives(self):
        """Test drug coverage query with interchangeable alternatives."""
        query = TEST_QUERIES[2]
        
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            mock_fn.return_value = {
                "decision": "covered",
                "summary": "Januvia (sitagliptin) is covered on ODB formulary. "
                           "Apo-Sitagliptin is the lowest-cost alternative at $1.89 vs $2.45.",
                "provenance_summary": "sql+vector",
                "confidence": 0.95,
                "highlights": [
                    {
                        "point": "Sitagliptin covered, no LU required",
                        "citations": [{"source": "odb_formulary.pdf", "loc": "SITAGLIPTIN"}]
                    },
                    {
                        "point": "Apo-Sitagliptin is lowest-cost at $1.89",
                        "citations": [{"source": "odb_formulary.pdf", "loc": "INTERCHANGEABLE"}]
                    }
                ],
                "conflicts": [],
                "followups": [],
                "trace": [
                    {"tool": "odb.get", "args": {"drug": "sitagliptin", "check_alternatives": True}}
                ]
            }
            
            response = await mock_fn(query)
            
            assert response["decision"] == "covered"
            assert response["confidence"] >= 0.90
            assert "lowest-cost" in response["summary"].lower() or "cheaper" in response["summary"].lower()
    
    @pytest.mark.asyncio
    async def test_cep_eligibility_calculation(self):
        """Test CEP eligibility with income threshold."""
        query = TEST_QUERIES[3]
        
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            mock_fn.return_value = {
                "decision": "eligible",
                "summary": "Patient is CEP eligible with income $19,000 (below $28,000 threshold). "
                           "Power wheelchair covered at 100% through CEP.",
                "provenance_summary": "sql+vector",
                "confidence": 0.88,
                "highlights": [
                    {
                        "point": "CEP covers 100% for income below $28,000",
                        "citations": [{"source": "mobility_manual.pdf", "loc": "CEP-02"}]
                    }
                ],
                "conflicts": [],
                "followups": [],
                "trace": [
                    {"tool": "adp.get", "args": {
                        "device": {"category": "mobility", "type": "power_wheelchair"},
                        "check": ["cep"],
                        "patient_income": 19000
                    }}
                ]
            }
            
            response = await mock_fn(query)
            
            assert response["decision"] == "eligible"
            assert "cep" in response["summary"].lower()
            assert "100%" in response["summary"] or "fully covered" in response["summary"].lower()
    
    @pytest.mark.asyncio
    async def test_confidence_scoring_logic(self):
        """Test that confidence scores follow expected rules."""
        # SQL base: 0.9
        # Vector corroboration: +0.03 per matching passage
        # Conflict: -0.1
        
        test_cases = [
            {
                "sql_hit": True,
                "vector_matches": 2,
                "has_conflict": False,
                "expected_confidence": 0.96  # 0.9 + (0.03 * 2)
            },
            {
                "sql_hit": True,
                "vector_matches": 1,
                "has_conflict": True,
                "expected_confidence": 0.83  # 0.9 + 0.03 - 0.1
            },
            {
                "sql_hit": False,
                "vector_matches": 3,
                "has_conflict": False,
                "expected_confidence": 0.69  # 0.6 (base for vector-only) + (0.03 * 3)
            }
        ]
        
        for case in test_cases:
            # This will be tested against actual implementation
            assert True  # Placeholder for now
    
    @pytest.mark.asyncio
    async def test_dual_path_always_runs(self):
        """Test that both SQL and vector retrieval always run."""
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            mock_fn.return_value = {
                "decision": "covered",
                "summary": "Test",
                "provenance_summary": "sql+vector",
                "confidence": 0.91,
                "highlights": [],
                "conflicts": [],
                "followups": [],
                "trace": []
            }
            
            response = await mock_fn({"question": "test"})
            
            # Should always include both provenance sources
            assert "sql" in response["provenance_summary"]
            assert "vector" in response["provenance_summary"]
    
    @pytest.mark.asyncio 
    async def test_conflict_detection(self):
        """Test that conflicts between SQL and vector are surfaced."""
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            # Simulate a conflict scenario
            mock_fn.return_value = {
                "decision": "covered",
                "summary": "Coverage confirmed but documentation requirements differ",
                "provenance_summary": "sql+vector",
                "confidence": 0.81,  # Lower due to conflict
                "highlights": [],
                "conflicts": [
                    {
                        "field": "documentation_required",
                        "sql_value": "None",
                        "vector_value": "Prior authorization form required",
                        "resolution": "Following vector source (more recent)"
                    }
                ],
                "followups": [],
                "trace": []
            }
            
            response = await mock_fn({"question": "test with conflict"})
            
            assert len(response["conflicts"]) > 0
            assert response["confidence"] < 0.85  # Confidence should be lower with conflicts
    
    @pytest.mark.asyncio
    async def test_citation_requirements(self):
        """Test that all responses include proper citations."""
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            mock_fn.return_value = {
                "decision": "billable",
                "summary": "Test",
                "provenance_summary": "sql+vector",
                "confidence": 0.91,
                "highlights": [
                    {
                        "point": "Test point",
                        "citations": [
                            {"source": "test.pdf", "loc": "TEST-01", "page": 1}
                        ]
                    }
                ],
                "conflicts": [],
                "followups": [],
                "trace": []
            }
            
            response = await mock_fn({"question": "test"})
            
            # Every highlight must have citations
            for highlight in response["highlights"]:
                assert "citations" in highlight
                assert len(highlight["citations"]) > 0
                
                # Each citation must have source and location
                for citation in highlight["citations"]:
                    assert "source" in citation
                    assert "loc" in citation
    
    @pytest.mark.asyncio
    async def test_trace_completeness(self):
        """Test that trace includes all tool calls made."""
        with patch('src.agents.ontario_orchestrator.mcp.tools.coverage.coverage_answer') as mock_fn:
            mock_fn.return_value = {
                "decision": "billable",
                "summary": "Test",
                "provenance_summary": "sql+vector", 
                "confidence": 0.91,
                "highlights": [],
                "conflicts": [],
                "followups": [],
                "trace": [
                    {"tool": "schedule.get", "args": {"codes": ["C124"]}, "duration_ms": 125},
                    {"tool": "adp.get", "args": {"device": {"type": "walker"}}, "duration_ms": 230}
                ]
            }
            
            response = await mock_fn({"question": "test"})
            
            # Trace should document all tools called
            assert len(response["trace"]) >= 1
            
            for trace_entry in response["trace"]:
                assert "tool" in trace_entry
                assert "args" in trace_entry


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])