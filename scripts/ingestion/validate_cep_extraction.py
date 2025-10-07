#!/usr/bin/env python3
"""Validate CEP extraction by comparing web page to extracted content."""
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import json
import requests
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_agents.dr_opa_agent.ingestion.cep.ingester_v2 import CEPIngesterV2

def get_sections_from_web(url):
    """Scrape actual web page to get section structure."""
    print(f"\nFetching live page: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all headings on the live page
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4']:
            for heading in soup.find_all(tag):
                text = heading.get_text(strip=True)
                if text and len(text) > 3:  # Skip trivial headings
                    headings.append({
                        'level': tag,
                        'text': text
                    })

        return headings, soup
    except Exception as e:
        print(f"  ❌ Error fetching: {e}")
        return [], None

def get_sections_from_extracted(html_file, ingester):
    """Get sections from our extraction."""
    with open(html_file) as f:
        soup = BeautifulSoup(f, 'html.parser')

    meta_file = html_file.with_suffix('.html').with_name(html_file.stem + '_meta.json')
    if meta_file.exists():
        with open(meta_file) as f:
            tool_info = json.load(f)
    else:
        tool_info = {'name': html_file.stem, 'category': 'unknown', 'slug': html_file.stem}

    sections = ingester._extract_full_sections(soup, tool_info)

    return sections

def compare_extraction(tool_name, url, html_file):
    """Compare web page content to extracted content."""
    print(f"\n{'='*80}")
    print(f"VALIDATION: {tool_name}")
    print('='*80)

    # Get web page sections
    web_headings, web_soup = get_sections_from_web(url)

    if not web_soup:
        print("  ⚠️  Could not fetch web page, skipping comparison")
        return

    # Get extracted sections
    ingester = CEPIngesterV2(chroma_path=None)
    extracted_sections = get_sections_from_extracted(html_file, ingester)

    print(f"\n📊 SECTION COMPARISON:")
    print(f"  Web page: {len(web_headings)} headings found")
    print(f"  Extracted: {len(extracted_sections)} sections")

    # Show web page headings (H2 and H3 only - main structure)
    print(f"\n📋 WEB PAGE STRUCTURE (H2/H3 headings):")
    web_h2h3 = [h for h in web_headings if h['level'] in ['h2', 'h3']]
    for i, heading in enumerate(web_h2h3[:20], 1):
        indent = "  " if heading['level'] == 'h2' else "    "
        print(f"{indent}{i}. [{heading['level'].upper()}] {heading['text'][:70]}")

    if len(web_h2h3) > 20:
        print(f"    ... and {len(web_h2h3) - 20} more")

    # Show extracted sections
    print(f"\n📦 EXTRACTED SECTIONS:")
    for i, section in enumerate(extracted_sections, 1):
        heading = section.get('heading', 'N/A')
        words = len(section.get('content', '').split())
        print(f"  {i}. {heading[:70]} ({words} words)")
        if section.get('subsections'):
            for sub in section['subsections'][:3]:
                print(f"      - {sub[:60]}")

    # Check if all major web sections are in extracted
    print(f"\n✅ COVERAGE CHECK:")
    web_h2_texts = [h['text'].lower() for h in web_headings if h['level'] == 'h2']
    extracted_headings = [s.get('heading', '').lower() for s in extracted_sections]

    found = 0
    missing = []
    for web_heading in web_h2_texts:
        # Fuzzy match - check if any extracted heading contains this text
        matched = any(web_heading in ext or ext in web_heading
                     for ext in extracted_headings)
        if matched:
            found += 1
        else:
            # Clean up the heading for display
            clean = web_heading.replace('new', '').strip()
            if clean:  # Skip empty after cleaning
                missing.append(clean)

    coverage_pct = (found / len(web_h2_texts) * 100) if web_h2_texts else 0
    print(f"  Found: {found}/{len(web_h2_texts)} major sections ({coverage_pct:.0f}%)")

    if missing:
        print(f"\n  ⚠️  Potentially missing sections:")
        for m in missing[:10]:
            print(f"    - {m[:70]}")
    else:
        print(f"  ✅ All major sections extracted!")

    # Word count comparison
    web_text = web_soup.get_text(separator=' ', strip=True)
    web_words = len(web_text.split())

    extracted_text = '\n\n'.join(s.get('content', '') for s in extracted_sections)
    extracted_words = len(extracted_text.split())

    print(f"\n📝 WORD COUNT:")
    print(f"  Web page (visible text): {web_words:,} words")
    print(f"  Extracted: {extracted_words:,} words")

    # Sample content comparison
    print(f"\n🔍 SAMPLE CONTENT CHECK:")

    # Pick a specific section to validate deeply
    test_section_keywords = ['diagnosis', 'assessment', 'screening', 'treatment', 'management']

    for keyword in test_section_keywords:
        web_section = None
        for h in web_headings:
            if keyword in h['text'].lower() and h['level'] == 'h2':
                web_section = h['text']
                break

        if web_section:
            print(f"\n  Testing section: '{web_section}'")

            # Find in extracted
            extracted_section = None
            for s in extracted_sections:
                if keyword in s.get('heading', '').lower():
                    extracted_section = s
                    break

            if extracted_section:
                content = extracted_section.get('content', '')
                words = len(content.split())
                print(f"    ✅ Found in extracted ({words} words)")
                print(f"    Preview: {content[:150]}...")

                # Check for key clinical terms that should be present
                clinical_terms = ['patient', 'treatment', 'assess', 'diagnos', 'symptom']
                found_terms = sum(1 for term in clinical_terms if term in content.lower())
                print(f"    Clinical terms present: {found_terms}/{len(clinical_terms)}")
            else:
                print(f"    ❌ NOT found in extracted sections")

            break  # Just check one sample section

    return coverage_pct, extracted_words


def main():
    """Validate extraction on 3 test tools."""
    raw_dir = Path("data/dr_opa_agent/raw/cep")

    test_cases = [
        {
            'name': 'Dementia Diagnosis',
            'url': 'https://tools.cep.health/tool/dementia-diagnosis/',
            'html': 'dementia-diagnosis.html'
        },
        {
            'name': 'Heart Failure Management',
            'url': 'https://tools.cep.health/tool/managing-patients-with-heart-failure-in-primary-care/',
            'html': 'managing-patients-with-heart-failure-in-primary-care.html'
        },
        {
            'name': 'ADHD in Adults',
            'url': 'https://tools.cep.health/tool/attention-deficit-hyperactivity-disorder-in-adults/',
            'html': 'attention-deficit-hyperactivity-disorder-in-adults.html'
        }
    ]

    results = []

    for test in test_cases:
        html_file = raw_dir / test['html']

        if not html_file.exists():
            print(f"\n⚠️  HTML file not found: {test['html']}")
            continue

        try:
            coverage, words = compare_extraction(test['name'], test['url'], html_file)
            results.append({
                'name': test['name'],
                'coverage': coverage,
                'words': words
            })
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # Final summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print('='*80)

    if results:
        avg_coverage = sum(r['coverage'] for r in results) / len(results)
        avg_words = sum(r['words'] for r in results) / len(results)

        print(f"\nOverall Results ({len(results)} tools):")
        print(f"  Average section coverage: {avg_coverage:.0f}%")
        print(f"  Average words extracted: {avg_words:,.0f}")

        print(f"\nPer-tool:")
        for r in results:
            print(f"  {r['name']:40} | {r['coverage']:3.0f}% coverage | {r['words']:6,d} words")

        if avg_coverage >= 90:
            print(f"\n✅ EXCELLENT: Extraction is comprehensive!")
        elif avg_coverage >= 75:
            print(f"\n✓ GOOD: Most content extracted, minor gaps acceptable")
        else:
            print(f"\n⚠️  NEEDS IMPROVEMENT: Significant content missing")


if __name__ == "__main__":
    main()
