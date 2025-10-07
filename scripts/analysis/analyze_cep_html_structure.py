#!/usr/bin/env python3
"""Analyze CEP HTML structure to understand extraction issues."""
from bs4 import BeautifulSoup
from pathlib import Path
import json

html_file = Path("data/dr_opa_agent/raw/cep/type-2-diabetes-non-insulin-pharmacotherapy-2.html")
with open(html_file) as f:
    soup = BeautifulSoup(f, 'html.parser')

print("="*80)
print("CEP HTML STRUCTURE ANALYSIS")
print("="*80)

# Check heading structure
print(f"\nHeading counts:")
print(f"  H1: {len(soup.find_all('h1'))}")
print(f"  H2: {len(soup.find_all('h2'))}")
print(f"  H3: {len(soup.find_all('h3'))}")
print(f"  H4: {len(soup.find_all('h4'))}")

# Find sections/divs
divs_with_id = soup.find_all('div', id=True)
print(f"\nTotal divs with ID: {len(divs_with_id)}")

# Sample div IDs
print("\nSample div IDs related to content:")
for div in divs_with_id[:30]:
    div_id = div.get('id', '')
    if any(keyword in div_id for keyword in ['section', 'content', 'tool', 'tab', 'panel', 'accordion']):
        print(f"  {div_id}")

# Check if CEP uses interactive/accordion structure
buttons = soup.find_all('button')
print(f"\nTotal buttons: {len(buttons)}")
if buttons:
    print("\nSample button texts (first 10):")
    for btn in buttons[:10]:
        text = btn.get_text(strip=True)
        if text and len(text) < 100:
            print(f"  {text[:80]}")

# Check for aria-controls (accordion pattern)
aria_controls = soup.find_all(attrs={'aria-controls': True})
print(f"\nElements with aria-controls: {len(aria_controls)}")

# Find main content area
main = soup.find('main')
if main:
    print("\n✓ Found <main> tag")
    print(f"  Children: {len(list(main.children))}")

# Check for role="tabpanel" or similar
tabpanels = soup.find_all(attrs={'role': 'tabpanel'})
accordions = soup.find_all(attrs={'role': 'region'})
print(f"\nInteractive elements:")
print(f"  Tabpanels: {len(tabpanels)}")
print(f"  Accordions/Regions: {len(accordions)}")

# Look for common CEP patterns
cep_content = soup.find_all('div', class_=lambda x: x and 'tool' in str(x).lower())
print(f"\nDivs with 'tool' in class: {len(cep_content)}")

# Sample some actual content
print("\n" + "="*80)
print("SAMPLE CONTENT")
print("="*80)

# Try to find where actual clinical content is
clinical_keywords = ['diagnosis', 'screen', 'treatment', 'management', 'algorithm']
for keyword in clinical_keywords:
    elements = soup.find_all(text=lambda t: t and keyword in t.lower())
    if elements:
        print(f"\n'{keyword}' appears {len(elements)} times in text nodes")
        # Show first occurrence context
        first = elements[0]
        parent = first.parent
        if parent:
            print(f"  Parent tag: {parent.name}")
            print(f"  Parent ID: {parent.get('id', 'N/A')}")
            print(f"  Parent class: {parent.get('class', 'N/A')}")
            print(f"  Sample: {str(first)[:150]}...")

print("\n" + "="*80)
