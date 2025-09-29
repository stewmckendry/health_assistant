#!/usr/bin/env python3
"""
Test the LLM reranker directly
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from src.agents.dr_off_agent.mcp.utils.llm_reranker import LLMReranker, Document

async def test_reranker():
    """Test LLM reranker directly"""
    
    print("Testing LLM Reranker...")
    print(f"OpenAI API Key loaded: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    # Create reranker
    reranker = LLMReranker()
    print(f"Reranker created: {reranker}")
    print(f"Reranker OpenAI client: {reranker.client is not None}")
    
    # Create test documents
    docs = [
        Document(
            text="OHIP Fee Code W562 - Admission assessment - Type 1 - Fee Amount: $69.35",
            metadata={"fee_code": "W562", "specialty": "A"}
        ),
        Document(
            text="OHIP Fee Code E840 - with repair of septal perforation - Fee Amount: $119.20",
            metadata={"fee_code": "E840", "specialty": "P"}
        ),
        Document(
            text="OHIP Fee Code C122 - Day following the hospital admission assessment - Fee Amount: $61.15",
            metadata={"fee_code": "C122", "specialty": "A"}
        )
    ]
    
    # Test reranking
    query = "hospital admission assessment"
    
    print(f"\nTesting reranking for query: '{query}'")
    print(f"Input documents: {len(docs)}")
    
    try:
        reranked = await reranker.rerank(query, docs, top_k=3)
        print(f"Reranked documents: {len(reranked)}")
        
        for i, doc in enumerate(reranked):
            print(f"  {i+1}. Score: {doc.relevance_score:.2f} - {doc.text[:80]}...")
            
    except Exception as e:
        print(f"Reranking failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reranker())