#!/usr/bin/env python
"""Test script to debug web fetch tool issues."""
import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import settings

def test_web_fetch():
    """Test the web fetch tool directly."""
    
    # Initialize client
    client = Anthropic(api_key=settings.anthropic_api_key)
    
    # Prepare a simple query that should trigger web fetch
    query = "According to the Mayo Clinic website, what are the symptoms of diabetes?"
    
    print(f"Testing web fetch with query: {query}")
    print(f"Model: {settings.primary_model}")
    print(f"Trusted domains count: {len(settings.trusted_domains)}")
    print(f"Sample trusted domains: {settings.trusted_domains[:5]}")
    
    # Prepare tools configuration
    tools = [
        {
            "type": "web_fetch_20250910",
            "name": "web_fetch",
            "allowed_domains": ["mayoclinic.org", "cdc.gov"],  # Test with just 2 domains
            "max_uses": 3
        }
    ]
    
    print(f"\nTools configuration: {tools}")
    
    try:
        # Make API call with explicit tool use instruction
        response = client.messages.create(
            model=settings.primary_model,
            max_tokens=1500,
            temperature=0.7,
            system="You are a helpful assistant. Use the web_fetch tool to get information from Mayo Clinic about diabetes symptoms.",
            messages=[
                {
                    "role": "user",
                    "content": query
                }
            ],
            tools=tools,
            extra_headers={"anthropic-beta": "web-fetch-2025-09-10"}
        )
        
        print("\n=== RESPONSE ===")
        print(f"Model: {response.model}")
        print(f"Stop reason: {response.stop_reason}")
        print(f"Usage: {response.usage}")
        
        # Check content blocks
        print("\n=== CONTENT BLOCKS ===")
        for i, block in enumerate(response.content):
            print(f"\nBlock {i}:")
            print(f"  Type: {block.type if hasattr(block, 'type') else 'unknown'}")
            if hasattr(block, 'text'):
                print(f"  Text: {block.text[:200]}..." if len(str(block.text)) > 200 else f"  Text: {block.text}")
            if hasattr(block, 'name'):
                print(f"  Tool name: {block.name}")
            if hasattr(block, 'input'):
                print(f"  Tool input: {block.input}")
            
            # Check for web fetch specific attributes
            if hasattr(block, 'url'):
                print(f"  URL: {block.url}")
            if hasattr(block, 'status_code'):
                print(f"  Status code: {block.status_code}")
            if hasattr(block, 'error'):
                print(f"  Error: {block.error}")
        
        # Extract full text
        full_text = ""
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                full_text += str(block.text)
        
        print("\n=== FULL RESPONSE TEXT ===")
        print(full_text)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_web_fetch()