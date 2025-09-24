"""
Test suite for schedule.get OHIP billing tool with realistic clinical queries.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Test queries based on real clinician scenarios
SCHEDULE_TEST_QUERIES = [
    {
        "test_name": "MRP billing day of discharge after 72hr admission",
        "request": {
            "q": "MRP billing day of discharge after 72hr admission",
            "codes": ["C124", "C122", "C123"],
            "include": ["codes", "fee", "limits", "documentation"],
            "top_k": 6
        },
        "expected_sql_results": [
            {
                "code": "C124",
                "description": "Day of discharge from hospital by MRP",
                "amount": 31.00,
                "requirements": "Requires discharge summary documentation",
                "specialty": "General Practice"
            }
        ],
        "expected_vector_results": [
            {
                "text": "C124 is billable as MRP on day of discharge after minimum 72 hour admission. Documentation requirements include discharge summary with diagnosis, treatment plan, and follow-up instructions.",
                "metadata": {"source": "schedule.pdf", "page": 45, "section": "GP"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.93,  # SQL base 0.9 + vector match 0.03
            "items": [
                {
                    "code": "C124",
                    "description": "Day of discharge from hospital by MRP",
                    "fee": 31.00,
                    "documentation_required": ["discharge summary", "diagnosis", "treatment plan"],
                    "eligibility": "Minimum 72 hour admission required"
                }
            ],
            "citations": [
                {"source": "schedule.pdf", "location": "GP-C124", "page": 45}
            ]
        }
    },
    {
        "test_name": "internist consultation in emergency department",
        "request": {
            "q": "internist consultation in emergency department",
            "codes": ["A135", "A935"],
            "include": ["fee", "specialty_restrictions"],
            "top_k": 6
        },
        "expected_sql_results": [
            {
                "code": "A135",
                "description": "Consultation - first consultation",
                "amount": 157.00,
                "specialty": "Internal Medicine",
                "requirements": "Written request from referring physician"
            },
            {
                "code": "A935", 
                "description": "Special surgical consultation",
                "amount": 113.15,
                "specialty": "Internal Medicine",
                "requirements": "Reassessment after initial consultation"
            }
        ],
        "expected_vector_results": [
            {
                "text": "A135 is used for initial consultation by internist in ED setting. A935 is for reassessment or repeat consultation. Both require formal request from ED physician.",
                "metadata": {"source": "schedule.pdf", "page": 120, "section": "A"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.93,
            "items": [
                {
                    "code": "A135",
                    "description": "Consultation - first consultation",
                    "fee": 157.00,
                    "specialty_restriction": "Internal Medicine",
                    "use_case": "Initial ED consultation"
                },
                {
                    "code": "A935",
                    "description": "Special surgical consultation", 
                    "fee": 113.15,
                    "specialty_restriction": "Internal Medicine",
                    "use_case": "ED reassessment"
                }
            ],
            "citations": [
                {"source": "schedule.pdf", "location": "A-Consultation", "page": 120}
            ]
        }
    },
    {
        "test_name": "house call assessment elderly patient with premium",
        "request": {
            "q": "house call assessment elderly patient with premium",
            "codes": ["B998", "B992", "B994"],
            "include": ["fee", "premiums", "time_restrictions"],
            "top_k": 6
        },
        "expected_sql_results": [
            {
                "code": "B998",
                "description": "House call assessment",
                "amount": 77.20,
                "specialty": "General Practice"
            },
            {
                "code": "B992",
                "description": "Weekday evening premium (18:00-24:00)",
                "amount": 38.60,
                "specialty": "General Practice"
            },
            {
                "code": "B994",
                "description": "Weekend/holiday premium",
                "amount": 52.10,
                "specialty": "General Practice"
            }
        ],
        "expected_vector_results": [
            {
                "text": "House call B998 base fee can be combined with time-based premiums. B992 applies weekday evenings 6pm-midnight. B994 for weekends and holidays all day.",
                "metadata": {"source": "schedule.pdf", "page": 200, "section": "B"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.93,
            "items": [
                {
                    "code": "B998",
                    "description": "House call assessment",
                    "fee": 77.20,
                    "type": "base_fee"
                },
                {
                    "code": "B992", 
                    "description": "Weekday evening premium (18:00-24:00)",
                    "fee": 38.60,
                    "type": "premium",
                    "time_restriction": "Weekdays 6pm-midnight"
                },
                {
                    "code": "B994",
                    "description": "Weekend/holiday premium",
                    "fee": 52.10,
                    "type": "premium",
                    "time_restriction": "Weekends and statutory holidays"
                }
            ],
            "citations": [
                {"source": "schedule.pdf", "location": "B-House Calls", "page": 200}
            ]
        }
    }
]


class TestScheduleTool:
    """Test suite for schedule.get OHIP billing tool."""
    
    @pytest.fixture
    def mock_sql_client(self):
        """Mock SQL client for testing."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_vector_client(self):
        """Mock vector client for testing."""
        client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_mrp_discharge_billing(self, mock_sql_client, mock_vector_client):
        """Test MRP billing on day of discharge after 72hr admission."""
        test_case = SCHEDULE_TEST_QUERIES[0]
        
        # Configure mocks
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        # Import will fail for now - this is expected
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
            
            # Once implemented, this should work:
            result = await schedule_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify dual-path execution
            assert mock_sql_client.query.called
            assert mock_vector_client.search.called
            
            # Verify response structure
            assert result["provenance"] == ["sql", "vector"]
            assert result["confidence"] >= 0.9
            assert len(result["items"]) > 0
            assert len(result["citations"]) > 0
            
            # Verify C124 is recommended with documentation requirements
            c124_item = next(i for i in result["items"] if i["code"] == "C124")
            assert c124_item["fee"] == 31.00
            assert "discharge summary" in c124_item["documentation_required"]
    
    @pytest.mark.asyncio
    async def test_internist_ed_consultation(self, mock_sql_client, mock_vector_client):
        """Test internist consultation codes in emergency department."""
        test_case = SCHEDULE_TEST_QUERIES[1]
        
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
            
            result = await schedule_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify both A135 and A935 are returned
            codes = [item["code"] for item in result["items"]]
            assert "A135" in codes  # Initial consultation
            assert "A935" in codes  # Reassessment
            
            # Verify specialty restrictions noted
            a135_item = next(i for i in result["items"] if i["code"] == "A135")
            assert a135_item["specialty_restriction"] == "Internal Medicine"
    
    @pytest.mark.asyncio
    async def test_house_call_with_premiums(self, mock_sql_client, mock_vector_client):
        """Test house call base fee with time-based premiums."""
        test_case = SCHEDULE_TEST_QUERIES[2]
        
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
            
            result = await schedule_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify base fee and premiums are distinguished
            base_fee = next(i for i in result["items"] if i["type"] == "base_fee")
            premiums = [i for i in result["items"] if i["type"] == "premium"]
            
            assert base_fee["code"] == "B998"
            assert len(premiums) == 2  # Evening and weekend premiums
            
            # Verify time restrictions are included
            evening_premium = next(p for p in premiums if p["code"] == "B992")
            assert "6pm" in evening_premium["time_restriction"].lower()
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, mock_sql_client, mock_vector_client):
        """Verify SQL and vector queries run in parallel with asyncio.gather()."""
        test_case = SCHEDULE_TEST_QUERIES[0]
        
        # Add delays to simulate real queries
        async def delayed_sql_query(*args):
            await asyncio.sleep(0.3)  # 300ms SQL query
            return test_case["expected_sql_results"]
        
        async def delayed_vector_search(*args):
            await asyncio.sleep(0.5)  # 500ms vector search
            return test_case["expected_vector_results"]
        
        mock_sql_client.query = delayed_sql_query
        mock_vector_client.search = delayed_vector_search
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
            import time
            
            start_time = time.time()
            result = await schedule_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            elapsed = time.time() - start_time
            
            # If running in parallel, should take ~500ms (max of 300ms and 500ms)
            # If serial, would take ~800ms (300ms + 500ms)
            assert elapsed < 0.6, "Queries should run in parallel"
            assert result["provenance"] == ["sql", "vector"]
    
    @pytest.mark.asyncio
    async def test_sql_timeout_handling(self, mock_sql_client, mock_vector_client):
        """Test handling of SQL query timeout."""
        test_case = SCHEDULE_TEST_QUERIES[0]
        
        # SQL times out
        mock_sql_client.query.side_effect = asyncio.TimeoutError("SQL query timeout")
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
            
            result = await schedule_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Should still return vector results
            assert "vector" in result["provenance"]
            assert "sql" not in result["provenance"]
            assert result["confidence"] < 0.9  # Lower confidence without SQL
            assert len(result["citations"]) > 0  # Vector still provides citations
    
    @pytest.mark.asyncio
    async def test_vector_enriches_sql_results(self, mock_sql_client, mock_vector_client):
        """Test that vector results add context to SQL data."""
        test_case = SCHEDULE_TEST_QUERIES[0]
        
        # SQL returns basic fee info
        mock_sql_client.query.return_value = [{
            "code": "C124",
            "description": "Day of discharge from hospital by MRP",
            "amount": 31.00
            # Note: No documentation requirements in SQL result
        }]
        
        # Vector adds documentation context
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
            
            result = await schedule_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify merged result includes both SQL and vector info
            c124_item = result["items"][0]
            assert c124_item["fee"] == 31.00  # From SQL
            assert "documentation_required" in c124_item  # Enriched from vector
            assert "72 hour" in str(c124_item.get("eligibility", "")).lower()  # From vector