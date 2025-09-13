"""Unit tests for LLM-based guardrails."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.utils.llm_guardrails import LLMGuardrails


class TestLLMGuardrails:
    """Test suite for LLM-based guardrails."""
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client."""
        with patch('src.utils.llm_guardrails.Anthropic') as mock:
            yield mock
    
    @pytest.fixture
    def guardrails_llm(self, mock_anthropic_client):
        """Create LLM guardrails instance."""
        return LLMGuardrails(mode="llm")
    
    @pytest.fixture
    def guardrails_hybrid(self, mock_anthropic_client):
        """Create hybrid guardrails instance."""
        return LLMGuardrails(mode="hybrid")
    
    @pytest.fixture
    def guardrails_regex(self):
        """Create regex-only guardrails instance."""
        return LLMGuardrails(mode="regex")
    
    def test_input_emergency_detection_llm(self, guardrails_llm, mock_anthropic_client):
        """Test LLM detects emergency in user input."""
        # Arrange
        query = "I'm having severe chest pain and can't breathe"
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "requires_intervention": True,
                "intervention_type": "emergency",
                "explanation": "User describes severe chest pain and breathing difficulty"
            }))
        ]
        mock_anthropic_client.return_value.messages.create.return_value = mock_response
        
        # Act
        result = guardrails_llm.check_input(query)
        
        # Assert
        assert result["requires_intervention"] is True
        assert result["intervention_type"] == "emergency"
        assert result["should_block"] is True
        assert "chest pain" in result["explanation"].lower()
    
    def test_input_mental_health_crisis_detection_llm(self, guardrails_llm, mock_anthropic_client):
        """Test LLM detects mental health crisis."""
        # Arrange
        query = "I've been thinking about ending my life"
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "requires_intervention": True,
                "intervention_type": "mental_health_crisis",
                "explanation": "User expresses suicidal ideation"
            }))
        ]
        mock_anthropic_client.return_value.messages.create.return_value = mock_response
        
        # Act
        result = guardrails_llm.check_input(query)
        
        # Assert
        assert result["requires_intervention"] is True
        assert result["intervention_type"] == "mental_health_crisis"
        assert result["should_block"] is True
    
    def test_input_safe_query_llm(self, guardrails_llm, mock_anthropic_client):
        """Test LLM passes safe educational query."""
        # Arrange
        query = "What are the symptoms of diabetes?"
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "requires_intervention": False,
                "intervention_type": "none",
                "explanation": "Educational query about diabetes symptoms"
            }))
        ]
        mock_anthropic_client.return_value.messages.create.return_value = mock_response
        
        # Act
        result = guardrails_llm.check_input(query)
        
        # Assert
        assert result["requires_intervention"] is False
        assert result["intervention_type"] == "none"
        assert result["should_block"] is False
    
    def test_output_diagnosis_violation_llm(self, guardrails_llm, mock_anthropic_client):
        """Test LLM detects diagnosis in output."""
        # Arrange
        response = "Based on your symptoms, you have diabetes and should start insulin."
        citations = []
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "passes_guardrails": False,
                "violations": ["DIAGNOSIS", "TREATMENT"],
                "explanation": "Response provides specific diagnosis and treatment",
                "suggested_action": "block_response"
            }))
        ]
        mock_anthropic_client.return_value.messages.create.return_value = mock_response
        
        # Act
        result = guardrails_llm.check_output(response, citations)
        
        # Assert
        assert result["passes_guardrails"] is False
        assert "DIAGNOSIS" in result["violations"]
        assert "TREATMENT" in result["violations"]
        assert result["suggested_action"] == "block_response"
        assert "cannot provide" in result["modified_response"]
    
    def test_output_missing_disclaimer_llm(self, guardrails_llm, mock_anthropic_client):
        """Test LLM detects missing disclaimer."""
        # Arrange
        response = "Diabetes symptoms include increased thirst and frequent urination."
        citations = [{"url": "https://mayoclinic.org/diabetes"}]
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "passes_guardrails": False,
                "violations": ["MISSING_DISCLAIMER"],
                "explanation": "Response lacks medical disclaimer",
                "suggested_action": "add_disclaimer"
            }))
        ]
        mock_anthropic_client.return_value.messages.create.return_value = mock_response
        
        # Act
        result = guardrails_llm.check_output(response, citations)
        
        # Assert
        assert result["passes_guardrails"] is False
        assert "MISSING_DISCLAIMER" in result["violations"]
        assert result["suggested_action"] == "add_disclaimer"
        assert "Medical Disclaimer" in result["modified_response"]
    
    def test_output_safe_response_llm(self, guardrails_llm, mock_anthropic_client):
        """Test LLM passes safe educational response."""
        # Arrange
        response = (
            "⚠️ **Medical Disclaimer**: This information is for educational purposes only.\n\n"
            "Common diabetes symptoms include increased thirst and frequent urination. "
            "Please consult a healthcare provider for medical advice."
        )
        citations = [
            {"url": "https://cdc.gov/diabetes"},
            {"url": "https://mayoclinic.org/diabetes"}
        ]
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "passes_guardrails": True,
                "violations": [],
                "explanation": "Response is educational with proper disclaimers",
                "suggested_action": "pass"
            }))
        ]
        mock_anthropic_client.return_value.messages.create.return_value = mock_response
        
        # Act
        result = guardrails_llm.check_output(response, citations)
        
        # Assert
        assert result["passes_guardrails"] is True
        assert len(result["violations"]) == 0
        assert result["suggested_action"] == "pass"
        assert result["modified_response"] == response  # No changes
    
    def test_hybrid_mode_fallback_to_regex(self, guardrails_hybrid, mock_anthropic_client):
        """Test hybrid mode falls back to regex when LLM fails."""
        # Arrange
        query = "I'm having chest pain right now"
        
        # Mock LLM failure
        mock_anthropic_client.return_value.messages.create.side_effect = Exception("API error")
        
        # Act
        result = guardrails_hybrid.check_input(query)
        
        # Assert (regex should catch "chest pain")
        assert result["requires_intervention"] is True
        assert result["intervention_type"] == "emergency"
        assert result["should_block"] is True
    
    def test_regex_mode_emergency_detection(self, guardrails_regex):
        """Test regex mode detects emergencies."""
        # Arrange
        query = "I'm having severe chest pain"
        
        # Act
        result = guardrails_regex.check_input(query)
        
        # Assert
        assert result["requires_intervention"] is True
        assert result["intervention_type"] == "emergency"
        assert result["should_block"] is True
    
    def test_regex_mode_output_violations(self, guardrails_regex):
        """Test regex mode detects forbidden phrases."""
        # Arrange
        response = "Based on your symptoms, you have diabetes."
        
        # Act
        result = guardrails_regex.check_output(response)
        
        # Assert
        assert result["passes_guardrails"] is False
        assert "you have" in result["violations"]
        assert "[medical assessment needed]" in result["modified_response"]
    
    def test_llm_json_parse_error_handling(self, guardrails_llm, mock_anthropic_client):
        """Test handling of invalid JSON from LLM."""
        # Arrange
        query = "What are symptoms of flu?"
        
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.content = [
            Mock(text="This is not valid JSON")
        ]
        mock_anthropic_client.return_value.messages.create.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(Exception):  # Should raise or handle gracefully
            guardrails_llm.check_input(query)
    
    def test_apply_suggested_actions(self, guardrails_llm):
        """Test different suggested actions are applied correctly."""
        # Test block_response action
        blocked = guardrails_llm._apply_suggested_action(
            "You have cancer", 
            "block_response", 
            ["DIAGNOSIS"]
        )
        assert "cannot provide" in blocked
        assert "healthcare provider" in blocked
        
        # Test add_disclaimer action
        with_disclaimer = guardrails_llm._apply_suggested_action(
            "Diabetes symptoms include thirst",
            "add_disclaimer",
            ["MISSING_DISCLAIMER"]
        )
        assert "Medical Disclaimer" in with_disclaimer
        assert "educational purposes" in with_disclaimer
        
        # Test remove_diagnosis action
        cleaned = guardrails_llm._apply_suggested_action(
            "You have diabetes and your symptoms indicate this",
            "remove_diagnosis",
            ["DIAGNOSIS"]
        )
        assert "you have" not in cleaned
        assert "your symptoms" not in cleaned
        assert "may indicate" in cleaned or "could be" in cleaned