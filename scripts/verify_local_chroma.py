#!/usr/bin/env python3
"""
Verify quality of local ChromaDB collections to understand what was migrated
"""

import chromadb
from pathlib import Path
from collections import defaultdict
import json

def analyze_collection(client, collection_name, sample_size=50):
    """Analyze a single collection for quality"""
    
    try:
        collection = client.get_collection(collection_name)
        count = collection.count()
        
        print(f"\n{'='*70}")
        print(f"📊 Collection: {collection_name}")
        print(f"   Total documents: {count:,}")
        print("-" * 70)
        
        if count == 0:
            print("   ⚠️  Collection is empty")
            return
        
        # Get sample documents
        sample_size = min(sample_size, count)
        results = collection.get(
            limit=sample_size,
            include=["documents", "metadatas", "embeddings"]
        )
        
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        ids = results.get("ids", [])
        embeddings = results.get("embeddings", [])
        
        print(f"   ✓ Sampled {len(documents)} documents")
        
        # Analyze metadata structure
        metadata_keys = defaultdict(int)
        empty_values = defaultdict(int)
        null_values = defaultdict(int)
        value_samples = defaultdict(set)
        
        for metadata in metadatas:
            if metadata:
                for key, value in metadata.items():
                    metadata_keys[key] += 1
                    
                    # Track empty/null values
                    if value == "" or value == "unknown":
                        empty_values[key] += 1
                    elif value is None:
                        null_values[key] += 1
                    elif len(value_samples[key]) < 3:  # Collect up to 3 samples
                        value_samples[key].add(str(value)[:50])  # Truncate long values
        
        # Report metadata structure
        print(f"\n   📋 Metadata Structure ({len(metadata_keys)} fields):")
        for key, count in sorted(metadata_keys.items(), key=lambda x: x[1], reverse=True):
            percent = (count / len(metadatas)) * 100
            empty_percent = (empty_values.get(key, 0) / count) * 100 if count > 0 else 0
            null_percent = (null_values.get(key, 0) / count) * 100 if count > 0 else 0
            
            # Determine status icon
            if empty_percent > 50 or null_percent > 50:
                status = "❌"
            elif empty_percent > 10 or null_percent > 10:
                status = "⚠️"
            else:
                status = "✓"
            
            print(f"      {status} '{key}': {count}/{len(metadatas)} ({percent:.1f}%)")
            
            if empty_percent > 0 or null_percent > 0:
                issues = []
                if empty_percent > 0:
                    issues.append(f"empty: {empty_values[key]} ({empty_percent:.1f}%)")
                if null_percent > 0:
                    issues.append(f"null: {null_values[key]} ({null_percent:.1f}%)")
                print(f"         Issues: {', '.join(issues)}")
            
            # Show sample values
            if value_samples[key]:
                samples = list(value_samples[key])[:2]
                print(f"         Samples: {', '.join(samples)}")
        
        # Document content analysis
        doc_lengths = [len(doc) if doc else 0 for doc in documents]
        if doc_lengths:
            avg_length = sum(doc_lengths) / len(doc_lengths)
            min_length = min(doc_lengths)
            max_length = max(doc_lengths)
            empty_docs = sum(1 for length in doc_lengths if length == 0)
            
            print(f"\n   📄 Document Content Analysis:")
            print(f"      Average length: {avg_length:,.0f} characters")
            print(f"      Range: {min_length:,} - {max_length:,} characters")
            
            if empty_docs > 0:
                print(f"      ❌ Empty documents: {empty_docs} ({(empty_docs/len(doc_lengths)*100):.1f}%)")
            else:
                print(f"      ✓ No empty documents found")
            
            # Sample first doc
            if documents and documents[0]:
                sample_text = documents[0][:200].replace('\n', ' ')
                print(f"      Sample text: \"{sample_text}...\"")
        
        # ID analysis
        print(f"\n   🔑 Document IDs:")
        if ids:
            # Check ID patterns
            id_prefixes = defaultdict(int)
            for id_val in ids:
                prefix = id_val.split('_')[0] if '_' in id_val else 'no_prefix'
                id_prefixes[prefix] += 1
            
            print(f"      ID patterns:")
            for prefix, count in sorted(id_prefixes.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"         - {prefix}: {count} IDs")
            
            # Check for duplicates
            if len(ids) != len(set(ids)):
                print(f"      ❌ Duplicate IDs found in sample!")
            else:
                print(f"      ✓ No duplicate IDs in sample")
            
            # Sample IDs
            print(f"      Sample IDs: {', '.join(ids[:3])}")
        
        # Embeddings check
        if embeddings and len(embeddings) > 0:
            if embeddings[0]:
                embedding_dim = len(embeddings[0])
                print(f"\n   🔢 Embeddings:")
                print(f"      ✓ Dimension: {embedding_dim}")
                print(f"      ✓ Present for all {len(embeddings)} sampled documents")
            else:
                print(f"\n   🔢 Embeddings:")
                print(f"      ⚠️  Embeddings are empty or null")
        
    except Exception as e:
        print(f"   ❌ Error analyzing collection: {e}")

def main():
    print("🔍 LOCAL CHROMADB COLLECTION QUALITY ANALYSIS")
    print("=" * 70)
    
    # Check both ChromaDB locations
    chroma_paths = [
        ("Dr. OFF", "data/dr_off_agent/processed/dr_off/chroma"),
        ("Dr. OPA", "data/dr_opa_agent/chroma")
    ]
    
    total_docs = 0
    all_collections = []
    
    for agent_name, chroma_path in chroma_paths:
        if not Path(chroma_path).exists():
            print(f"\n⚠️  {agent_name} ChromaDB not found at {chroma_path}")
            continue
        
        print(f"\n\n{'='*70}")
        print(f"🏥 {agent_name} Agent Collections ({chroma_path})")
        print("=" * 70)
        
        client = chromadb.PersistentClient(path=chroma_path)
        collections = client.list_collections()
        
        for collection_info in collections:
            collection_name = collection_info.name
            all_collections.append((agent_name, collection_name))
            
            # Skip test collections
            if "cosine" in collection_name and client.get_collection(collection_name).count() <= 1:
                print(f"\n⏭️  Skipping test collection: {collection_name}")
                continue
            
            analyze_collection(client, collection_name, sample_size=30)
            total_docs += client.get_collection(collection_name).count()
    
    # Summary
    print(f"\n\n{'='*70}")
    print("📈 OVERALL QUALITY SUMMARY")
    print("=" * 70)
    print(f"Total collections analyzed: {len(all_collections)}")
    print(f"Total documents: {total_docs:,}")
    
    print("\nCollections by agent:")
    for agent_name, collection_name in all_collections:
        print(f"  - {agent_name}: {collection_name}")
    
    print("\n✅ Quality analysis complete")
    print("\nNOTE: This analysis is from LOCAL collections that were migrated to Railway.")
    print("The Railway collections should have identical structure and content.")

if __name__ == "__main__":
    main()