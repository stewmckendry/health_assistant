#!/usr/bin/env python3
"""
Extract unique CEP tools from collection and build tool catalog.
Uses both ChromaDB metadata and raw HTML filenames for comprehensive catalog.
"""

import chromadb
import json
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import re

load_dotenv()

# Initialize ChromaDB
client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
collection = client.get_collection("opa_cep_corpus")

print(f"Collection: {collection.name}")
print(f"Total chunks: {collection.count()}")

# Get all chunks with metadata
all_chunks = collection.get(include=['metadatas'])

# Extract unique tools from collection
tools = defaultdict(lambda: {
    'chunk_count': 0,
    'urls': set(),
    'topics': set(),
    'sections': [],
    'source_file': None
})

for i, metadata in enumerate(all_chunks['metadatas']):
    title = metadata.get('title', 'Unknown')
    url = metadata.get('source_url', '')
    topics = metadata.get('topics', '').split(',')
    section = metadata.get('section_title', '')

    tools[title]['chunk_count'] += 1
    if url:
        tools[title]['urls'].add(url)
        # Extract filename from URL
        if '/tool/' in url:
            filename = url.split('/tool/')[-1].rstrip('/')
            tools[title]['source_file'] = filename
    for topic in topics:
        if topic.strip():
            tools[title]['topics'].add(topic.strip())
    if section:
        tools[title]['sections'].append(section)

# Also scan raw HTML files to ensure we don't miss any tools
raw_cep_dir = Path('data/dr_opa_agent/raw/cep')
if raw_cep_dir.exists():
    html_files = list(raw_cep_dir.glob('*.html'))
    print(f"\nFound {len(html_files)} HTML files in raw data")

    # Create reverse lookup from source_file to tool title
    source_file_to_title = {}
    for title, data in tools.items():
        if data['source_file']:
            source_file_to_title[data['source_file']] = title

print(f"\nFound {len(tools)} unique tools")

# Build catalog
catalog = []
for tool_name, data in sorted(tools.items()):
    # Generate tool_id from source_file if available, otherwise from title
    if data.get('source_file'):
        tool_id = data['source_file'].replace('-', '_')
    else:
        tool_id = tool_name.lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '').replace(':', '')
        # Remove common prefixes
        for prefix in ['management_of_', 'managing_']:
            if tool_id.startswith(prefix):
                tool_id = tool_id[len(prefix):]

    # Extract category from topics
    topic_list = list(data['topics'])
    primary_topic = topic_list[0] if topic_list else 'general'

    # Map topics to clinical domains
    domain_mapping = {
        'pain_management': 'pain_management',
        'mental_health': 'mental_health',
        'neurology': 'neurology',
        'cardiovascular': 'cardiovascular',
        'substance_use': 'substance_use',
        'diabetes': 'endocrine',
        'respiratory': 'respiratory',
        'infectious_disease': 'infectious_disease',
        'social_care': 'social_care',
        'screening': 'prevention'
    }

    clinical_domain = domain_mapping.get(primary_topic, 'general')

    # Extract conditions from tool name
    conditions = []
    condition_keywords = {
        'chronic pain': 'chronic pain',
        'insomnia': 'insomnia',
        'dementia': 'dementia',
        'neck': 'neck pain',
        'headache': 'headache',
        'diabetes': 'diabetes',
        'heart failure': 'heart failure',
        'depression': 'depression',
        'anxiety': 'anxiety',
        'opioid': 'opioid use',
        'obesity': 'obesity',
        'menopause': 'menopause'
    }

    tool_name_lower = tool_name.lower()
    for keyword, condition in condition_keywords.items():
        if keyword in tool_name_lower:
            conditions.append(condition)

    # Extract capabilities from sections
    capabilities = set()
    for section in data['sections'][:10]:  # Sample first 10 sections
        section_lower = section.lower()
        if 'assessment' in section_lower or 'screening' in section_lower:
            capabilities.add('assessment')
        if 'treatment' in section_lower or 'management' in section_lower:
            capabilities.add('treatment')
        if 'algorithm' in section_lower or 'pathway' in section_lower:
            capabilities.add('algorithms')
        if 'pharmacolog' in section_lower:
            capabilities.add('pharmacotherapy')
        if 'referral' in section_lower:
            capabilities.add('referral_guidance')

    catalog_entry = {
        'tool_id': tool_id,
        'tool_name': tool_name,
        'aliases': [tool_name],
        'clinical_domain': clinical_domain,
        'conditions': conditions if conditions else ['general'],
        'capabilities': list(capabilities) if capabilities else ['clinical_guidance'],
        'chunk_count': data['chunk_count'],
        'source_url': list(data['urls'])[0] if data['urls'] else '',
        'topics': list(data['topics'])
    }

    catalog.append(catalog_entry)

# Sort by chunk count (most common first)
catalog = sorted(catalog, key=lambda x: x['chunk_count'], reverse=True)

# Save catalog
output_file = Path('src/ai_agents/dr_opa_agent/dr_opa_mcp/cep_tool_catalog.json')
with open(output_file, 'w') as f:
    json.dump(catalog, f, indent=2)

print(f"\n✅ Saved {len(catalog)} tools to {output_file}")

# Print summary
print("\n📊 Top 10 tools by chunk count:")
for tool in catalog[:10]:
    print(f"  {tool['tool_id']:40} | {tool['chunk_count']:3} chunks | {tool['clinical_domain']:20}")

print("\n📊 Tools by clinical domain:")
domains = defaultdict(int)
for tool in catalog:
    domains[tool['clinical_domain']] += 1

for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
    print(f"  {domain:20}: {count} tools")
