#!/usr/bin/env python
"""Debug script to see raw API response."""
import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import settings

def debug_response():
    """Debug the raw API response."""
    
    # Initialize client
    client = Anthropic(api_key=settings.anthropic_api_key)
    
    query = "What are the common symptoms of diabetes?"
    
    print(f"Query: {query}")
    print(f"Model: {settings.primary_model}")
    
    # Tools configuration with both search and fetch
    tools = [
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 3
        },
        {
            "type": "web_fetch_20250910",
            "name": "web_fetch",
            "allowed_domains": settings.trusted_domains[:20],  # Use first 20 domains
            "max_uses": 5,
            "citations": {"enabled": True}
        }
    ]
    
    try:
        # Make API call
        response = client.messages.create(
            model=settings.primary_model,
            max_tokens=1500,
            temperature=0.7,
            system=settings.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": query
                }
            ],
            tools=tools,
            extra_headers={
                "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
            }
        )
        
        # Extract full text response
        full_text = ""
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                full_text += str(block.text)
        
        print("\n=== FULL RESPONSE TEXT ===")
        print(full_text)
        
        # Check for emergency keywords
        print("\n=== CHECKING FOR EMERGENCY KEYWORDS ===")
        from src.utils.guardrails import EMERGENCY_KEYWORDS
        
        text_lower = full_text.lower()
        triggers = []
        for keyword in EMERGENCY_KEYWORDS:
            if keyword in text_lower:
                triggers.append(keyword)
                # Find the context
                index = text_lower.find(keyword)
                start = max(0, index - 50)
                end = min(len(full_text), index + len(keyword) + 50)
                context = full_text[start:end]
                print(f"FOUND: '{keyword}'")
                print(f"  Context: ...{context}...")
        
        if triggers:
            print(f"\n⚠️ Emergency keywords found: {triggers}")
        else:
            print("\n✅ No emergency keywords found")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_response()