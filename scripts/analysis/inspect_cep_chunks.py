#!/usr/bin/env python3
"""Deep inspection of CEP collection chunks to understand retrieval issues."""
import chromadb
import json
from collections import Counter

client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
collection = client.get_collection(name="opa_cep_corpus")

print(f"\n{'='*80}")
print(f"CEP CORPUS DEEP INSPECTION")
print(f"{'='*80}\n")

# Get all chunks
results = collection.get(
    limit=collection.count(),
    include=['metadatas', 'documents']
)

print(f"Total chunks: {collection.count()}\n")

# Analyze chunk types
chunk_types = Counter()
doc_types = Counter()
section_titles = Counter()
tool_names = Counter()

for i, metadata in enumerate(results['metadatas']):
    chunk_type = metadata.get('chunk_type', 'MISSING')
    doc_type = metadata.get('document_type', 'MISSING')
    section_title = metadata.get('section_title', 'MISSING')
    tool_name = metadata.get('title', 'MISSING')

    chunk_types[chunk_type] += 1
    doc_types[doc_type] += 1
    section_titles[section_title] += 1
    tool_names[tool_name] += 1

print("CHUNK TYPE DISTRIBUTION:")
for ct, count in chunk_types.most_common():
    print(f"  {ct}: {count} chunks ({count/len(results['metadatas'])*100:.1f}%)")

print("\n\nDOCUMENT TYPE DISTRIBUTION:")
for dt, count in doc_types.most_common():
    print(f"  {dt}: {count} chunks ({count/len(results['metadatas'])*100:.1f}%)")

print("\n\nTOP 20 SECTION TITLES:")
for title, count in section_titles.most_common(20):
    print(f"  {title}: {count} chunks")

print("\n\nTOOL NAME DISTRIBUTION (Top 15):")
for name, count in tool_names.most_common(15):
    print(f"  {name}: {count} chunks")

# Check for boilerplate
print("\n\nBOILERPLATE ANALYSIS:")
boilerplate_keywords = [
    'acknowledgment', 'acknowledgement', 'legal', 'permission to use',
    'references', 'in collaboration with', 'centre for effective practice'
]
boilerplate_count = 0
for i, (metadata, doc) in enumerate(zip(results['metadatas'], results['documents'])):
    section_title = metadata.get('section_title', '').lower()
    doc_lower = doc[:200].lower()  # First 200 chars

    is_boilerplate = any(keyword in section_title for keyword in boilerplate_keywords)
    if is_boilerplate:
        boilerplate_count += 1

print(f"  Total boilerplate chunks: {boilerplate_count} ({boilerplate_count/len(results['metadatas'])*100:.1f}%)")

# Check diabetes-related chunks
print("\n\nDIABETES-RELATED CHUNKS:")
diabetes_keywords = ['diabetes', 'diabetic', 'glycemic', 'blood glucose', 'hba1c']
diabetes_chunks = []
for i, (metadata, doc) in enumerate(zip(results['metadatas'], results['documents'])):
    doc_lower = doc.lower()
    title_lower = metadata.get('title', '').lower()
    section_lower = metadata.get('section_title', '').lower()

    if any(keyword in doc_lower or keyword in title_lower or keyword in section_lower
           for keyword in diabetes_keywords):
        diabetes_chunks.append({
            'id': results['ids'][i],
            'title': metadata.get('title', 'N/A'),
            'section': metadata.get('section_title', 'N/A'),
            'chunk_type': metadata.get('chunk_type', 'N/A'),
            'preview': doc[:150]
        })

print(f"  Found {len(diabetes_chunks)} diabetes-related chunks")
print("\n  Sample diabetes chunks:")
for chunk in diabetes_chunks[:5]:
    print(f"\n  - ID: {chunk['id']}")
    print(f"    Tool: {chunk['title']}")
    print(f"    Section: {chunk['section']}")
    print(f"    Type: {chunk['chunk_type']}")
    print(f"    Preview: {chunk['preview'][:100]}...")

# Check cardiovascular-related chunks
print("\n\nCARDIOVASCULAR-RELATED CHUNKS:")
cv_keywords = ['cardiovascular', 'cardiac', 'heart', 'cv risk', 'framingham']
cv_chunks = []
for i, (metadata, doc) in enumerate(zip(results['metadatas'], results['documents'])):
    doc_lower = doc.lower()
    title_lower = metadata.get('title', '').lower()
    section_lower = metadata.get('section_title', '').lower()

    if any(keyword in doc_lower or keyword in title_lower or keyword in section_lower
           for keyword in cv_keywords):
        cv_chunks.append({
            'id': results['ids'][i],
            'title': metadata.get('title', 'N/A'),
            'section': metadata.get('section_title', 'N/A'),
            'chunk_type': metadata.get('chunk_type', 'N/A'),
            'preview': doc[:150]
        })

print(f"  Found {len(cv_chunks)} cardiovascular-related chunks")
print("\n  Sample CV chunks:")
for chunk in cv_chunks[:5]:
    print(f"\n  - ID: {chunk['id']}")
    print(f"    Tool: {chunk['title']}")
    print(f"    Section: {chunk['section']}")
    print(f"    Type: {chunk['chunk_type']}")
    print(f"    Preview: {chunk['preview'][:100]}...")

# Check parent vs child content length
print("\n\nPARENT VS CHILD CONTENT LENGTH:")
parent_lengths = []
child_lengths = []
for i, (metadata, doc) in enumerate(zip(results['metadatas'], results['documents'])):
    chunk_type = metadata.get('chunk_type', '')
    if chunk_type == 'parent':
        parent_lengths.append(len(doc))
    elif chunk_type == 'child':
        child_lengths.append(len(doc))

if parent_lengths:
    print(f"  Parent chunks: avg={sum(parent_lengths)/len(parent_lengths):.0f} chars, "
          f"min={min(parent_lengths)}, max={max(parent_lengths)}")
if child_lengths:
    print(f"  Child chunks: avg={sum(child_lengths)/len(child_lengths):.0f} chars, "
          f"min={min(child_lengths)}, max={max(child_lengths)}")

print(f"\n{'='*80}\n")
