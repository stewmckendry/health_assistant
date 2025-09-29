#!/usr/bin/env python3
"""
Deep analysis of ODB XML structure to understand the hierarchy
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import json

def analyze_xml_hierarchy(xml_file):
    """Analyze the complete structure of the XML file"""
    
    print(f"📄 Analyzing XML hierarchy: {xml_file}")
    print("=" * 80)
    
    # Parse XML
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Find the formulary section
    formulary = root.find('formulary')
    if not formulary:
        print("❌ No formulary section found")
        return
    
    print("\n🔍 Analyzing Formulary Hierarchy:\n")
    
    # Track unique structures
    sample_records = []
    hierarchy_samples = []
    
    # Iterate through top level - likely therapeutic classes (pcg2)
    for i, pcg2 in enumerate(formulary):
        if i >= 3:  # Get first 3 samples
            break
            
        pcg2_name = None
        for child in pcg2:
            if child.tag == 'name':
                pcg2_name = child.text
                break
        
        print(f"\n📌 Level 1 - PCG2 (Therapeutic Class?): {pcg2.tag}")
        print(f"   Name: {pcg2_name}")
        
        # Level 2 - Categories (pcg6)
        for j, pcg6 in enumerate(pcg2.findall('pcg6')):
            if j >= 2:  # Get first 2 categories per class
                break
                
            pcg6_name = None
            for child in pcg6:
                if child.tag == 'name':
                    pcg6_name = child.text
                    break
            
            print(f"\n   📌 Level 2 - PCG6 (Category?): {pcg6.tag}")
            print(f"      Name: {pcg6_name}")
            
            # Level 3 - Generic Names
            for k, gen_name_elem in enumerate(pcg6.findall('genericName')):
                if k >= 1:  # Get first generic per category
                    break
                    
                gen_name = None
                for child in gen_name_elem:
                    if child.tag == 'name':
                        gen_name = child.text
                        break
                
                print(f"\n      📌 Level 3 - Generic Name: {gen_name}")
                
                # Level 4 - PCG Groups (interchangeable groups)
                for l, pcg_group in enumerate(gen_name_elem.findall('pcgGroup')):
                    if l >= 1:  # Get first group
                        break
                    
                    print(f"\n         📌 Level 4 - PCG Group (Interchangeable Group)")
                    
                    # Level 5 - PCG9 (item groups with strength/form)
                    for m, pcg9 in enumerate(pcg_group.findall('pcg9')):
                        if m >= 1:  # Get first item
                            break
                        
                        # Get PCG9 attributes
                        pcg9_data = {}
                        for child in pcg9:
                            if child.tag != 'drug':
                                pcg9_data[child.tag] = child.text
                        
                        print(f"\n            📌 Level 5 - PCG9 (Item Group)")
                        print(f"               Item Number: {pcg9_data.get('itemNumber')}")
                        print(f"               Strength: {pcg9_data.get('strength')}")
                        print(f"               Dosage Form: {pcg9_data.get('dosageForm')}")
                        print(f"               Daily Cost: {pcg9_data.get('dailyCost')}")
                        
                        # Level 6 - Individual drugs
                        print(f"\n               📌 Level 6 - Individual Drugs:")
                        for n, drug in enumerate(pcg9.findall('drug')):
                            if n >= 3:  # Get first 3 drugs
                                break
                            
                            # Get all drug data
                            drug_data = {
                                'attributes': drug.attrib,
                                'elements': {}
                            }
                            
                            for elem in drug:
                                drug_data['elements'][elem.tag] = elem.text
                            
                            din = drug.attrib.get('id', 'N/A')
                            name = drug_data['elements'].get('name', 'N/A')
                            mfr = drug_data['elements'].get('manufacturerId', 'N/A')
                            price = drug_data['elements'].get('individualPrice', 'N/A')
                            
                            print(f"\n                  Drug {n+1}:")
                            print(f"                     DIN: {din}")
                            print(f"                     Name: {name}")
                            print(f"                     Manufacturer: {mfr}")
                            print(f"                     Price: {price}")
                            print(f"                     Attributes: {list(drug.attrib.keys())}")
                            print(f"                     Elements: {list(drug_data['elements'].keys())}")
                            
                            # Store complete sample
                            if len(sample_records) < 5:
                                complete_record = {
                                    'therapeutic_class': pcg2_name,
                                    'category': pcg6_name,
                                    'generic_name': gen_name,
                                    'item_number': pcg9_data.get('itemNumber'),
                                    'strength': pcg9_data.get('strength'),
                                    'dosage_form': pcg9_data.get('dosageForm'),
                                    'daily_cost': pcg9_data.get('dailyCost'),
                                    'drug': drug_data
                                }
                                sample_records.append(complete_record)
    
    # Print summary of data to be captured
    print("\n" + "=" * 80)
    print("\n📊 DATA CAPTURE STRATEGY:\n")
    
    print("1️⃣ SQL Database Tables:")
    print("   - odb_drugs: Individual drug records with all attributes")
    print("   - odb_interchangeable_groups: Groups of interchangeable drugs")
    print("   - odb_manufacturers: Manufacturer reference table")
    print("   - odb_limited_use: LU criteria (if available)")
    
    print("\n2️⃣ Fields for SQL:")
    print("   From hierarchy:")
    print("   - therapeutic_class (pcg2 name)")
    print("   - category (pcg6 name)")  
    print("   - generic_name")
    print("   - item_number, strength, dosage_form")
    print("   - interchangeable_group_id")
    print("   From drug element:")
    print("   - din (id attribute)")
    print("   - name, manufacturerId")
    print("   - individualPrice, amountMOHLTCPays, dailyCost")
    print("   - listingDate, note")
    print("   - Special flags: sec3, sec3b, sec3c, sec9, sec12")
    print("   - Status flags: notABenefit, chronicUseMed, dinStatus")
    
    print("\n3️⃣ Fields for Embeddings:")
    print("   - Concatenated text: generic_name + strength + dosage_form + category")
    print("   - Drug name (brand name)")
    print("   - Clinical notes")
    print("   - Therapeutic class description")
    
    print("\n4️⃣ Sample Complete Record:")
    if sample_records:
        print(json.dumps(sample_records[0], indent=2))
    
    return sample_records

def main():
    xml_file = "data/dr_off_agent/ontario/odb/moh-ontario-drug-benefit-odb-formulary-edition-43-data-extract-en-2025-08-29.xml"
    
    if not Path(xml_file).exists():
        print(f"❌ XML file not found: {xml_file}")
        return
    
    analyze_xml_hierarchy(xml_file)

if __name__ == "__main__":
    main()