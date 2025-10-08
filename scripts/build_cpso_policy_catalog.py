#!/usr/bin/env python3
"""
Build CPSO Policy Catalog from ChromaDB metadata.

Extracts policy-level metadata from the opa_cpso_corpus ChromaDB collection
to create a catalog for LLM-based policy triage.

Input: ChromaDB collection (opa_cpso_corpus)
Output: data/dr_opa_agent/cpso_policy_catalog.json

Author: AI Assistant
Date: 2025-10-07
"""

import chromadb
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set
import re
from datetime import datetime


def extract_policy_id_from_url(url: str) -> str:
    """
    Extract policy ID from CPSO URL.

    Examples:
        https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies/Virtual-Care
        -> virtual_care

        https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies/Consent-to-Treatment
        -> consent_to_treatment
    """
    # Get last part of URL path
    parts = url.rstrip('/').split('/')
    policy_slug = parts[-1] if parts else url

    # Convert to lowercase with underscores
    policy_id = policy_slug.lower().replace('-', '_')

    return policy_id


def infer_practice_domain(topics: Set[str]) -> str:
    """
    Infer practice domain from topics.

    Domains:
    - service_delivery: virtual_care, continuity_of_care
    - patient_interaction: consent, privacy, ending_relationship
    - prescribing_treatment: prescribing, medical_assistance_dying
    - professional_conduct: professional_misconduct, boundary_violations, social_media
    - administrative: billing, medical_records, advertising
    - delegation_supervision: delegation
    """
    domain_keywords = {
        'service_delivery': ['virtual_care', 'continuity_of_care'],
        'patient_interaction': ['consent', 'privacy', 'ending_relationship'],
        'prescribing_treatment': ['prescribing', 'medical_assistance_dying'],
        'professional_conduct': ['professional_misconduct', 'social_media', 'advertising'],
        'administrative': ['billing', 'medical_records'],
        'delegation_supervision': ['delegation']
    }

    # Score each domain
    domain_scores = defaultdict(int)
    for topic in topics:
        for domain, keywords in domain_keywords.items():
            if any(kw in topic for kw in keywords):
                domain_scores[domain] += 1

    # Return highest scoring domain, or 'general' if none
    if domain_scores:
        return max(domain_scores.items(), key=lambda x: x[1])[0]
    return 'general'


def extract_key_requirements_from_chunks(collection, url: str, max_requirements: int = 5) -> List[str]:
    """
    Extract key requirements from policy chunks by finding sentences with 'must'.
    """
    # Get all chunks for this policy
    results = collection.get(
        where={"source_url": url},
        include=['documents', 'metadatas']
    )

    requirements = []

    for doc, metadata in zip(results['documents'], results['metadatas']):
        # Only look at parent chunks (overviews)
        if metadata.get('chunk_type') != 'parent':
            continue

        # Find sentences with "must" (case-insensitive)
        sentences = re.split(r'[.!?]', doc)
        for sentence in sentences:
            if ' must ' in sentence.lower() and len(sentence.strip()) > 20:
                # Clean up the sentence
                req = sentence.strip()
                # Remove markdown formatting
                req = re.sub(r'\*\*', '', req)
                req = re.sub(r'\n+', ' ', req)
                # Limit length
                if len(req) > 150:
                    req = req[:147] + '...'
                requirements.append(req)

                if len(requirements) >= max_requirements:
                    break

        if len(requirements) >= max_requirements:
            break

    return requirements[:max_requirements]


def find_related_policies(
    policies_by_url: Dict,
    current_url: str,
    current_topics: Set[str],
    top_n: int = 3
) -> List[str]:
    """
    Find related policies by topic overlap.
    """
    if not current_topics:
        return []

    # Score other policies by topic overlap
    scores = []
    for url, data in policies_by_url.items():
        if url == current_url:
            continue

        other_topics = data['topics']
        overlap = len(current_topics.intersection(other_topics))

        if overlap > 0:
            scores.append((url, overlap))

    # Sort by overlap descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Return policy IDs of top N
    related_ids = [extract_policy_id_from_url(url) for url, _ in scores[:top_n]]
    return related_ids


def generate_aliases(title: str, topics: Set[str]) -> List[str]:
    """
    Generate aliases for a policy based on title and topics.
    """
    aliases = []

    # Add variations of title
    title_lower = title.lower()

    # Common variations
    alias_patterns = {
        'virtual care': ['telemedicine', 'telehealth', 'remote care'],
        'consent': ['informed consent', 'capacity assessment'],
        'prescribing': ['prescription', 'medication management', 'drug therapy'],
        'boundary violations': ['professional boundaries', 'sexual misconduct'],
        'medical records': ['documentation', 'charting', 'health records'],
        'ending': ['terminating', 'discontinuing care'],
        'advertising': ['marketing', 'promotion'],
        'delegation': ['supervised acts', 'controlled acts']
    }

    for key, variations in alias_patterns.items():
        if key in title_lower:
            aliases.extend(variations)

    # Add topic-based aliases
    topic_aliases = {
        'virtual_care': 'online consultations',
        'consent': 'patient authorization',
        'privacy': 'confidentiality',
        'prescribing': 'medication orders',
        'medical_records': 'patient charts'
    }

    for topic in topics:
        if topic in topic_aliases:
            aliases.append(topic_aliases[topic])

    # Remove duplicates and limit
    aliases = list(set(aliases))[:5]
    return aliases


