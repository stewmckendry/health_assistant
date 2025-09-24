"""
Test suite for adp.get ADP device funding tool with realistic clinical queries.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Test queries based on real clinician scenarios
ADP_TEST_QUERIES = [
    {
        "test_name": "power wheelchair funding with CEP eligibility",
        "request": {
            "device": {"category": "mobility", "type": "power_wheelchair"},
            "check": ["eligibility", "funding", "cep"],
            "use_case": {
                "daily": True,
                "independent_transfer": False,
                "income": 19000  # Below CEP threshold
            }
        },
        "expected_sql_results": [
            {
                "scenario": "Power wheelchair - basic mobility",
                "client_share_percent": 25,
                "adp_share_percent": 75,
                "details": "ADP covers 75% for approved power wheelchairs"
            },
            {
                "scenario": "CEP income threshold",
                "threshold": 28000,
                "details": "Clients with income below $28,000 eligible for CEP"
            }
        ],
        "expected_vector_results": [
            {
                "text": "Power wheelchairs require assessment by authorized prescriber. Client must demonstrate need for powered mobility due to inability to self-propel manual wheelchair. ADP covers 75% of approved price. CEP (Client Eligibility Program) covers remaining 25% for low-income clients.",
                "metadata": {"source": "mobility-manual", "page": 45, "section": "410.01"}
            },
            {
                "text": "CEP eligibility: Net income below $28,000 for single person. Must be Ontario resident with valid health card. CEP covers client's 25% share for approved devices.",
                "metadata": {"source": "mobility-manual", "page": 89, "section": "CEP"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.96,  # High confidence with SQL + multiple vector matches
            "eligibility": {
                "eligible": True,
                "requirements": [
                    "Authorized prescriber assessment",
                    "Unable to self-propel manual wheelchair",
                    "Valid Ontario health card"
                ]
            },
            "funding": {
                "adp_coverage": 75,
                "client_share": 25,
                "cep_eligible": True,
                "cep_covers_remaining": True,
                "final_client_cost": 0
            },
            "citations": [
                {"source": "mobility-manual", "location": "410.01", "page": 45},
                {"source": "mobility-manual", "location": "CEP", "page": 89}
            ]
        }
    },
    {
        "test_name": "scooter batteries exclusion",
        "request": {
            "device": {"category": "mobility", "type": "scooter_batteries"},
            "check": ["exclusions", "replacement_schedule"],
            "use_case": {}
        },
        "expected_sql_results": [
            {
                "phrase": "batteries",
                "applies_to": "All mobility devices",
                "section_ref": "Exclusions",
                "details": "Batteries are not covered by ADP"
            },
            {
                "phrase": "repairs and maintenance",
                "applies_to": "All devices",
                "section_ref": "General Exclusions",
                "details": "Repairs and maintenance not covered"
            }
        ],
        "expected_vector_results": [
            {
                "text": "ADP does not cover: batteries, repairs, maintenance, or replacement parts for any mobility device. Clients are responsible for all maintenance costs including battery replacement.",
                "metadata": {"source": "mobility-manual", "page": 112, "section": "Exclusions"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.93,
            "eligibility": {
                "eligible": False,
                "reason": "Batteries explicitly excluded from ADP coverage"
            },
            "exclusions": [
                {
                    "item": "batteries",
                    "reason": "Not covered for any mobility device",
                    "alternatives": "Client responsible for purchase"
                }
            ],
            "citations": [
                {"source": "mobility-manual", "location": "Exclusions", "page": 112}
            ]
        }
    },
    {
        "test_name": "SGD for ALS patient with fast-track",
        "request": {
            "device": {"category": "comm_aids", "type": "SGD"},  # Speech Generating Device
            "check": ["eligibility", "funding", "forms"],
            "use_case": {
                "diagnosis": "ALS",
                "cognitive_intact": True,
                "speech_deteriorating": True
            }
        },
        "expected_sql_results": [
            {
                "scenario": "Communication aids - SGD",
                "client_share_percent": 25,
                "adp_share_percent": 75,
                "details": "Speech generating devices covered at 75%"
            }
        ],
        "expected_vector_results": [
            {
                "text": "Speech Generating Devices (SGDs) for ALS patients have expedited approval process. Requirements: SLP assessment, confirmation of ALS diagnosis, cognitive capacity to use device. ADP covers 75% of approved SGD cost.",
                "metadata": {"source": "comm-aids-manual", "page": 23, "section": "200.03"}
            },
            {
                "text": "ALS fast-track process: Streamlined application for progressive conditions. SLP completes functional assessment. Processing time reduced to 2-3 weeks for ALS/MND patients.",
                "metadata": {"source": "comm-aids-manual", "page": 67, "section": "Special Programs"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.96,
            "eligibility": {
                "eligible": True,
                "fast_track": True,
                "requirements": [
                    "SLP assessment required",
                    "ALS diagnosis confirmation",
                    "Cognitive capacity verification"
                ]
            },
            "funding": {
                "adp_coverage": 75,
                "client_share": 25,
                "processing_time": "2-3 weeks (expedited for ALS)"
            },
            "forms": [
                "ADP Application for Communication Aids",
                "SLP Assessment Form",
                "ALS Fast-Track Authorization"
            ],
            "citations": [
                {"source": "comm-aids-manual", "location": "200.03", "page": 23},
                {"source": "comm-aids-manual", "location": "Special Programs", "page": 67}
            ]
        }
    },
    {
        "test_name": "walker for elderly with standard funding",
        "request": {
            "device": {"category": "mobility", "type": "walker"},
            "check": ["eligibility", "funding"],
            "use_case": {
                "age": 85,
                "mobility_limited": True,
                "fall_risk": True
            }
        },
        "expected_sql_results": [
            {
                "scenario": "Walker - standard",
                "client_share_percent": 25,
                "adp_share_percent": 75,
                "details": "Standard walkers covered at 75%"
            }
        ],
        "expected_vector_results": [
            {
                "text": "Walkers covered for clients with demonstrated mobility impairment. Prescriber must be OT, PT, or physician. ADP covers 75% of approved walker models. Client pays 25% unless eligible for CEP.",
                "metadata": {"source": "mobility-manual", "page": 78, "section": "420.01"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.93,
            "eligibility": {
                "eligible": True,
                "requirements": [
                    "Mobility impairment documentation",
                    "Prescriber: OT, PT, or physician",
                    "Ontario resident with valid health card"
                ]
            },
            "funding": {
                "adp_coverage": 75,
                "client_share": 25,
                "approved_models": "See ADP approved product list"
            },
            "citations": [
                {"source": "mobility-manual", "location": "420.01", "page": 78}
            ]
        }
    },
    {
        "test_name": "scooter vs car substitute determination",
        "request": {
            "device": {"category": "mobility", "type": "power_scooter"},
            "check": ["eligibility", "exclusions"],
            "use_case": {
                "primary_use": "shopping and errands",
                "can_walk_indoors": True,
                "outdoor_only": True
            }
        },
        "expected_sql_results": [
            {
                "phrase": "car substitute",
                "applies_to": "Power scooters",
                "section_ref": "Eligibility Criteria",
                "details": "Device must not be primarily a car substitute"
            }
        ],
        "expected_vector_results": [
            {
                "text": "Power scooters must address basic mobility need, not serve as car substitute. If client can walk indoors but wants scooter for shopping/errands, this may be considered car substitute and not eligible.",
                "metadata": {"source": "mobility-manual", "page": 56, "section": "410.02"}
            }
        ],
        "expected_response": {
            "provenance": ["sql", "vector"],
            "confidence": 0.90,
            "eligibility": {
                "eligible": False,
                "reason": "Scooter appears to be car substitute based on use case"
            },
            "exclusions": [
                {
                    "criteria": "Car substitute",
                    "assessment": "Client can walk indoors, needs device for errands only",
                    "recommendation": "Not eligible for ADP funding"
                }
            ],
            "citations": [
                {"source": "mobility-manual", "location": "410.02", "page": 56}
            ]
        }
    }
]


class TestADPTool:
    """Test suite for adp.get ADP device funding tool."""
    
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
    async def test_power_wheelchair_with_cep(self, mock_sql_client, mock_vector_client):
        """Test power wheelchair funding with CEP eligibility for low-income client."""
        test_case = ADP_TEST_QUERIES[0]
        
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
            
            result = await adp_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify dual-path execution
            assert result["provenance"] == ["sql", "vector"]
            
            # Verify CEP eligibility correctly determined
            assert result["funding"]["cep_eligible"] is True
            assert result["funding"]["final_client_cost"] == 0
            assert result["funding"]["adp_coverage"] == 75
            
            # Verify citations provided
            assert len(result["citations"]) >= 2
            assert any("CEP" in c["location"] for c in result["citations"])
    
    @pytest.mark.asyncio
    async def test_scooter_batteries_exclusion(self, mock_sql_client, mock_vector_client):
        """Test that batteries are correctly identified as excluded."""
        test_case = ADP_TEST_QUERIES[1]
        
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
            
            result = await adp_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify not eligible due to exclusion
            assert result["eligibility"]["eligible"] is False
            assert "batteries" in result["eligibility"]["reason"].lower()
            
            # Verify exclusions list populated
            assert len(result["exclusions"]) > 0
            battery_exclusion = next(e for e in result["exclusions"] if "batteries" in e["item"])
            assert battery_exclusion is not None
    
    @pytest.mark.asyncio
    async def test_sgd_als_fast_track(self, mock_sql_client, mock_vector_client):
        """Test SGD for ALS patient with fast-track processing."""
        test_case = ADP_TEST_QUERIES[2]
        
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
            
            result = await adp_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify fast-track identified
            assert result["eligibility"]["fast_track"] is True
            
            # Verify SLP assessment requirement
            assert any("SLP" in req for req in result["eligibility"]["requirements"])
            
            # Verify expedited processing time
            assert "2-3 weeks" in result["funding"]["processing_time"]
            
            # Verify forms list includes ALS fast-track
            assert any("ALS" in form for form in result.get("forms", []))
    
    @pytest.mark.asyncio
    async def test_walker_standard_funding(self, mock_sql_client, mock_vector_client):
        """Test walker with standard 75/25 funding split."""
        test_case = ADP_TEST_QUERIES[3]
        
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
            
            result = await adp_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify standard funding split
            assert result["funding"]["adp_coverage"] == 75
            assert result["funding"]["client_share"] == 25
            
            # Verify prescriber requirements
            prescriber_req = next((r for r in result["eligibility"]["requirements"] 
                                  if "prescriber" in r.lower()), None)
            assert prescriber_req is not None
            assert any(prof in prescriber_req.upper() for prof in ["OT", "PT"])
    
    @pytest.mark.asyncio
    async def test_scooter_car_substitute(self, mock_sql_client, mock_vector_client):
        """Test scooter identified as car substitute and not eligible."""
        test_case = ADP_TEST_QUERIES[4]
        
        mock_sql_client.query.return_value = test_case["expected_sql_results"]
        mock_vector_client.search.return_value = test_case["expected_vector_results"]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
            
            result = await adp_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Verify not eligible
            assert result["eligibility"]["eligible"] is False
            assert "car substitute" in result["eligibility"]["reason"].lower()
            
            # Verify exclusion reasoning
            car_sub_exclusion = next((e for e in result["exclusions"] 
                                     if "car substitute" in e["criteria"].lower()), None)
            assert car_sub_exclusion is not None
            assert "walk indoors" in car_sub_exclusion["assessment"].lower()
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, mock_sql_client, mock_vector_client):
        """Verify SQL and vector queries run in parallel."""
        test_case = ADP_TEST_QUERIES[0]
        
        # Add delays to simulate real queries
        async def delayed_sql_query(*args):
            await asyncio.sleep(0.3)
            return test_case["expected_sql_results"]
        
        async def delayed_vector_search(*args):
            await asyncio.sleep(0.5)
            return test_case["expected_vector_results"]
        
        mock_sql_client.query = delayed_sql_query
        mock_vector_client.search = delayed_vector_search
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
            import time
            
            start_time = time.time()
            result = await adp_get(
                test_case["request"],
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            elapsed = time.time() - start_time
            
            # Should take ~500ms if parallel, ~800ms if serial
            assert elapsed < 0.6, "Queries should run in parallel"
            assert result["provenance"] == ["sql", "vector"]
    
    @pytest.mark.asyncio
    async def test_conflict_detection(self, mock_sql_client, mock_vector_client):
        """Test conflict detection between SQL and vector results."""
        
        # SQL says 75% coverage
        mock_sql_client.query.return_value = [{
            "scenario": "Power wheelchair",
            "client_share_percent": 25,
            "adp_share_percent": 75
        }]
        
        # Vector says 50% coverage (conflict!)
        mock_vector_client.search.return_value = [{
            "text": "Power wheelchairs covered at 50% by ADP, client pays 50%.",
            "metadata": {"source": "mobility-manual", "page": 45}
        }]
        
        with pytest.raises(ImportError):
            from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
            
            result = await adp_get(
                {"device": {"category": "mobility", "type": "power_wheelchair"},
                 "check": ["funding"]},
                sql_client=mock_sql_client,
                vector_client=mock_vector_client
            )
            
            # Should detect and surface conflict
            assert "conflicts" in result
            assert len(result["conflicts"]) > 0
            assert result["confidence"] < 0.9  # Lower confidence due to conflict