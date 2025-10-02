"""
Quick script to analyze the structure of Quality Standards PDFs.
"""

import PyPDF2
import re
from pathlib import Path

def analyze_pdf(pdf_path: str, pages_to_check: int = 20):
    """Analyze PDF structure to understand quality statement patterns."""
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        print(f"\nAnalyzing: {Path(pdf_path).name}")
        print(f"Total pages: {len(reader.pages)}")
        print("="*60)
        
        # Look for quality statement patterns
        for i in range(min(pages_to_check, len(reader.pages))):
            text = reader.pages[i].extract_text()
            
            # Search for various patterns
            patterns = [
                r'Quality Statement\s+(\d+)',
                r'QUALITY STATEMENT\s+(\d+)',
                r'Statement\s+(\d+):',
                r'^\s*(\d+)\.\s+[A-Z]',  # Numbered items
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
                if matches:
                    print(f"\nPage {i+1}:")
                    print(f"  Pattern '{pattern}' found: {matches}")
                    
                    # Show context
                    lines = text.split('\n')
                    for j, line in enumerate(lines):
                        if re.search(pattern, line, re.IGNORECASE):
                            # Show 2 lines before and after for context
                            start = max(0, j-2)
                            end = min(len(lines), j+3)
                            print(f"  Context:")
                            for k in range(start, end):
                                prefix = ">>> " if k == j else "    "
                                print(f"  {prefix}{lines[k][:80]}")
                            break

if __name__ == "__main__":
    pdf_path = "data/dr_opa_agent/raw/oh_quality_std/qs-chronic-pain-quality-standard-en.pdf"
    analyze_pdf(pdf_path, pages_to_check=20)