def build_catalog(chroma_path: str = "data/dr_opa_agent/chroma") -> List[Dict]:
    """
    Build policy catalog from ChromaDB.
    """
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("opa_cpso_corpus")

    print("Extracting policy metadata...")
    results = collection.get(limit=1000, include=['metadatas'])

    # Group by source_url
    policies_by_url = defaultdict(lambda: {
        'title': None,
        'topics': set(),
        'policy_level': None,
        'effective_date': None,
        'chunk_count': 0,
        'parent_chunks': 0,
        'child_chunks': 0
    })

    for metadata in results['metadatas']:
        url = metadata.get('source_url', '')
        if not url:
            continue

        policy = policies_by_url[url]
        policy['chunk_count'] += 1

        chunk_type = metadata.get('chunk_type', 'unknown')
        if chunk_type == 'parent':
            policy['parent_chunks'] += 1
        elif chunk_type == 'child':
            policy['child_chunks'] += 1

        # Set attributes from first occurrence
        if not policy['title']:
            policy['title'] = metadata.get('title', '')
            policy['policy_level'] = metadata.get('policy_level', '')
            policy['effective_date'] = metadata.get('effective_date', '')

        # Accumulate topics
        topics_str = metadata.get('topics', '')
        if topics_str:
            policy['topics'].update(topics_str.split(','))

    print(f"Found {len(policies_by_url)} unique policies")

    # Build catalog entries
    catalog = []

    print("Building catalog entries...")
    for url, data in policies_by_url.items():
        policy_id = extract_policy_id_from_url(url)
        title = data['title']
        topics = data['topics']

        # Skip if no title
        if not title:
            print(f"  Warning: Skipping policy with no title: {url}")
            continue

        print(f"  Processing: {title}")

        # Generate metadata
        practice_domain = infer_practice_domain(topics)
        aliases = generate_aliases(title, topics)
        key_requirements = extract_key_requirements_from_chunks(collection, url)
        related_policies = find_related_policies(policies_by_url, url, topics)

        entry = {
            "policy_id": policy_id,
            "policy_title": title,
            "aliases": aliases,
            "practice_domain": practice_domain,
            "topics": sorted(list(topics)),
            "policy_level": data['policy_level'] or 'unknown',
            "key_requirements": key_requirements,
            "related_policies": related_policies,
            "chunk_count": data['chunk_count'],
            "parent_chunks": data['parent_chunks'],
            "child_chunks": data['child_chunks'],
            "effective_date": data['effective_date'] or None,
            "source_url": url
        }

        catalog.append(entry)

    # Sort by title
    catalog.sort(key=lambda x: x['policy_title'])

    return catalog


def main():
    """Main execution."""
    print("="*60)
    print("CPSO Policy Catalog Builder")
    print("="*60)
    print()

    # Build catalog
    catalog = build_catalog()

    # Save to file
    output_path = Path("data/dr_opa_agent/cpso_policy_catalog.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print()
    print(f"Saving catalog to {output_path}...")

    with open(output_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"✓ Saved {len(catalog)} policies to catalog")

    # Print summary statistics
    print()
    print("="*60)
    print("Catalog Summary")
    print("="*60)
    print(f"Total policies: {len(catalog)}")

    # Count by policy level
    by_level = defaultdict(int)
    for entry in catalog:
        by_level[entry['policy_level']] += 1

    print(f"\nBy policy level:")
    for level, count in sorted(by_level.items()):
        print(f"  {level}: {count}")

    # Count by practice domain
    by_domain = defaultdict(int)
    for entry in catalog:
        by_domain[entry['practice_domain']] += 1

    print(f"\nBy practice domain:")
    for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count}")

    # Print sample entries
    print()
    print("Sample catalog entries:")
    for i, entry in enumerate(catalog[:3]):
        print(f"\n{i+1}. {entry['policy_title']}")
        print(f"   ID: {entry['policy_id']}")
        print(f"   Level: {entry['policy_level']}")
        print(f"   Domain: {entry['practice_domain']}")
        print(f"   Topics: {', '.join(entry['topics'][:5])}")
        print(f"   Aliases: {', '.join(entry['aliases'][:3])}")
        print(f"   Chunks: {entry['chunk_count']} (parent: {entry['parent_chunks']}, child: {entry['child_chunks']})")
        if entry['key_requirements']:
            print(f"   Requirements: {len(entry['key_requirements'])} key requirements extracted")

    print()
    print("="*60)
    print("✓ Catalog build complete!")
    print("="*60)


if __name__ == "__main__":
    main()
