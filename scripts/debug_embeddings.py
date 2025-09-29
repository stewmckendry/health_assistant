#!/usr/bin/env python3
"""
Debug script to check embedding generation
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.dr_off_agent.ingestion.ingesters.ohip_ingester import EnhancedOHIPIngester
import os

def debug_embeddings():
    """Debug embedding generation"""
    
    print("Debugging embedding generation...")
    print(f"OpenAI API Key loaded: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    # Create ingester instance with OpenAI API key
    ingester = EnhancedOHIPIngester(
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Check if OpenAI client is working
    print(f"OpenAI client created: {ingester.openai_client is not None}")
    
    # Test embedding generation with a simple text
    test_texts = [
        "OHIP Fee Code C122",
        "Service: Subsequent visit by the Most Responsible Physician (MRP)",
        "Fee Amount: $61.15"
    ]
    
    print(f"\nTesting embeddings for {len(test_texts)} texts...")
    embeddings = ingester.generate_embeddings(test_texts)
    
    print(f"Generated {len(embeddings)} embeddings")
    for i, embedding in enumerate(embeddings):
        print(f"Embedding {i+1}: {len(embedding)} dimensions")
        print(f"  First 5 values: {embedding[:5]}")
        print(f"  Sum: {sum(embedding):.4f}")
        print(f"  All zeros? {all(v == 0.0 for v in embedding)}")

if __name__ == "__main__":
    debug_embeddings()