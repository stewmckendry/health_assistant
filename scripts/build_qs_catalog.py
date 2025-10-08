#!/usr/bin/env python3
"""
Build Ontario Health Quality Standards Catalog from ChromaDB metadata.

Extracts standard-level metadata from the opa_quality_standards_corpus ChromaDB collection
to create a catalog for LLM-based standard triage.

Input: ChromaDB collection (opa_quality_standards_corpus)
Output: data/dr_opa_agent/qs_catalog.json

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


def extract_standard_id_from_filename(filename: str) -> str:
    """
    Extract standard ID from PDF filename.

    Examples:
        qs-alcohol-use-disorder-quality-standard-en.pdf
        -> alcohol_use_disorder

        qs-chronic-obstructive-pulmonary-disease-quality-standard-2023-en.pdf
        -> copd
    """
    # Remove path and extension
    name = Path(filename).stem

    # Remove 'qs-' prefix
    if name.startswith('qs-'):
        name = name[3:]

    # Remove '-quality-standard' suffix
    name = name.replace('-quality-standard', '')

    # Remove year and language suffixes
    name = re.sub(r'-\d{4}', '', name)  # Remove year like -2023
    name = name.replace('-en', '')  # Remove language

    # Convert to lowercase with underscores
    standard_id = name.replace('-', '_')

    # Map common abbreviations
    abbreviations = {
        'chronic_obstructive_pulmonary_disease': 'copd',
        'prediabetes_and_type_2_diabetes': 'diabetes',
        'obsessive_compulsive_disorder': 'ocd',
        'low_back_pain': 'lbp',
        'heavy_menstrual_bleeding': 'hmb',
        'behavioural_symptoms_of_dementia': 'dementia_behavioural',
        'dementia_community': 'dementia_community',
    }

    return abbreviations.get(standard_id, standard_id)


def infer_clinical_domain(condition: str, statement_titles: List[str]) -> str:
    """
    Infer clinical domain from condition and statement titles.

    Domains:
    - mental_health: depression, anxiety, schizophrenia, ocd, eating disorders
    - respiratory: copd, asthma
    - neurology_cognitive: dementia, delirium, headache
    - endocrine_metabolic: diabetes, thyroid
    - cardiovascular: heart failure, hypertension
    - musculoskeletal: osteoarthritis, low back pain, hip fracture
    - womens_health: pregnancy, menstrual, menopause
    - oncology: cancer-related
    - palliative_care: palliative, end of life
    - general: everything else
    """
    domain_keywords = {
        'mental_health': ['depression', 'anxiety', 'schizophrenia', 'ocd', 'psychosis',
                         'eating disorder', 'insomnia', 'alcohol', 'opioid'],
        'respiratory': ['copd', 'asthma', 'pulmonary'],
        'neurology_cognitive': ['dementia', 'delirium', 'headache', 'stroke'],
        'endocrine_metabolic': ['diabetes', 'thyroid', 'prediabetes'],
        'cardiovascular': ['heart failure', 'hypertension', 'cardiac'],
        'musculoskeletal': ['osteoarthritis', 'back pain', 'hip fracture', 'spine'],
        'womens_health': ['pregnancy', 'menstrual', 'menopause', 'obstetric', 'caesarean'],
        'hematology': ['sickle cell', 'blood'],
        'dermatology': ['ulcer', 'wound', 'pressure injur'],
        'palliative_care': ['palliative', 'end of life'],
        'transitions_care': ['transition', 'hospital to home']
    }

    # Check condition
    condition_lower = condition.lower()
    for domain, keywords in domain_keywords.items():
        if any(kw in condition_lower for kw in keywords):
            return domain

    # Check statement titles
    all_titles = ' '.join(statement_titles).lower()
    for domain, keywords in domain_keywords.items():
        if any(kw in all_titles for kw in keywords):
            return domain

    return 'general'


def extract_care_focus_from_statements(statement_titles: List[str]) -> List[str]:
    """
    Extract care focus areas from statement titles.
    """
    care_focus = set()

    focus_keywords = {
        'screening': ['screen', 'assess', 'identif'],
        'diagnosis': ['diagnos', 'confirm'],
        'treatment': ['treatment', 'therap', 'intervention', 'medication'],
        'management': ['manag', 'care plan', 'monitor'],
        'prevention': ['prevent', 'reduc risk'],
        'education': ['educat', 'information', 'self-management'],
        'rehabilitation': ['rehabilitation', 'exercise'],
        'palliative': ['palliat', 'symptom control', 'end of life'],
        'transitions': ['transition', 'continuity', 'follow']
    }

    all_titles = ' '.join(statement_titles).lower()
    for focus, keywords in focus_keywords.items():
        if any(kw in all_titles for kw in keywords):
            care_focus.add(focus)

    return sorted(list(care_focus)) if care_focus else ['clinical_care']


def generate_aliases(title: str, condition: str) -> List[str]:
    """
    Generate aliases for a quality standard based on title and condition.
    """
    aliases = []

    # Add condition variations
    condition_lower = condition.lower()

    # Common variations
    alias_patterns = {
        'diabetes': ['T2DM', 'type 2 diabetes', 'prediabetes', 'glycemic control'],
        'copd': ['chronic obstructive pulmonary disease', 'chronic bronchitis', 'emphysema'],
        'asthma': ['bronchial asthma', 'reactive airway'],
        'depression': ['major depressive disorder', 'MDD', 'depressive illness'],
        'anxiety': ['anxiety disorder', 'GAD', 'generalized anxiety'],
        'schizophrenia': ['psychotic disorder', 'psychosis'],
        'heart failure': ['CHF', 'congestive heart failure', 'cardiac failure'],
        'dementia': ['cognitive impairment', 'alzheimer', 'memory disorder'],
        'palliative': ['end of life', 'EOL', 'comfort care'],
        'hip fracture': ['femoral fracture', 'hip break'],
        'osteoarthritis': ['OA', 'degenerative joint disease', 'arthritis'],
        'opioid': ['opioid use disorder', 'OUD', 'opioid addiction'],
        'low back pain': ['LBP', 'lumbar pain', 'back pain'],
        'hypertension': ['high blood pressure', 'HTN']
    }

    for key, variations in alias_patterns.items():
        if key in condition_lower or key in title.lower():
            aliases.extend(variations)

    # Remove duplicates and limit
    aliases = list(set(aliases))[:5]
    return aliases


def extract_key_statements_from_chunks(collection, title: str, max_statements: int = 5) -> List[str]:
    """
    Extract key quality statement titles from standard chunks.
    """
    # Get all chunks for this standard
    results = collection.get(
        where={"title": title},
        include=['documents', 'metadatas']
    )

    key_statements = []

    for metadata in results['metadatas']:
        # Look for statement chunks
        if metadata.get('chunk_type') == 'statement':
            stmt_title = metadata.get('statement_title', '')
            if stmt_title and stmt_title not in key_statements:
                key_statements.append(stmt_title)

                if len(key_statements) >= max_statements:
                    break

    return key_statements


def find_related_standards(
    standards_by_title: Dict,
    current_title: str,
    current_domain: str,
    top_n: int = 3
) -> List[str]:
    """
    Find related standards by clinical domain.
    """
    related_ids = []

    for title, data in standards_by_title.items():
        if title == current_title:
            continue

        # Same domain is related
        if data.get('clinical_domain') == current_domain:
            standard_id = data.get('standard_id')
            if standard_id:
                related_ids.append(standard_id)

                if len(related_ids) >= top_n:
                    break

    return related_ids


def build_catalog(chroma_path: str = "data/dr_opa_agent/chroma") -> List[Dict]:
    """
    Build quality standards catalog from ChromaDB.
    """
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("opa_quality_standards_corpus")

    print("Extracting quality standards metadata...")
    results = collection.get(limit=1000, include=['metadatas'])

    # Group by title
    standards_by_title = defaultdict(lambda: {
        'title': None,
        'condition': None,
        'source_file': None,
        'source_url': None,
        'doc_chunks': 0,
        'statement_chunks': 0,
        'total_chunks': 0,
        'statement_titles': [],
        'num_statements': 0
    })

    for metadata in results['metadatas']:
        title = metadata.get('title', '')
        if not title or title == 'Unknown':
            continue

        standard = standards_by_title[title]
        standard['title'] = title
        standard['total_chunks'] += 1

        # Set attributes from first occurrence
        if not standard['condition']:
            standard['condition'] = metadata.get('condition', '')
            standard['source_file'] = metadata.get('source_file', '')
            standard['source_url'] = metadata.get('source_url', '')

        # Track chunk types
        chunk_type = metadata.get('chunk_type', '')
        if chunk_type == 'document':
            standard['doc_chunks'] += 1
            # Get statement count from document chunk
            num_stmts = metadata.get('num_statements')
            if num_stmts:
                standard['num_statements'] = int(num_stmts)
            # Get statement titles
            stmt_titles = metadata.get('statement_titles', '')
            if stmt_titles:
                standard['statement_titles'] = [s.strip() for s in stmt_titles.split(',')]
        elif chunk_type == 'statement':
            standard['statement_chunks'] += 1
            stmt_title = metadata.get('statement_title', '')
            if stmt_title and stmt_title not in standard['statement_titles']:
                standard['statement_titles'].append(stmt_title)

    print(f"Found {len(standards_by_title)} unique quality standards")

    # Build catalog entries
    catalog = []

    print("Building catalog entries...")
    for title, data in standards_by_title.items():
        print(f"  Processing: {title}")

        # Generate standard_id from source file
        source_file = data.get('source_file', '')
        if source_file:
            standard_id = extract_standard_id_from_filename(source_file)
        else:
            # Fallback: generate from title
            standard_id = title.lower().replace(' ', '_').replace('-', '_')

        # Infer clinical domain
        clinical_domain = infer_clinical_domain(
            data['condition'] or '',
            data['statement_titles']
        )

        # Extract care focus
        care_focus = extract_care_focus_from_statements(data['statement_titles'])

        # Generate aliases
        aliases = generate_aliases(title, data['condition'] or '')

        # Extract key statements
        key_statements = data['statement_titles'][:5]  # Top 5

        entry = {
            "standard_id": standard_id,
            "standard_title": title,
            "aliases": aliases,
            "clinical_domain": clinical_domain,
            "conditions": [data['condition']] if data['condition'] else ['general'],
            "care_focus": care_focus,
            "key_statements": key_statements,
            "statement_count": data['num_statements'] or data['statement_chunks'],
            "chunk_count": data['total_chunks'],
            "doc_chunks": data['doc_chunks'],
            "statement_chunks": data['statement_chunks'],
            "source_url": data['source_url'] or '',
            "source_file": source_file
        }

        # Store for related standards lookup
        standards_by_title[title]['standard_id'] = standard_id
        standards_by_title[title]['clinical_domain'] = clinical_domain

        catalog.append(entry)

    # Add related standards
    print("Finding related standards...")
    for entry in catalog:
        title = entry['standard_title']
        domain = entry['clinical_domain']
        related = find_related_standards(standards_by_title, title, domain)
        entry['related_standards'] = related

    # Sort by title
    catalog.sort(key=lambda x: x['standard_title'])

    return catalog


def main():
    """Main execution."""
    print("="*60)
    print("Ontario Health Quality Standards Catalog Builder")
    print("="*60)
    print()

    # Build catalog
    catalog = build_catalog()

    # Save to file
    output_path = Path("data/dr_opa_agent/qs_catalog.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print()
    print(f"Saving catalog to {output_path}...")

    with open(output_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"✓ Saved {len(catalog)} quality standards to catalog")

    # Print summary statistics
    print()
    print("="*60)
    print("Catalog Summary")
    print("="*60)
    print(f"Total quality standards: {len(catalog)}")

    # Count by clinical domain
    by_domain = defaultdict(int)
    for entry in catalog:
        by_domain[entry['clinical_domain']] += 1

    print(f"\nBy clinical domain:")
    for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count}")

    # Count by care focus
    by_care_focus = defaultdict(int)
    for entry in catalog:
        for focus in entry['care_focus']:
            by_care_focus[focus] += 1

    print(f"\nBy care focus:")
    for focus, count in sorted(by_care_focus.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {focus}: {count}")

    # Print sample entries
    print()
    print("Sample catalog entries:")
    for i, entry in enumerate(catalog[:3]):
        print(f"\n{i+1}. {entry['standard_title']}")
        print(f"   ID: {entry['standard_id']}")
        print(f"   Domain: {entry['clinical_domain']}")
        print(f"   Conditions: {', '.join(entry['conditions'])}")
        print(f"   Care focus: {', '.join(entry['care_focus'][:3])}")
        print(f"   Aliases: {', '.join(entry['aliases'][:3])}")
        print(f"   Statements: {entry['statement_count']} ({entry['statement_chunks']} chunks)")
        if entry['key_statements']:
            print(f"   Key statements: {', '.join(entry['key_statements'][:2])}...")

    print()
    print("="*60)
    print("✓ Catalog build complete!")
    print("="*60)


if __name__ == "__main__":
    main()
