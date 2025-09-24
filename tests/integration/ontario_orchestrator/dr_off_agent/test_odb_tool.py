"""
TDD Test Suite for ODB Tool - Real prescribing scenarios
Tests MUST fail initially (Red), then pass after implementation (Green)
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# These imports will exist after implementation
from src.agents.ontario_orchestrator.mcp.tools.odb import ODBTool
from src.agents.ontario_orchestrator.mcp.models.request import ODBGetRequest
from src.agents.ontario_orchestrator.mcp.models.response import ODBGetResponse


class TestODBToolRealScenarios:
    """Test real prescribing scenarios that Ontario clinicians face daily."""
    
    @pytest.fixture
    def odb_tool(self):
        """Create ODB tool instance for testing."""
        return ODBTool()
    
    @pytest.mark.asyncio
    async def test_metformin_coverage_and_cheaper_alternatives(self, odb_tool):
        """
        Scenario: Clinician needs to know if metformin is covered and what
        are the cheaper alternatives for a diabetic patient.
        """
        request = ODBGetRequest(
            q="metformin coverage and cheaper alternatives",
            drug="metformin",
            check=["coverage", "interchangeable", "lowest_cost"],
            top_k=5
        )
        
        response = await odb_tool.execute(request)
        
        # Assertions for expected outcomes
        assert isinstance(response, ODBGetResponse)
        assert response.coverage.covered is True, "Metformin should be covered"
        assert response.coverage.plan == "ODB", "Should be on ODB formulary"
        
        # Should have interchangeable generics
        assert response.interchangeable is not None
        assert response.interchangeable.group_id is not None
        assert len(response.interchangeable.members) > 1, "Should have multiple generic options"
        
        # Should identify lowest cost option
        assert response.lowest_cost is not None
        assert response.lowest_cost.din is not None
        assert response.lowest_cost.price > 0
        assert response.lowest_cost.price < 50, "Generic metformin should be under $50"
        
        # Should have both SQL and vector provenance
        assert "sql" in response.provenance
        assert "vector" in response.provenance
        
        # Should have citations from vector search
        assert len(response.citations) > 0
        assert any("formulary" in c.source.lower() for c in response.citations)
        
        # Confidence should be high (SQL hit + vector corroboration)
        assert response.confidence >= 0.9
    
    @pytest.mark.asyncio
    async def test_ozempic_t2dm_with_lu_requirements(self, odb_tool):
        """
        Scenario: Ozempic (semaglutide) for Type 2 Diabetes - needs Limited Use criteria.
        DIN: 02468646
        """
        request = ODBGetRequest(
            q="Ozempic for T2DM with LU code requirements",
            din="02468646",
            check=["coverage", "lu_criteria", "documentation"],
            condition="type 2 diabetes"
        )
        
        response = await odb_tool.execute(request)
        
        assert response.coverage.covered is True, "Ozempic should be covered with LU"
        assert response.coverage.requires_lu is True, "Should require Limited Use code"
        
        # LU criteria should be present
        assert response.lu_criteria is not None
        assert response.lu_criteria.code is not None  # e.g., "LU 123"
        assert "metformin" in response.lu_criteria.requirements.lower(), \
            "Should mention metformin failure requirement"
        assert response.lu_criteria.documentation_needed is not None
        
        # Should have citations explaining LU requirements
        assert any("limited use" in c.source.lower() for c in response.citations)
        
        # Should detect if SQL has drug but vector has LU details
        assert len(response.provenance) == 2, "Should use both paths"
    
    @pytest.mark.asyncio  
    async def test_januvia_vs_sitagliptin_generic_pricing(self, odb_tool):
        """
        Scenario: Compare brand Januvia vs generic sitagliptin pricing.
        Patient wants to know if generic is available and how much they save.
        """
        request = ODBGetRequest(
            q="Januvia vs sitagliptin generic pricing",
            ingredient="sitagliptin",
            check=["interchangeable_group", "price_comparison"],
            include_brand=True
        )
        
        response = await odb_tool.execute(request)
        
        # Should find interchangeable group
        assert response.interchangeable is not None
        assert response.interchangeable.group_name is not None
        
        # Should have both brand and generic
        members = response.interchangeable.members
        brand = [m for m in members if "januvia" in m.brand.lower()]
        generics = [m for m in members if "januvia" not in m.brand.lower()]
        
        assert len(brand) > 0, "Should find brand Januvia"
        assert len(generics) > 0, "Should find generic alternatives"
        
        # Generic should be cheaper
        brand_price = brand[0].price
        generic_price = min(g.price for g in generics)
        assert generic_price < brand_price, "Generic should cost less than brand"
        
        # Price comparison should be included
        assert response.price_comparison is not None
        assert response.price_comparison.brand_price == brand_price
        assert response.price_comparison.generic_price == generic_price
        assert response.price_comparison.savings > 0
        
    @pytest.mark.asyncio
    async def test_drug_not_covered_suggest_alternatives(self, odb_tool):
        """
        Scenario: Drug not on formulary (e.g., new GLP-1), suggest covered alternatives.
        """
        request = ODBGetRequest(
            q="Is Mounjaro covered? What are alternatives?",
            drug="tirzepatide",  # Mounjaro
            check=["coverage", "alternatives"],
            drug_class="glp1 agonist"
        )
        
        response = await odb_tool.execute(request)
        
        assert response.coverage.covered is False, "Mounjaro not yet on ODB"
        assert response.coverage.plan == "not_covered"
        
        # Should suggest alternatives
        assert response.alternatives is not None
        assert len(response.alternatives) > 0
        
        # Alternatives should include other GLP-1s
        alt_names = [a.drug_name.lower() for a in response.alternatives]
        assert any("ozempic" in name or "semaglutide" in name for name in alt_names)
        
        # Should explain via citations
        assert any("not listed" in c.text.lower() for c in response.citations)
    
    @pytest.mark.asyncio
    async def test_statin_lowest_cost_without_lu(self, odb_tool):
        """
        Scenario: Find cheapest statin that doesn't require Limited Use authorization.
        """
        request = ODBGetRequest(
            q="Cheapest statin without LU requirement",
            drug_class="statin",
            check=["lowest_cost", "lu_criteria"],
            exclude_lu=True
        )
        
        response = await odb_tool.execute(request)
        
        assert response.lowest_cost is not None
        assert response.lowest_cost.price < 100, "Generic statins should be affordable"
        
        # Should NOT require LU
        assert response.coverage.requires_lu is False
        
        # Common generic statins should appear
        drug_name = response.lowest_cost.drug_name.lower()
        common_statins = ["atorvastatin", "simvastatin", "pravastatin", "rosuvastatin"]
        assert any(s in drug_name for s in common_statins)
    
    @pytest.mark.asyncio
    async def test_interchangeable_group_with_multiple_strengths(self, odb_tool):
        """
        Scenario: Get all strengths and forms within an interchangeable group.
        """
        request = ODBGetRequest(
            q="All amlodipine options and strengths",
            ingredient="amlodipine",
            check=["interchangeable_group", "all_strengths"]
        )
        
        response = await odb_tool.execute(request)
        
        assert response.interchangeable is not None
        
        # Should have multiple strengths
        strengths = set()
        for member in response.interchangeable.members:
            if member.strength:
                strengths.add(member.strength)
        
        assert len(strengths) >= 3, "Amlodipine comes in 2.5mg, 5mg, 10mg at minimum"
        
        # All should be in same group
        group_ids = set(m.group_id for m in response.interchangeable.members)
        assert len(group_ids) == 1, "All amlodipine products should share group ID"
    
    @pytest.mark.asyncio
    async def test_conflict_detection_coverage_discrepancy(self, odb_tool):
        """
        Scenario: SQL says covered but vector docs mention restrictions - 
        should surface conflict.
        """
        # Mock conflicting data
        with patch.object(odb_tool.sql_client, 'query_odb_drugs') as mock_sql:
            mock_sql.return_value = [{
                'din': '12345678',
                'covered': True,
                'price': 50.00
            }]
            
            with patch.object(odb_tool.vector_client, 'search_odb') as mock_vector:
                mock_vector.return_value = [{
                    'text': 'This drug requires special authorization and may not be covered for all indications.',
                    'metadata': {'source': 'odb_formulary.pdf', 'page': 123}
                }]
                
                request = ODBGetRequest(
                    q="Drug coverage check",
                    din="12345678",
                    check=["coverage"]
                )
                
                response = await odb_tool.execute(request)
                
                # Should detect and report conflict
                assert len(response.conflicts) > 0
                conflict = response.conflicts[0]
                assert "coverage" in conflict.field
                assert conflict.sql_value == "covered"
                assert "special authorization" in conflict.vector_value
                
                # Confidence should be reduced
                assert response.confidence < 0.9


class TestODBToolEdgeCases:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def odb_tool(self):
        return ODBTool()
    
    @pytest.mark.asyncio
    async def test_sql_timeout_still_returns_vector_results(self, odb_tool):
        """If SQL times out, should still return vector results."""
        with patch.object(odb_tool.sql_client, 'query_odb_drugs') as mock_sql:
            mock_sql.side_effect = asyncio.TimeoutError()
            
            request = ODBGetRequest(
                q="metformin coverage",
                drug="metformin",
                check=["coverage"]
            )
            
            response = await odb_tool.execute(request)
            
            # Should still have response
            assert response is not None
            assert "vector" in response.provenance
            assert "sql" not in response.provenance  # SQL failed
            
            # Confidence should be lower without SQL
            assert response.confidence < 0.9
    
    @pytest.mark.asyncio
    async def test_empty_results_needs_more_info(self, odb_tool):
        """When no data found, should indicate needs_more_info."""
        request = ODBGetRequest(
            q="Non-existent drug XYZ123",
            drug="XYZ123",
            check=["coverage"]
        )
        
        response = await odb_tool.execute(request)
        
        assert response.coverage.covered is False
        assert response.coverage.plan == "not_found"
        assert response.needs_more_info is True
        assert response.confidence < 0.5  # Low confidence when no data


class TestODBToolIntegration:
    """Integration tests with actual database (if available)."""
    
    @pytest.fixture
    def odb_tool(self):
        return ODBTool()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_database_metformin_query(self, odb_tool):
        """Test against actual ODB database if available."""
        # Skip if database not available
        import os
        db_path = "data/processed/dr_off/dr_off.db"
        if not os.path.exists(db_path):
            pytest.skip("Database not available")
        
        request = ODBGetRequest(
            q="metformin 500mg coverage",
            ingredient="metformin",
            strength="500",
            check=["coverage", "interchangeable", "lowest_cost"]
        )
        
        response = await odb_tool.execute(request)
        
        # Real data assertions
        assert response.coverage.covered is True
        assert response.interchangeable is not None
        assert len(response.interchangeable.members) > 5  # Many metformin generics
        assert response.lowest_cost.price < 20  # Metformin is cheap
        
        # Should have real citations
        assert len(response.citations) > 0
        assert response.citations[0].source == "odb_formulary"