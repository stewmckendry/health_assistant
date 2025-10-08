#!/usr/bin/env python3
"""Analyze what boilerplate content looks like in the collection."""
import chromadb
from collections import Counter

client = chromadb.PersistentClient(path='data/dr_opa_agent/chroma')
collection = client.get_collection('opa_cep_corpus')

# Get all chunks
results = collection.get(
    limit=collection.count(),
    include=['metadatas', 'documents']
)

print("="*80)
print("BOILERPLATE ANALYSIS")
print("="*80)

# Identify boilerplate by section title
boilerplate_keywords = ['reference', 'acknowledgment', 'acknowledgement', 'legal', 'permission']

boilerplate_chunks = []
content_chunks = []

for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
    section = metadata.get('section_title', '').lower()
    is_boilerplate = any(kw in section for kw in boilerplate_keywords)

    if is_boilerplate:
        boilerplate_chunks.append({
            'id': results['ids'][i],
            'section': metadata.get('section_title', 'N/A'),
            'tool': metadata.get('title', 'N/A'),
            'doc': doc,
            'words': len(doc.split())
        })
    else:
        content_chunks.append({
            'section': metadata.get('section_title', 'N/A'),
            'words': len(doc.split())
        })

print(f"\nTotal chunks: {len(results['documents'])}")
print(f"Boilerplate: {len(boilerplate_chunks)} ({len(boilerplate_chunks)/len(results['documents'])*100:.1f}%)")
print(f"Content: {len(content_chunks)} ({len(content_chunks)/len(results['documents'])*100:.1f}%)")

# Analyze boilerplate sections
print(f"\n{'='*80}")
print("BOILERPLATE SECTION TYPES")
print('='*80)

section_counts = Counter(chunk['section'] for chunk in boilerplate_chunks)
for section, count in section_counts.most_common(10):
    print(f"  {section:50} {count:3d} chunks")

# Show sample boilerplate content
print(f"\n{'='*80}")
print("SAMPLE BOILERPLATE CONTENT")
print('='*80)

print("\n1. REFERENCES SECTION:")
print("-"*80)
ref_sample = [c for c in boilerplate_chunks if 'reference' in c['section'].lower()]
if ref_sample:
    sample = ref_sample[0]
    print(f"Tool: {sample['tool']}")
    print(f"Words: {sample['words']}")
    print(f"Content preview:\n{sample['doc'][:500]}...")

print("\n2. ACKNOWLEDGMENTS SECTION:")
print("-"*80)
ack_sample = [c for c in boilerplate_chunks if 'acknowledgment' in c['section'].lower()]
if ack_sample:
    sample = ack_sample[0]
    print(f"Tool: {sample['tool']}")
    print(f"Words: {sample['words']}")
    print(f"Content preview:\n{sample['doc'][:500]}...")

# Check if references contain useful info
print(f"\n{'='*80}")
print("BOILERPLATE VALUE ASSESSMENT")
print('='*80)

print("\nReferences sections:")
print("  - Contain academic citations (authors, journals, DOIs)")
print("  - May include evidence source URLs")
print("  - NOT directly useful for answering clinical queries")
print("  - But could be useful for 'what evidence supports X?'")

print("\nAcknowledgments/Legal sections:")
print("  - Standard disclaimer text (appears in all tools)")
print("  - Development methodology")
print("  - Funding/collaboration info")
print("  - NOT useful for clinical queries")

# Compare to content sections
print(f"\n{'='*80}")
print("CONTENT SECTION SAMPLES")
print('='*80)

content_sections = Counter(chunk['section'] for chunk in content_chunks)
print("\nTop 10 content sections:")
for section, count in content_sections.most_common(10):
    print(f"  {section:50} {count:3d} chunks")

# Sample clinical content
clinical_samples = [c for c in content_chunks if any(kw in c['section'].lower()
                    for kw in ['diagnos', 'treatment', 'management', 'screening', 'assessment'])]

if clinical_samples:
    print(f"\nSample clinical content section:")
    sample_idx = min(10, len(results['documents'])-1)
    for i, (doc, metadata) in enumerate(zip(results['documents'][:50], results['metadatas'][:50])):
        section = metadata.get('section_title', '')
        if any(kw in section.lower() for kw in ['diagnos', 'treatment', 'management']):
            print(f"\nSection: {section}")
            print(f"Tool: {metadata.get('title', 'N/A')}")
            print(f"Words: {len(doc.split())}")
            print(f"Content preview:\n{doc[:400]}...")
            break

print(f"\n{'='*80}")
