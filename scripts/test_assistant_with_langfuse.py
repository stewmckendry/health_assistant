#!/usr/bin/env python
"""Test PatientAssistant with Langfuse tracing enabled."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.assistants.patient import PatientAssistant
from langfuse import get_client

def test_patient_assistant_with_tracing():
    """Test the patient assistant with full Langfuse tracing."""
    
    print("🚀 Testing PatientAssistant with Langfuse tracing...")
    print("-" * 50)
    
    # Initialize Langfuse client to verify connection
    langfuse = get_client()
    if langfuse.auth_check():
        print("✅ Langfuse connected")
    else:
        print("❌ Langfuse not connected")
        return
    
    # Initialize PatientAssistant
    assistant = PatientAssistant(guardrail_mode="hybrid")
    print("✅ PatientAssistant initialized with hybrid guardrails")
    
    # Test queries
    test_queries = [
        {
            "query": "What are the common symptoms of the flu?",
            "session_id": "test_flu_001",
            "description": "Basic medical information query"
        },
        {
            "query": "I have chest pain and can't breathe, what should I do?",
            "session_id": "test_emergency_001",
            "description": "Emergency detection test"
        },
        {
            "query": "What foods help lower blood pressure naturally?",
            "session_id": "test_nutrition_001",
            "description": "Nutrition and lifestyle query"
        }
    ]
    
    for test_case in test_queries:
        print(f"\n📝 Test: {test_case['description']}")
        print(f"   Query: {test_case['query'][:50]}...")
        print(f"   Session: {test_case['session_id']}")
        
        try:
            # Process query
            response = assistant.query(
                query=test_case["query"],
                session_id=test_case["session_id"]
            )
            
            # Display results
            print(f"   ✅ Response received")
            print(f"   - Guardrails applied: {response.get('guardrails_applied', False)}")
            print(f"   - Emergency detected: {response.get('emergency_detected', False)}")
            print(f"   - Citations: {len(response.get('citations', []))}")
            print(f"   - Response length: {len(response.get('content', ''))}")
            
            # Score the trace for evaluation
            langfuse.score_current_trace(
                name="test_run_success",
                value=1.0 if not response.get('error') else 0.0,
                data_type="NUMERIC",
                comment=f"Test case: {test_case['description']}"
            )
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Flush all traces to Langfuse
    print("\n" + "-" * 50)
    print("💾 Flushing traces to Langfuse...")
    langfuse.flush()
    print("✅ All traces sent to Langfuse dashboard")
    print("\n🎯 Check your Langfuse dashboard at: https://us.cloud.langfuse.com")
    print("   Look for traces with names: 'patient_query', 'llm_call', 'input_guardrail_check', etc.")

if __name__ == "__main__":
    test_patient_assistant_with_tracing()