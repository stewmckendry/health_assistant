"""
Extract the 5 remaining Quality Standards PDFs with alternative TOC format.
"""

import asyncio
import json
import re
from pathlib import Path
import PyPDF2
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from src.ai_agents.dr_opa_agent.ingestion.quality_standards.qs_extractor_v3 import (
    QualityStandardsExtractorV3,
    QualityStandardDocument,
    QualityStatement,
    FrontMatter
)

def parse_alternative_toc(toc_text: str):
    """
    Parse TOC for PDFs with alternative format.
    Statements are listed between two "Quality Statements to Improve Care" entries.
    """
    lines = toc_text.split('\n')
    statements = {}
    stmt_num = 0
    
    # Find the range of quality statements
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        # Find second occurrence of "Quality Statements to Improve Care" (the section start)
        if "Quality Statements to Improve Care" in line and "..." in line and i > 5:
            start_idx = i + 1
        elif start_idx and "Appendices" in line:
            end_idx = i
            break
    
    if not start_idx:
        return statements
    
    # Extract statements between the markers
    for i in range(start_idx, end_idx if end_idx else len(lines)):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Parse statement entry (title with dots and page number)
        # Pattern: Title...page or Title spaces page
        match = re.match(r'^([A-Z][^\.0-9]+?)[\s\.]+(\d+)\s*$', line)
        if match:
            stmt_num += 1
            title = match.group(1).strip()
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            page = int(match.group(2))
            
            statements[stmt_num] = (title, page)
            print(f"Found Statement {stmt_num}: {title} on page {page}")
    
    return statements

async def extract_with_custom_toc(pdf_path: str, output_path: str):
    """Extract PDF using custom TOC parsing."""
    
    print(f"\nProcessing: {pdf_path}")
    
    # Find TOC page
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        toc_text = None
        toc_page = None
        
        for i in range(min(10, len(reader.pages))):
            text = reader.pages[i].extract_text()
            if "Table of Contents" in text:
                toc_text = text
                toc_page = i + 1
                print(f"Found TOC on page {toc_page}")
                break
    
    if not toc_text:
        print("ERROR: Could not find Table of Contents")
        return False
    
    # Parse statements
    statements = parse_alternative_toc(toc_text)
    
    if not statements:
        print("ERROR: Could not parse statements from TOC")
        return False
    
    print(f"Parsed {len(statements)} statements from TOC")
    
    # Create extractor and extract using parsed TOC
    extractor = QualityStandardsExtractorV3()
    
    # Manually build document
    try:
        # Get first statement page
        first_stmt_page = min(page for _, page in statements.values())
        
        # Extract front matter
        print(f"Extracting front matter (pages 1-{first_stmt_page-1})")
        front_matter = await extractor.extract_front_matter(pdf_path, first_stmt_page)
        
        # Extract statements
        extracted_statements = []
        total_pages = len(PyPDF2.PdfReader(open(pdf_path, 'rb')).pages)
        sorted_stmts = sorted(statements.items())
        
        for i, (stmt_num, (title, start_page)) in enumerate(sorted_stmts):
            # Determine end page
            if i < len(sorted_stmts) - 1:
                end_page = sorted_stmts[i + 1][1][1] - 1
            else:
                end_page = min(start_page + 4, total_pages)
            
            print(f"Extracting Statement {stmt_num}: {title} (pages {start_page}-{end_page})")
            
            # Extract text
            text = extractor.extract_pages(pdf_path, start_page, end_page)
            
            # Use LLM to structure
            stmt = await extractor.extract_statement_with_llm(text, stmt_num, title)
            
            if stmt:
                extracted_statements.append(stmt)
                print(f"  ✓ Extracted successfully")
        
        # Get title from first page
        first_page = extractor.extract_pages(pdf_path, 1, 1)
        title_match = re.search(r'([\w\s\-,&]+?)(?:Quality Standard|Care for)', first_page)
        title = title_match.group(1).strip() if title_match else Path(pdf_path).stem
        
        # Create document
        document = QualityStandardDocument(
            title=title,
            year=None,
            front_matter=front_matter,
            total_statements=len(extracted_statements),
            statements=extracted_statements,
            source_file=pdf_path
        )
        
        # Save
        with open(output_path, 'w') as f:
            json.dump(document.to_dict(), f, indent=2)
        
        print(f"✓ Successfully saved to {output_path}")
        print(f"  Extracted {len(extracted_statements)}/{len(statements)} statements")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

async def main():
    """Extract the missing PDF (duplicate major depression file)."""
    
    failed_pdfs = [
        "qs-major-depression-quality-standard-en-2024 (1).pdf"  # The duplicate file that wasn't extracted
    ]
    
    input_dir = Path("data/dr_opa_agent/raw/oh_quality_std")
    output_dir = Path("data/dr_opa_agent/processed/quality_standards/extracted_v3/run_20251001_224304")
    
    print("=" * 60)
    print(f"EXTRACTING MISSING {len(failed_pdfs)} QUALITY STANDARD")
    print("=" * 60)
    
    success_count = 0
    
    for pdf_name in failed_pdfs:
        pdf_path = str(input_dir / pdf_name)
        output_path = str(output_dir / f"{Path(pdf_name).stem}.json")
        
        result = await extract_with_custom_toc(pdf_path, output_path)
        if result:
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"EXTRACTION COMPLETE: {success_count}/{len(failed_pdfs)} PDFs extracted")
    print("=" * 60)

if __name__ == "__main__":
    import os
    # Ensure API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        print("Please run: export OPENAI_API_KEY=your_key_here")
        sys.exit(1)
    
    asyncio.run(main())