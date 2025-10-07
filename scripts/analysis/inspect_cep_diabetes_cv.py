#!/usr/bin/env python3
"""Check if CEP has diabetes screening or CV risk assessment tools."""
import chromadb

client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
collection = client.get_collection(name="opa_cep_corpus")

results = collection.get(
    limit=collection.count(),
    include=['metadatas', 'documents']
)

print(f"\n{'='*80}")
print("CHECKING FOR DIABETES & CV TOOLS IN CEP CORPUS")
print(f"{'='*80}\n")

# Get unique tool names
unique_tools = set()
for metadata in results['metadatas']:
    tool_name = metadata.get('title', '')
    if tool_name:
        unique_tools.add(tool_name)

print(f"Total unique tools: {len(unique_tools)}\n")

# Check for diabetes tools
print("DIABETES-RELATED TOOLS:")
diabetes_tools = [t for t in unique_tools if any(keyword in t.lower()
                  for keyword in ['diabetes', 'diabetic', 'glycemic'])]
if diabetes_tools:
    for tool in sorted(diabetes_tools):
        print(f"  ✓ {tool}")
else:
    print("  ❌ NO DIABETES-SPECIFIC TOOLS FOUND")

# Check for CV tools
print("\n\nCARDIOVASCULAR-RELATED TOOLS:")
cv_tools = [t for t in unique_tools if any(keyword in t.lower()
            for keyword in ['cardiovascular', 'cardiac', 'heart', 'cv'])]
if cv_tools:
    for tool in sorted(cv_tools):
        print(f"  ✓ {tool}")
else:
    print("  ❌ NO CV RISK ASSESSMENT TOOLS FOUND")

# Now let's look at the diabetes tools in detail
print("\n\n" + "="*80)
print("DETAILED INSPECTION: DIABETES TOOLS")
print("="*80)

for tool_name in sorted(diabetes_tools):
    print(f"\n\n📋 Tool: {tool_name}")
    print("-" * 80)

    # Get all chunks for this tool
    tool_chunks = []
    for i, metadata in enumerate(results['metadatas']):
        if metadata.get('title', '') == tool_name:
            tool_chunks.append({
                'id': results['ids'][i],
                'section': metadata.get('section_title', 'N/A'),
                'chunk_type': metadata.get('chunk_type', 'N/A'),
                'doc': results['documents'][i]
            })

    print(f"Total chunks: {len(tool_chunks)}")

    # Show sections
    sections = {}
    for chunk in tool_chunks:
        section = chunk['section']
        if section not in sections:
            sections[section] = []
        sections[section].append(chunk)

    print(f"\nSections ({len(sections)}):")
    for section, chunks in sorted(sections.items()):
        print(f"  • {section} ({len(chunks)} chunks)")

    # Look for screening-related sections
    screening_sections = [s for s in sections.keys()
                         if any(keyword in s.lower()
                         for keyword in ['screen', 'diagnosis', 'assessment', 'risk'])]

    if screening_sections:
        print("\n🔍 Screening/Diagnosis sections found:")
        for section in screening_sections:
            print(f"\n  Section: {section}")
            for chunk in sections[section][:2]:  # Show first 2 chunks
                print(f"  Type: {chunk['chunk_type']}")
                print(f"  Preview: {chunk['doc'][:200]}...")
                print()

# Same for CV tools
print("\n\n" + "="*80)
print("DETAILED INSPECTION: CARDIOVASCULAR/HEART TOOLS")
print("="*80)

for tool_name in sorted(cv_tools):
    print(f"\n\n📋 Tool: {tool_name}")
    print("-" * 80)

    # Get all chunks for this tool
    tool_chunks = []
    for i, metadata in enumerate(results['metadatas']):
        if metadata.get('title', '') == tool_name:
            tool_chunks.append({
                'id': results['ids'][i],
                'section': metadata.get('section_title', 'N/A'),
                'chunk_type': metadata.get('chunk_type', 'N/A'),
                'doc': results['documents'][i]
            })

    print(f"Total chunks: {len(tool_chunks)}")

    # Show sections
    sections = {}
    for chunk in tool_chunks:
        section = chunk['section']
        if section not in sections:
            sections[section] = []
        sections[section].append(chunk)

    print(f"\nSections ({len(sections)}):")
    for section, chunks in sorted(sections.items()):
        print(f"  • {section} ({len(chunks)} chunks)")

print(f"\n{'='*80}\n")
