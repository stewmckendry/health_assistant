#!/usr/bin/env python3
"""
Analyze ADP PDFs to extract Table of Contents and determine clinically relevant page ranges
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'pdfplumber'])
    import pdfplumber


class ADPTOCAnalyzer:
    """Analyze ADP PDFs to extract clinically relevant sections"""
    
    # Clinically relevant parts based on your analysis
    RELEVANT_PARTS = {
        'devices_covered': [2],  # Part 2: Devices Covered
        'eligibility': [3, 4],   # Part 3-4: Eligibility criteria
        'special_programs': [5], # Part 5: CEP, special programs
        'funding': [6, 7]        # Part 6-7: Device eligibility and funding
    }
    
    # Pattern to match part headers
    PART_PATTERN = re.compile(r'Part\s+(\d+):\s*([^0-9]+?)(?:\s+(\d+))?$', re.IGNORECASE)
    
    # Pattern to match section numbers with page numbers  
    SECTION_PATTERN = re.compile(r'(\d{2,4})\s+(.+?)\s+(\d+)$')
    
    def __init__(self):
        self.toc_cache = {}
    
    def extract_toc_from_pdf(self, pdf_path: str) -> Dict:
        """Extract table of contents from PDF"""
        
        if pdf_path in self.toc_cache:
            return self.toc_cache[pdf_path]
        
        toc_data = {
            'parts': [],
            'sections': [],
            'page_ranges': {}
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Look for TOC in first 10 pages
                toc_text = ""
                for page_num in range(min(10, len(pdf.pages))):
                    page_text = pdf.pages[page_num].extract_text() or ""
                    
                    # Check if this looks like a TOC page
                    if any(keyword in page_text.lower() for keyword in ['table of contents', 'contents']):
                        toc_text += f"\n--- PAGE {page_num + 1} ---\n{page_text}"
                
                if not toc_text:
                    print(f"  Warning: No TOC found in {Path(pdf_path).name}")
                    return toc_data
                
                # Parse parts and sections
                current_part = None
                lines = toc_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line or len(line) < 10:
                        continue
                    
                    # Check for part headers
                    part_match = self.PART_PATTERN.match(line)
                    if part_match:
                        part_num = int(part_match.group(1))
                        part_title = part_match.group(2).strip()
                        page_num = part_match.group(3)
                        
                        current_part = {
                            'number': part_num,
                            'title': part_title,
                            'start_page': int(page_num) if page_num else None
                        }
                        toc_data['parts'].append(current_part)
                        continue
                    
                    # Check for section entries
                    section_match = self.SECTION_PATTERN.match(line)
                    if section_match:
                        section_num = section_match.group(1)
                        section_title = section_match.group(2).strip()
                        page_num = int(section_match.group(3))
                        
                        section = {
                            'number': section_num,
                            'title': section_title,
                            'page': page_num,
                            'part': current_part['number'] if current_part else None
                        }
                        toc_data['sections'].append(section)
                
                # Calculate page ranges for relevant parts
                toc_data['page_ranges'] = self._calculate_relevant_ranges(toc_data)
                
        except Exception as e:
            print(f"  Error processing {Path(pdf_path).name}: {e}")
        
        self.toc_cache[pdf_path] = toc_data
        return toc_data
    
    def _calculate_relevant_ranges(self, toc_data: Dict) -> Dict:
        """Calculate page ranges for clinically relevant sections"""
        ranges = {}
        
        # Get all relevant part numbers
        relevant_parts = []
        for category, part_nums in self.RELEVANT_PARTS.items():
            relevant_parts.extend(part_nums)
        
        # Find start and end pages for relevant parts
        relevant_sections = [
            s for s in toc_data['sections'] 
            if s['part'] in relevant_parts
        ]
        
        if relevant_sections:
            # Sort by page number
            relevant_sections.sort(key=lambda x: x['page'])
            
            start_page = relevant_sections[0]['page']
            end_page = relevant_sections[-1]['page']
            
            # Try to find the end of the last relevant section
            # by looking for the next section that's not relevant
            all_sections = sorted(toc_data['sections'], key=lambda x: x['page'])
            
            last_relevant_page = end_page
            for section in all_sections:
                if section['page'] > end_page and section['part'] not in relevant_parts:
                    last_relevant_page = section['page'] - 1
                    break
            
            ranges['clinical_content'] = {
                'start_page': start_page,
                'end_page': last_relevant_page,
                'total_pages': last_relevant_page - start_page + 1
            }
            
            # Break down by category
            for category, part_nums in self.RELEVANT_PARTS.items():
                category_sections = [
                    s for s in relevant_sections 
                    if s['part'] in part_nums
                ]
                
                if category_sections:
                    cat_start = min(s['page'] for s in category_sections)
                    cat_end = max(s['page'] for s in category_sections)
                    
                    # Extend end to next non-category section
                    for section in all_sections:
                        if section['page'] > cat_end and section['part'] not in part_nums:
                            cat_end = section['page'] - 1
                            break
                    
                    ranges[category] = {
                        'start_page': cat_start,
                        'end_page': cat_end,
                        'parts': part_nums
                    }
        
        return ranges
    
    def analyze_document(self, pdf_path: str) -> Dict:
        """Analyze a single ADP document"""
        
        doc_name = Path(pdf_path).name
        print(f"\nAnalyzing: {doc_name}")
        print("-" * 50)
        
        # Extract TOC
        toc_data = self.extract_toc_from_pdf(pdf_path)
        
        # Document info
        doc_info = {
            'filename': doc_name,
            'path': str(pdf_path),
            'total_parts': len(toc_data['parts']),
            'total_sections': len(toc_data['sections'])
        }
        
        # Show parts found
        if toc_data['parts']:
            print(f"Found {len(toc_data['parts'])} parts:")
            for part in toc_data['parts']:
                relevance = "📋" if part['number'] in [2,3,4,5,6,7] else "❌"
                print(f"  {relevance} Part {part['number']}: {part['title']}")
        
        # Show page ranges for extraction
        if toc_data['page_ranges']:
            clinical_range = toc_data['page_ranges'].get('clinical_content')
            if clinical_range:
                start = clinical_range['start_page']
                end = clinical_range['end_page']
                total = clinical_range['total_pages']
                print(f"\n📄 Recommended extraction: Pages {start}-{end} ({total} pages)")
                
                # Show breakdown
                for category, range_info in toc_data['page_ranges'].items():
                    if category != 'clinical_content':
                        parts = range_info.get('parts', [])
                        start = range_info['start_page']
                        end = range_info['end_page']
                        print(f"   • {category.replace('_', ' ').title()}: Pages {start}-{end} (Parts {parts})")
        
        # Combine all data
        doc_info.update({
            'toc': toc_data,
            'extraction_recommended': toc_data['page_ranges'].get('clinical_content', {})
        })
        
        return doc_info


def main():
    print("ADP Document TOC Analysis for Clinically Relevant Content")
    print("=" * 60)
    
    # Find all ADP PDFs
    pdf_dir = Path("data/dr_off_agent/ontario/adp")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDFs found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} ADP documents")
    
    analyzer = ADPTOCAnalyzer()
    results = []
    
    # Analyze each document
    for pdf_path in pdf_files:
        try:
            doc_info = analyzer.analyze_document(pdf_path)
            results.append(doc_info)
        except Exception as e:
            print(f"Error analyzing {pdf_path.name}: {e}")
    
    # Save results
    output_file = Path("tests/dr_off_agent/test_outputs/adp_toc_analysis.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    summary = {
        'analysis_date': '2025-09-24',
        'total_documents': len(results),
        'documents': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ Analysis complete! Results saved to: {output_file}")
    
    # Summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    
    total_clinical_pages = 0
    for doc in results:
        extraction = doc.get('extraction_recommended', {})
        if extraction:
            pages = extraction.get('total_pages', 0)
            total_clinical_pages += pages
            print(f"{doc['filename']:<50} {pages:>3} pages")
    
    print(f"\nTotal clinical pages to extract: {total_clinical_pages}")
    print(f"Average per document: {total_clinical_pages/len(results):.1f} pages")


if __name__ == "__main__":
    main()