"""
Debug TOC extraction for problematic PDFs.
"""

import PyPDF2
import re

def debug_toc(pdf_path):
    """Debug TOC extraction."""
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        # Find TOC page
        for i in range(min(10, len(reader.pages))):
            text = reader.pages[i].extract_text()
            
            if "Table of Contents" in text:
                print(f"Found Table of Contents on page {i+1}")
                print("=" * 60)
                print(text)
                print("=" * 60)
                
                # Look for the quality statements section
                lines = text.split('\n')
                in_section = False
                
                for j, line in enumerate(lines):
                    if "Quality Statements to Improve Care" in line:
                        print(f"\nFound section at line {j}: {line}")
                        in_section = True
                        # Print next 20 lines
                        for k in range(j+1, min(j+21, len(lines))):
                            print(f"  Line {k}: {repr(lines[k])}")
                        break
                
                return

# Test on eating disorders PDF
pdf_path = "data/dr_opa_agent/raw/oh_quality_std/qs-eating-disorders-quality-standard-en.pdf"
debug_toc(pdf_path)