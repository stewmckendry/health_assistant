#!/usr/bin/env python
"""Test Langfuse connection and basic functionality."""

import os
from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables
load_dotenv()

def test_langfuse_connection():
    """Test that we can connect to Langfuse."""
    try:
        # Initialize Langfuse client
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        )
        
        # Test authentication
        if langfuse.auth_check():
            print("✅ Langfuse authentication successful!")
            print(f"   Host: {os.getenv('LANGFUSE_HOST')}")
            print(f"   Project: health_assistant")
            
            # Create a test trace using the observe decorator
            from langfuse import observe
            
            @observe(name="test_function")
            def test_traced_function():
                """Simple function to test tracing."""
                langfuse.score_current_trace(
                    name="test_score",
                    value=1.0,
                    data_type="NUMERIC",
                    comment="Test score from connection test"
                )
                return "Test successful"
            
            # Call the traced function
            result = test_traced_function()
            print(f"✅ Created test trace: {result}")
            
            # Flush to ensure it's sent
            langfuse.flush()
            print("✅ Traces flushed to Langfuse")
            
            return True
        else:
            print("❌ Langfuse authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Langfuse: {e}")
        return False

if __name__ == "__main__":
    test_langfuse_connection()