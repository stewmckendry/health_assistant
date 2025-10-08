#!/usr/bin/env python3
"""Deep inspection of CEP HTML to find ALL content locations."""
from bs4 import BeautifulSoup
from pathlib import Path
from collections import Counter

html_file = Path("data/dr_opa_agent/raw/cep/type-2-diabetes-non-insulin-pharmacotherapy-2.html")
with open(html_file) as f:
    soup = BeautifulSoup(f, 'html.parser')

print("="*80)
print("DEEP CEP HTML CONTENT INSPECTION")
print("="*80)

# 1. Find all tags with substantial text (>100 chars)
print("\n1. TAGS WITH SUBSTANTIAL CONTENT (>100 chars):")
print("-"*80)

content_tags = Counter()
for element in soup.find_all():
    if element.name:
        text = element.get_text(strip=True)
        if len(text) > 100:
            # Only count direct text, not all descendant text
            direct_text = ''.join(element.find_all(text=True, recursive=False))
            if len(direct_text) > 100:
                content_tags[element.name] += 1

print("Tag counts with >100 chars direct content:")
for tag, count in content_tags.most_common(20):
    print(f"  <{tag}>: {count} instances")

# 2. Find all classes that contain content
print("\n2. CLASSES WITH SUBSTANTIAL CONTENT:")
print("-"*80)

content_classes = Counter()
for element in soup.find_all(class_=True):
    classes = element.get('class', [])
    if isinstance(classes, list):
        classes = ' '.join(classes)
    text = element.get_text(strip=True)
    if len(text) > 100:
        content_classes[classes] += 1

print("Top 20 classes with content:")
for cls, count in content_classes.most_common(20):
    # Truncate long class names
    cls_display = cls[:80] + '...' if len(cls) > 80 else cls
    print(f"  {cls_display}: {count} instances")

# 3. Analyze Gravity Forms structure
print("\n3. GRAVITY FORMS STRUCTURE:")
print("-"*80)

gfields = soup.find_all('div', class_=lambda x: x and 'gfield' in str(x))
print(f"Total gfield divs: {len(gfields)}")

# Categorize gfields by type
gfield_types = Counter()
for gfield in gfields:
    classes = ' '.join(gfield.get('class', []))
    # Extract type
    if 'gfield--type-html' in classes:
        gfield_types['html_content'] += 1
    elif 'gfield--type-radio' in classes:
        gfield_types['radio_input'] += 1
    elif 'gfield--type-section' in classes:
        gfield_types['section_header'] += 1
    elif 'gfield--type-text' in classes:
        gfield_types['text_input'] += 1
    else:
        gfield_types['other'] += 1

print("\ngfield types:")
for gtype, count in gfield_types.items():
    print(f"  {gtype}: {count}")

# 4. Show sample HTML content gfields
print("\n4. SAMPLE HTML CONTENT GFIELDS:")
print("-"*80)

html_gfields = soup.find_all('div', class_=lambda x: x and 'gfield--type-html' in str(x))
print(f"Total HTML gfields: {len(html_gfields)}")

for i, gfield in enumerate(html_gfields[:5]):
    text = gfield.get_text(strip=True)
    print(f"\nHTML gfield #{i+1}:")
    print(f"  ID: {gfield.get('id', 'N/A')}")
    print(f"  Text length: {len(text)} chars")
    print(f"  Sample: {text[:200]}...")

# 5. Check for hidden content
print("\n5. HIDDEN CONTENT CHECK:")
print("-"*80)

hidden_elements = soup.find_all(class_=lambda x: x and 'hidden' in str(x).lower())
print(f"Elements with 'hidden' in class: {len(hidden_elements)}")

# Check style="display:none"
display_none = soup.find_all(style=lambda x: x and 'display:none' in str(x).lower())
print(f"Elements with display:none: {len(display_none)}")

# Check visibility classes
visibility_hidden = soup.find_all(class_=lambda x: x and 'gfield_visibility_' in str(x))
print(f"Elements with gfield_visibility_*: {len(visibility_hidden)}")

visible = [e for e in visibility_hidden if 'visible' in ' '.join(e.get('class', []))]
hidden = [e for e in visibility_hidden if 'hidden' in ' '.join(e.get('class', []))]
print(f"  - visible: {len(visible)}")
print(f"  - hidden: {len(hidden)}")

# 6. Find actual section headings
print("\n6. SECTION HEADING ANALYSIS:")
print("-"*80)

print("\nH2 headings:")
for h2 in soup.find_all('h2'):
    print(f"  - {h2.get_text(strip=True)}")

print("\nH3 headings:")
for h3 in soup.find_all('h3')[:10]:
    print(f"  - {h3.get_text(strip=True)}")

print("\nH4 headings (first 10):")
for h4 in soup.find_all('h4')[:10]:
    print(f"  - {h4.get_text(strip=True)}")

# 7. Find conditional logic sections
print("\n7. CONDITIONAL LOGIC (INTERACTIVE) SECTIONS:")
print("-"*80)

conditional = soup.find_all(attrs={'data-conditional-logic': True})
print(f"Elements with conditional logic: {len(conditional)}")

has_conditional = soup.find_all(class_=lambda x: x and 'has-conditional-logic' in str(x))
print(f"Elements with 'has-conditional-logic' class: {len(has_conditional)}")

# 8. Find where "Diagnosis" section content actually is
print("\n8. LOCATING 'DIAGNOSIS' CONTENT:")
print("-"*80)

diagnosis_heading = soup.find('h2', string=lambda s: s and 'diagnosis' in s.lower())
if diagnosis_heading:
    print(f"Found Diagnosis heading: {diagnosis_heading.get_text(strip=True)}")
    print(f"  Parent: {diagnosis_heading.parent.name}")
    print(f"  Parent ID: {diagnosis_heading.parent.get('id', 'N/A')}")

    # Find next siblings with content
    print("\n  Next siblings with content:")
    sibling = diagnosis_heading.find_next_sibling()
    count = 0
    while sibling and count < 5:
        if sibling.name and len(sibling.get_text(strip=True)) > 50:
            text = sibling.get_text(strip=True)
            print(f"    {sibling.name} (id={sibling.get('id', 'N/A')}): {text[:100]}...")
            count += 1
        sibling = sibling.find_next_sibling()

print("\n" + "="*80)
