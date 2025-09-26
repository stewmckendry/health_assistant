#!/usr/bin/env python3
"""
Analyze ODB XML file structure and content
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict, Counter
import json

def analyze_xml_structure(xml_file):
    """Analyze the structure and content of the ODB XML file"""
    
    print(f"📄 Analyzing XML file: {xml_file}")
    print("=" * 80)
    
    # Parse XML
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    print(f"\n📌 Root element: {root.tag}")
    print(f"   Attributes: {root.attrib}")
    
    # Analyze top-level structure
    print(f"\n📊 Top-level elements:")
    child_counts = Counter()
    for child in root:
        child_counts[child.tag] += 1
    
    for tag, count in child_counts.items():
        print(f"   - {tag}: {count} items")
    
    # Analyze manufacturer structure
    print(f"\n🏭 Manufacturer Structure:")
    manufacturers = root.find('.//manufacturers')
    if manufacturers:
        sample_mfr = manufacturers[0] if len(manufacturers) > 0 else None
        if sample_mfr:
            print(f"   Sample manufacturer:")
            for elem in sample_mfr:
                text = elem.text[:50] if elem.text else "None"
                print(f"     - {elem.tag}: {text}")
    
    # Analyze product structure
    print(f"\n💊 Product/Drug Structure:")
    products = root.find('.//products')
    if products:
        # Get first product group
        first_group = None
        for child in products:
            if child.tag in ['category', 'therapeuticClass']:
                print(f"\n   Category/Class: {child.tag} = {child.text}")
            elif child.tag == 'itemNumber':
                first_group = child
                break
        
        if first_group:
            print(f"\n   Item Number: {first_group.text}")
            
            # Analyze drug structure
            for drug_container in first_group:
                if drug_container.tag in ['genericName', 'strength', 'dosageForm']:
                    print(f"   {drug_container.tag}: {drug_container.text}")
                elif drug_container.tag == 'drug':
                    print(f"\n   📦 Drug entry structure:")
                    print(f"      Attributes: {drug_container.attrib}")
                    for elem in drug_container:
                        text = elem.text[:50] if elem.text else "None"
                        print(f"      - {elem.tag}: {text}")
                    break
    
    # Detailed analysis of drug attributes
    print(f"\n🔍 Analyzing all drug entries...")
    all_drugs = []
    drug_attributes = defaultdict(set)
    drug_elements = defaultdict(set)
    lu_codes = set()
    
    # Find all drug elements
    for drug in root.iter('drug'):
        drug_data = {'attributes': drug.attrib, 'elements': {}}
        
        # Collect attributes
        for attr, value in drug.attrib.items():
            drug_attributes[attr].add(value)
            if attr == 'id':  # DIN
                drug_data['din'] = value
        
        # Collect child elements
        for elem in drug:
            drug_elements[elem.tag].add(elem.text if elem.text else "")
            drug_data['elements'][elem.tag] = elem.text
            
            # Check for Limited Use codes
            if elem.tag == 'limitedUseCode':
                lu_codes.add(elem.text)
        
        all_drugs.append(drug_data)
    
    print(f"\n📈 Statistics:")
    print(f"   Total drugs: {len(all_drugs)}")
    print(f"   Unique Limited Use codes: {len(lu_codes)}")
    
    print(f"\n🏷️ Drug Attributes Found:")
    for attr, values in drug_attributes.items():
        sample_values = list(values)[:5]
        print(f"   - {attr}: {len(values)} unique values")
        print(f"     Examples: {sample_values}")
    
    print(f"\n📋 Drug Elements Found:")
    for elem, values in drug_elements.items():
        non_empty = [v for v in values if v]
        print(f"   - {elem}: {len(non_empty)} non-empty values")
        if non_empty:
            samples = list(non_empty)[:3]
            print(f"     Examples: {samples[:3]}")
    
    # Sample complete drug records
    print(f"\n📝 Sample Complete Drug Records (first 3):")
    for i, drug in enumerate(all_drugs[:3]):
        print(f"\n   Drug {i+1}:")
        print(f"   DIN: {drug.get('din', 'N/A')}")
        print(f"   Attributes: {json.dumps(drug['attributes'], indent=6)}")
        print(f"   Elements:")
        for key, value in drug['elements'].items():
            if value:
                print(f"      - {key}: {value[:100]}")
    
    # Analyze Limited Use patterns
    if lu_codes:
        print(f"\n🔒 Limited Use Codes Found: {len(lu_codes)}")
        print(f"   Sample LU codes: {list(lu_codes)[:10]}")
    
    # Find drugs with special sections
    section_counts = {
        'sec3': 0, 'sec3b': 0, 'sec3c': 0, 
        'sec9': 0, 'sec12': 0
    }
    for drug in all_drugs:
        for section in section_counts:
            if drug['attributes'].get(section) == 'Y':
                section_counts[section] += 1
    
    print(f"\n📑 Special Sections:")
    for section, count in section_counts.items():
        print(f"   - {section}: {count} drugs")
    
    return {
        'total_drugs': len(all_drugs),
        'lu_codes': lu_codes,
        'sample_drugs': all_drugs[:5],
        'drug_attributes': {k: list(v)[:10] for k, v in drug_attributes.items()},
        'drug_elements': {k: list(v)[:10] for k, v in drug_elements.items()}
    }

def main():
    xml_file = "data/dr_off_agent/ontario/odb/moh-ontario-drug-benefit-odb-formulary-edition-43-data-extract-en-2025-08-29.xml"
    
    if not Path(xml_file).exists():
        print(f"❌ XML file not found: {xml_file}")
        return
    
    analyze_xml_structure(xml_file)

if __name__ == "__main__":
    main()