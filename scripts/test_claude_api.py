#!/usr/bin/env python
"""Test Claude API connectivity."""

import os
import time
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

def test_claude_api():
    """Test basic Claude API call."""
    
    print("Testing Claude API...")
    print("="*60)
    
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Initialize client
    client = Anthropic(api_key=api_key)
    
    # Test with different models
    models = [
        "claude-3-haiku-20240307",
        "claude-3-5-haiku-latest", 
        "claude-3-opus-20240229",
        "claude-3-5-sonnet-latest"
    ]
    
    for model in models:
        print(f"\nTesting model: {model}")
        print("-"*40)
        
        try:
            # Simple test message
            response = client.messages.create(
                model=model,
                max_tokens=100,
                temperature=0,
                messages=[
                    {"role": "user", "content": "Say 'API is working' if you can read this."}
                ]
            )
            
            # Extract response
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
            
            print(f"✅ Success: {content[:50]}")
            
        except Exception as e:
            error_msg = str(e)
            if "529" in error_msg or "overloaded" in error_msg.lower():
                print(f"⚠️ API Overloaded (529): Service is temporarily overloaded")
            elif "404" in error_msg:
                print(f"❌ Model not found (404): {model} may not be available")
            elif "401" in error_msg:
                print(f"❌ Authentication error (401): Check API key")
            else:
                print(f"❌ Error: {error_msg[:100]}")
        
        # Small delay between tests
        time.sleep(2)
    
    print("\n" + "="*60)
    print("Test complete. If all models show overloaded, the API is experiencing high load.")
    print("Try again in a few minutes.")

if __name__ == "__main__":
    test_claude_api()