"""Unit tests for enhanced guardrails with web fetch verification."""
import pytest
from unittest.mock import Mock, patch

from src.utils.llm_guardrails import LLMGuardrails


class TestEnhancedGuardrails:
    """Test suite for enhanced guardrails with source verification."""
    
    @pytest.fixture
    def guardrails(self):
        """Create guardrails instance."""
        with patch('src.utils.llm_guardrails.Anthropic'):
            return LLMGuardrails(mode="hybrid")
    
    def test_no_trusted_sources_violation(self, guardrails):
        """Test that medical info without trusted sources is flagged."""
        # Medical response without citations
        response = "Diabetes symptoms include increased thirst and frequent urination."
        citations = []
        tool_calls = []
        
        result = guardrails.check_output(response, citations, None, tool_calls)
        
        assert result["passes_guardrails"] is False
        assert "NO_TRUSTED_SOURCES" in result["violations"]
        assert result["suggested_action"] == "require_sources"
        assert "needs to be verified" in result["modified_response"]
    
    def test_trusted_sources_passes(self, guardrails):
        """Test that medical info with trusted sources passes."""
        response = "Diabetes symptoms include increased thirst and frequent urination."
        citations = [
            {"url": "https://www.mayoclinic.org/diabetes", "title": "Diabetes - Mayo Clinic"},
            {"url": "https://www.cdc.gov/diabetes", "title": "Diabetes - CDC"}
        ]
        tool_calls = [
            {"type": "server_tool_use", "name": "web_search"},
            {"type": "server_tool_use", "name": "web_fetch"}
        ]
        
        result = guardrails.check_output(response, citations, None, tool_calls)
        
        # Should pass if it has trusted sources
        assert result["has_trusted_citations"] is True
        assert result["web_search_performed"] is True
    
    def test_untrusted_sources_violation(self, guardrails):
        """Test that citations from untrusted sources are flagged."""
        response = "Diabetes symptoms include increased thirst and frequent urination."
        citations = [
            {"url": "https://random-blog.com/diabetes", "title": "My Diabetes Blog"},
            {"url": "https://unknown-site.net/health", "title": "Health Tips"}
        ]
        tool_calls = [
            {"type": "server_tool_use", "name": "web_search"}
        ]
        
        result = guardrails.check_output(response, citations, None, tool_calls)
        
        assert result["has_trusted_citations"] is False
        assert result["passes_guardrails"] is False
        assert "NO_TRUSTED_SOURCES" in result["violations"]
    
    def test_web_search_detection(self, guardrails):
        """Test detection of web search tool usage."""
        # Test with web search tools
        tool_calls = [
            {"type": "server_tool_use", "name": "web_search"},
            {"type": "web_fetch_result", "url": "https://mayoclinic.org"}
        ]
        
        assert guardrails._check_web_search_performed(tool_calls) is True
        
        # Test without web search tools
        tool_calls = [
            {"type": "other_tool", "name": "calculator"}
        ]
        
        assert guardrails._check_web_search_performed(tool_calls) is False
        
        # Test with empty list
        assert guardrails._check_web_search_performed([]) is False
        assert guardrails._check_web_search_performed(None) is False
    
    def test_trusted_citation_validation(self, guardrails):
        """Test validation of trusted medical domains."""
        # Mayo Clinic - trusted
        citations = [{"url": "https://www.mayoclinic.org/diseases"}]
        assert guardrails._check_trusted_citations(citations) is True
        
        # CDC - trusted
        citations = [{"url": "https://www.cdc.gov/diabetes"}]
        assert guardrails._check_trusted_citations(citations) is True
        
        # NIH - trusted
        citations = [{"url": "https://www.nih.gov/health"}]
        assert guardrails._check_trusted_citations(citations) is True
        
        # Cleveland Clinic - trusted
        citations = [{"url": "https://my.clevelandclinic.org/health"}]
        assert guardrails._check_trusted_citations(citations) is True
        
        # PubMed - trusted
        citations = [{"url": "https://pubmed.ncbi.nlm.nih.gov/12345"}]
        assert guardrails._check_trusted_citations(citations) is True
        
        # WHO - trusted
        citations = [{"url": "https://www.who.int/topics"}]
        assert guardrails._check_trusted_citations(citations) is True
        
        # Random blog - not trusted
        citations = [{"url": "https://random-health-blog.com"}]
        assert guardrails._check_trusted_citations(citations) is False
        
        # Mixed - should pass if at least one is trusted
        citations = [
            {"url": "https://random-blog.com"},
            {"url": "https://www.mayoclinic.org/health"}
        ]
        assert guardrails._check_trusted_citations(citations) is True
    
    def test_medical_info_detection(self, guardrails):
        """Test detection of medical information in responses."""
        # Clear medical information
        assert guardrails._contains_medical_info("Diabetes symptoms include thirst") is True
        assert guardrails._contains_medical_info("Treatment for hypertension") is True
        assert guardrails._contains_medical_info("Consult your physician") is True
        
        # Non-medical content
        assert guardrails._contains_medical_info("The weather is nice today") is False
        assert guardrails._contains_medical_info("How to bake a cake") is False
    
    def test_non_medical_response_passes(self, guardrails):
        """Test that non-medical responses don't require sources."""
        response = "The weather today is sunny with a high of 75 degrees."
        citations = []
        tool_calls = []
        
        result = guardrails.check_output(response, citations, None, tool_calls)
        
        # Should pass even without sources since it's not medical
        assert "NO_TRUSTED_SOURCES" not in result.get("violations", [])
    
    def test_government_edu_domains_trusted(self, guardrails):
        """Test that .gov and .edu domains are trusted."""
        # .gov domain
        citations = [{"url": "https://health.gov/guidelines"}]
        assert guardrails._check_trusted_citations(citations) is True
        
        # .edu domain
        citations = [{"url": "https://medicine.stanford.edu/research"}]
        assert guardrails._check_trusted_citations(citations) is True
    
    def test_empty_citations_handled(self, guardrails):
        """Test handling of empty or None citations."""
        assert guardrails._check_trusted_citations([]) is False
        assert guardrails._check_trusted_citations(None) is False
        assert guardrails._check_trusted_citations([{"url": ""}]) is False
        assert guardrails._check_trusted_citations([{"title": "No URL"}]) is False