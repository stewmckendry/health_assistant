#!/usr/bin/env python3
"""
Investigate vector embedding quality by testing semantic search directly on ChromaDB
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

import chromadb
from chromadb.config import Settings
import openai
import numpy as np

def investigate_embeddings():
    """Investigate vector embedding quality and semantic search"""
    
    print("🔍 Investigating Vector Embedding Quality...")
    chroma_path = 'data/dr_off_agent/processed/dr_off/chroma'
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection('ohip_documents')
    
    print(f"📊 Collection has {collection.count()} documents\n")
    
    # Initialize OpenAI client
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Test queries with expected results
    test_cases = [
        {
            "query": "hospital admission assessment",
            "expected_codes": ["C122", "E082", "W562", "W232", "W234"],
            "description": "Should find admission-related codes"
        },
        {
            "query": "patient discharge from hospital", 
            "expected_codes": ["C122", "C123", "C124"],
            "description": "Should find discharge/follow-up codes"
        },
        {
            "query": "subsequent visit by physician",
            "expected_codes": ["C122", "C123", "C124"],
            "description": "Should find physician visit codes"
        },
        {
            "query": "day following hospital admission",
            "expected_codes": ["C122"],
            "description": "Should specifically find C122"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"=== Test Case {i+1}: {test_case['query']} ===")
        print(f"Expected: {test_case['expected_codes']}")
        print(f"Goal: {test_case['description']}\n")
        
        # Generate query embedding
        query_embedding = openai_client.embeddings.create(
            input=[test_case['query']],
            model="text-embedding-3-small"
        ).data[0].embedding
        
        # Search in ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=15,
            where={"source_type": "ohip"},
            include=["documents", "metadatas", "distances"]
        )
        
        print("🔍 Raw Vector Search Results:")
        found_expected = []
        
        for j, doc in enumerate(results['documents'][0]):
            distance = results['distances'][0][j]
            similarity = 1 - distance
            metadata = results['metadatas'][0][j]
            fee_code = metadata.get('fee_code', 'Unknown')
            
            # Check if this is an expected code
            is_expected = fee_code in test_case['expected_codes']
            if is_expected:
                found_expected.append(fee_code)
                status = "✅ EXPECTED"
            else:
                status = "❌ Unexpected"
            
            print(f"  {j+1:2d}. {status} | Code: {fee_code} | Similarity: {similarity:.4f}")
            print(f"      Text: {doc[:80]}...")
            
            # Show first 5 in detail
            if j < 5:
                print(f"      Full Text: {doc}")
                print(f"      Metadata: {metadata}")
            print()
        
        # Analysis
        expected_found = len(found_expected)
        expected_total = len(test_case['expected_codes'])
        missing = set(test_case['expected_codes']) - set(found_expected)
        
        print(f"📈 Analysis:")
        print(f"  - Found {expected_found}/{expected_total} expected codes")
        print(f"  - Missing codes: {list(missing)}")
        print(f"  - Best similarity score: {(1 - results['distances'][0][0]):.4f}")
        print(f"  - Worst similarity score: {(1 - results['distances'][0][-1]):.4f}")
        print()
        
        # Check if expected codes exist in collection at all
        if missing:
            print("🔎 Checking if missing codes exist in collection...")
            for code in missing:
                check_results = collection.get(
                    where={"fee_code": code},
                    include=["documents", "metadatas"]
                )
                
                if check_results['documents']:
                    print(f"  ✅ {code} EXISTS in collection:")
                    print(f"      Text: {check_results['documents'][0][:100]}...")
                else:
                    print(f"  ❌ {code} NOT FOUND in collection")
            print()
        
        print("="*80 + "\n")
    
    # Additional analysis: Check embedding quality
    print("🧪 Additional Analysis: Embedding Quality Check")
    
    # Get a few specific documents we know should be similar
    c122_docs = collection.get(
        where={"fee_code": "C122"},
        include=["documents", "embeddings"],
        limit=3
    )
    
    if c122_docs['documents']:
        print(f"Found {len(c122_docs['documents'])} C122 documents")
        
        # Test semantic similarity between C122 documents
        if len(c122_docs['embeddings']) >= 2:
            emb1 = np.array(c122_docs['embeddings'][0])
            emb2 = np.array(c122_docs['embeddings'][1])
            
            # Calculate cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            cosine_sim = dot_product / (norm1 * norm2)
            
            print(f"Cosine similarity between C122 documents: {cosine_sim:.4f}")
            print(f"  Doc 1: {c122_docs['documents'][0][:100]}...")
            print(f"  Doc 2: {c122_docs['documents'][1][:100]}...")
            
    # Test query embedding vs document embedding directly
    print("\n🎯 Direct Embedding Comparison:")
    query_text = "hospital admission assessment"
    
    # Find C122 document
    c122_result = collection.get(
        where={"fee_code": "C122"},
        include=["documents", "embeddings"],
        limit=1
    )
    
    if len(c122_result['embeddings']) > 0:
        # Generate fresh query embedding
        query_emb = openai_client.embeddings.create(
            input=[query_text],
            model="text-embedding-3-small"  
        ).data[0].embedding
        
        doc_emb = c122_result['embeddings'][0]
        
        # Calculate cosine similarity
        dot_product = np.dot(query_emb, doc_emb)
        norm1 = np.linalg.norm(query_emb)
        norm2 = np.linalg.norm(doc_emb)
        cosine_sim = dot_product / (norm1 * norm2)
        
        print(f"Direct cosine similarity between query and C122: {cosine_sim:.4f}")
        print(f"Query: '{query_text}'")
        print(f"C122 Doc: {c122_result['documents'][0][:100]}...")
        
        # ChromaDB uses L2 distance, convert to similarity
        # For normalized vectors: L2 distance = sqrt(2 * (1 - cosine_similarity))  
        expected_l2_distance = np.sqrt(2 * (1 - cosine_sim))
        chromadb_similarity = 1 - expected_l2_distance
        print(f"Expected ChromaDB similarity: {chromadb_similarity:.4f}")

if __name__ == "__main__":
    investigate_embeddings()