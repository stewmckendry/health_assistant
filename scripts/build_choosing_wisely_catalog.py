#!/usr/bin/env python3
"""
Build Choosing Wisely Specialty Catalog from ChromaDB metadata.

Extracts specialty-level metadata from the opa_choosing_wisely_corpus ChromaDB collection
to create a catalog for LLM-based specialty triage.

Input: ChromaDB collection (opa_choosing_wisely_corpus)
Output: data/dr_opa_agent/choosing_wisely_specialty_catalog.json

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


def extract_specialty_id_from_name(specialty_name: str) -> str:
    """
    Convert specialty name to ID.

    Examples:
        "Cardiology" -> "cardiology"
        "Family Medicine" -> "family_medicine"
        "Emergency Medicine" -> "emergency_medicine"
    """
    # Convert to lowercase with underscores
    specialty_id = specialty_name.lower().replace(' ', '_').replace('-', '_')
    return specialty_id


def infer_clinical_domain(specialty_name: str) -> str:
    """
    Infer clinical domain from specialty name.

    Domains:
    - primary_care: Family Medicine, General Practice
    - cardiovascular: Cardiology
    - surgical: General Surgery, Orthopedics, etc.
    - imaging: Radiology, Nuclear Medicine
    - emergency: Emergency Medicine
    - internal_medicine: subspecialties
    - mental_health: Psychiatry
    - pediatrics: Pediatrics
    - critical_care: Critical Care, ICU
    - oncology: Hematology, Oncology
    """
    specialty_lower = specialty_name.lower()

    # Primary care
    if any(kw in specialty_lower for kw in ['family', 'primary', 'general practice']):
        return 'primary_care'

    # Cardiovascular
    if any(kw in specialty_lower for kw in ['cardio', 'cardiovascular']):
        return 'cardiovascular'

    # Surgical
    if any(kw in specialty_lower for kw in ['surgery', 'surgical', 'orthopedic']):
        return 'surgical'

    # Imaging
    if any(kw in specialty_lower for kw in ['radiology', 'imaging', 'nuclear medicine']):
        return 'imaging'

    # Emergency
    if 'emergency' in specialty_lower:
        return 'emergency'

    # Critical care
    if any(kw in specialty_lower for kw in ['critical care', 'intensive care', 'icu']):
        return 'critical_care'

    # Mental health
    if any(kw in specialty_lower for kw in ['psychiatry', 'mental health']):
        return 'mental_health'

    # Pediatrics
    if 'pediatric' in specialty_lower or 'paediatric' in specialty_lower:
        return 'pediatrics'

    # Oncology
    if any(kw in specialty_lower for kw in ['oncology', 'hematology', 'cancer']):
        return 'oncology'

    # Internal medicine (default for medical subspecialties)
    if any(kw in specialty_lower for kw in ['medicine', 'endocrin', 'nephro', 'gastro', 'pulmon', 'rheumato']):
        return 'internal_medicine'

    return 'general'


def generate_aliases(specialty_name: str) -> List[str]:
    """
    Generate aliases for a specialty based on common variations.
    """
    aliases = []
    specialty_lower = specialty_name.lower()

    # Common variations
    alias_patterns = {
        'cardiology': ['cardiac', 'cardiovascular', 'heart'],
        'family medicine': ['family practice', 'primary care', 'GP', 'general practice'],
        'emergency medicine': ['emergency', 'ER', 'emergency department'],
        'radiology': ['imaging', 'diagnostic imaging'],
        'orthopedic': ['orthopedics', 'orthopaedics', 'bones', 'musculoskeletal'],
        'psychiatry': ['mental health', 'psychiatric'],
        'pediatric': ['pediatrics', 'paediatrics', 'children'],
        'anesthesiology': ['anesthesia', 'anaesthesiology'],
        'critical care': ['ICU', 'intensive care'],
        'gastroenterology': ['GI', 'digestive'],
        'nephrology': ['kidney', 'renal'],
        'endocrinology': ['diabetes', 'thyroid', 'hormones'],
        'neurology': ['neurological', 'brain', 'nervous system'],
        'oncology': ['cancer'],
        'hematology': ['blood'],
        'dermatology': ['skin'],
        'internal medicine': ['general medicine', 'hospitalist']
    }

    for key, variations in alias_patterns.items():
        if key in specialty_lower:
            aliases.extend(variations)

    # Remove duplicates and limit
    aliases = list(set(aliases))[:5]
    return aliases


def extract_common_scenarios_from_recommendations(
    collection,
    specialty_name: str,
    max_scenarios: int = 5
) -> List[str]:
    """
    Extract common clinical scenarios from recommendation titles.
    """
    # Get child chunks (recommendations) for this specialty
    results = collection.get(
        where={
            "$and": [
                {"specialty": specialty_name},
                {"chunk_type": "child"}
            ]
        },
        include=['documents', 'metadatas']
    )

    scenarios = []

    for doc, metadata in zip(results['documents'], results['metadatas']):
        # Extract first sentence or "Don't..." statement
        # Recommendations typically start with "Don't..."
        match = re.search(r"Don't ([^.!?]+)", doc, re.IGNORECASE)
        if match:
            scenario = match.group(1).strip()
            # Limit length
            if len(scenario) > 100:
                scenario = scenario[:97] + '...'
            scenarios.append(scenario)

        if len(scenarios) >= max_scenarios:
            break

    return scenarios


def extract_sample_recommendations(
    collection,
    specialty_name: str,
    max_samples: int = 2
) -> List[str]:
    """
    Extract sample recommendation titles for catalog.
    """
    # Get child chunks (recommendations) for this specialty
    results = collection.get(
        where={
            "$and": [
                {"specialty": specialty_name},
                {"chunk_type": "child"}
            ]
        },
        include=['documents', 'metadatas']
    )

    samples = []

    for doc in results['documents'][:max_samples]:
        # Extract first sentence
        first_sentence = doc.split('.')[0].strip()
        if len(first_sentence) > 150:
            first_sentence = first_sentence[:147] + '...'
        samples.append(first_sentence)

    return samples


def build_catalog(chroma_path: str = "data/dr_opa_agent/chroma") -> List[Dict]:
    """
    Build specialty catalog from ChromaDB.
    """
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("opa_choosing_wisely_corpus")

    print(f"Total chunks in collection: {collection.count()}")

    print("Extracting specialty metadata...")
    # Get all parent chunks (specialty overviews)
    parent_results = collection.get(
        where={"chunk_type": "parent"},
        include=['metadatas', 'documents']
    )

    print(f"Found {len(parent_results['ids'])} specialty overviews")

    # Build catalog entries
    catalog = []

    print("\nBuilding catalog entries...")
    for idx, (chunk_id, doc, metadata) in enumerate(zip(
        parent_results['ids'],
        parent_results['documents'],
        parent_results['metadatas']
    )):
        specialty_name = metadata.get('specialty', '')
        organization = metadata.get('organization', '')

        if not specialty_name:
            print(f"  Warning: Skipping chunk with no specialty: {chunk_id}")
            continue

        print(f"  {idx+1}. Processing: {specialty_name}")

        # Generate metadata
        specialty_id = extract_specialty_id_from_name(specialty_name)
        clinical_domain = infer_clinical_domain(specialty_name)
        aliases = generate_aliases(specialty_name)
        common_scenarios = extract_common_scenarios_from_recommendations(
            collection, specialty_name
        )
        sample_recommendations = extract_sample_recommendations(
            collection, specialty_name
        )

        # Get recommendation count
        recommendation_count = int(metadata.get('recommendation_count', 0))

        # Get source URL
        source_url = metadata.get('source_url', '')

        # Get has_methodology flag
        has_methodology = metadata.get('has_methodology', 'False') == 'True'

        # Get chunk IDs for this specialty
        all_chunks = collection.get(
            where={"specialty": specialty_name},
            include=['metadatas']
        )

        parent_chunks = [
            cid for cid, m in zip(all_chunks['ids'], all_chunks['metadatas'])
            if m.get('chunk_type') == 'parent'
        ]
        child_chunks = [
            cid for cid, m in zip(all_chunks['ids'], all_chunks['metadatas'])
            if m.get('chunk_type') == 'child'
        ]

        entry = {
            "specialty_id": specialty_id,
            "specialty_name": specialty_name,
            "aliases": aliases,
            "clinical_domain": clinical_domain,
            "organization": organization,
            "common_scenarios": common_scenarios,
            "recommendation_count": recommendation_count,
            "sample_recommendations": sample_recommendations,
            "has_methodology": has_methodology,
            "source_url": source_url,
            "chunk_ids": {
                "parent": parent_chunks,
                "children": child_chunks
            },
            "total_chunks": len(parent_chunks) + len(child_chunks)
        }

        catalog.append(entry)

    # Sort by specialty name
    catalog.sort(key=lambda x: x['specialty_name'])

    return catalog


def main():
    """Main execution."""
    print("="*60)
    print("Choosing Wisely Specialty Catalog Builder")
    print("="*60)
    print()

    # Build catalog
    catalog = build_catalog()

    # Save to file
    output_path = Path("data/dr_opa_agent/choosing_wisely_specialty_catalog.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print()
    print(f"Saving catalog to {output_path}...")

    with open(output_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"✓ Saved {len(catalog)} specialties to catalog")

    # Print summary statistics
    print()
    print("="*60)
    print("Catalog Summary")
    print("="*60)
    print(f"Total specialties: {len(catalog)}")

    # Count by clinical domain
    by_domain = defaultdict(int)
    for entry in catalog:
        by_domain[entry['clinical_domain']] += 1

    print(f"\nBy clinical domain:")
    for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count}")

    # Total recommendations
    total_recommendations = sum(entry['recommendation_count'] for entry in catalog)
    print(f"\nTotal recommendations: {total_recommendations}")

    avg_recommendations = total_recommendations / len(catalog) if catalog else 0
    print(f"Average recommendations per specialty: {avg_recommendations:.1f}")

    # Total chunks
    total_chunks = sum(entry['total_chunks'] for entry in catalog)
    print(f"Total chunks: {total_chunks}")

    # Print sample entries
    print()
    print("Sample catalog entries:")
    for i, entry in enumerate(catalog[:3]):
        print(f"\n{i+1}. {entry['specialty_name']}")
        print(f"   ID: {entry['specialty_id']}")
        print(f"   Organization: {entry['organization']}")
        print(f"   Domain: {entry['clinical_domain']}")
        print(f"   Aliases: {', '.join(entry['aliases'][:3])}")
        print(f"   Recommendations: {entry['recommendation_count']}")
        print(f"   Total chunks: {entry['total_chunks']} (parent: {len(entry['chunk_ids']['parent'])}, children: {len(entry['chunk_ids']['children'])})")
        if entry['common_scenarios']:
            print(f"   Common scenarios: {len(entry['common_scenarios'])} extracted")
            print(f"     - {entry['common_scenarios'][0][:80]}...")
        if entry['sample_recommendations']:
            print(f"   Sample recommendation:")
            print(f"     - {entry['sample_recommendations'][0][:80]}...")

    print()
    print("="*60)
    print("✓ Catalog build complete!")
    print("="*60)


if __name__ == "__main__":
    main()
