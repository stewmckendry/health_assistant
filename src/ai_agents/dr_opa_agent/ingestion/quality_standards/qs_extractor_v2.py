"""
Quality Standards extractor v2 - finds and parses Table of Contents page.

This improved extractor:
1. Searches for the "Table of Contents" page
2. Extracts all quality statement entries from TOC
3. Infers page boundaries from TOC entries
4. Extracts each statement using LLM
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import PyPDF2
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class QualityStatement:
    """Represents a single quality statement with all components."""
    number: int
    title: str
    brief_statement: str
    full_statement: str
    background: str
    for_patients: str
    for_clinicians: str
    for_health_services: str
    indicators: List[str]
    sources: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QualityStandardDocument:
    """Represents a complete Quality Standard document."""
    title: str
    year: Optional[int]
    scope: str
    total_statements: int
    statements: List[QualityStatement]
    source_file: str
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'year': self.year,
            'scope': self.scope,
            'total_statements': self.total_statements,
            'statements': [stmt.to_dict() for stmt in self.statements],
            'source_file': self.source_file
        }


class QualityStandardsExtractorV2:
    """Improved extractor that finds and parses the Table of Contents."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the extractor.
        
        Args:
            openai_api_key: OpenAI API key (will use env var if not provided)
        """
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key required for extraction")
        
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Extraction prompt for LLM
        self.extraction_prompt = """You are extracting content from an Ontario Health Quality Standard document.

Extract the following information from this quality statement section:

1. Statement Number (integer)
2. Statement Title (the title after the number)
3. Brief Statement (the bold summary paragraph that describes what should be done)
4. Full Detailed Statement (complete description)
5. Background/Rationale (why this is important, evidence base)
6. What This Means for Patients (patient perspective and expectations)
7. What This Means for Clinicians (clinical practice implications)
8. What This Means for Health Services (system-level implications)
9. Quality Indicators (specific measurable indicators)
10. Sources/References (key citations)

Return as JSON with this exact structure:
{
    "number": 1,
    "title": "Statement Title",
    "brief_statement": "The concise statement of what should be done",
    "full_statement": "The complete detailed statement",
    "background": "Background and rationale text",
    "for_patients": "What patients should know and expect",
    "for_clinicians": "What clinicians should do",
    "for_health_services": "System-level requirements",
    "indicators": ["Indicator 1", "Indicator 2"],
    "sources": ["Source 1", "Source 2"]
}

If a section is not found, use an empty string or empty list as appropriate."""
    
    def find_table_of_contents_page(self, pdf_path: str) -> Optional[Tuple[int, str]]:
        """
        Find the page containing the Table of Contents.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (page_number, page_text) or None if not found
        """
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Search first 10 pages for Table of Contents
            for i in range(min(10, len(reader.pages))):
                text = reader.pages[i].extract_text()
                
                # Look for "Table of Contents" header or page with multiple quality statements
                if re.search(r'Table\s+of\s+Contents', text, re.IGNORECASE):
                    logger.info(f"Found Table of Contents on page {i+1}")
                    return (i+1, text)
                
                # Alternative: Check if page has multiple "Quality Statement" references with page numbers
                # This handles PDFs where TOC doesn't have explicit "Table of Contents" header
                quality_stmt_count = len(re.findall(r'Quality Statement\s+\d+:', text, re.IGNORECASE))
                if quality_stmt_count >= 5:  # If we see 5+ quality statements, likely a TOC
                    # Also check for page numbers
                    if re.search(r'\d+\s*$', text, re.MULTILINE):
                        logger.info(f"Found likely Table of Contents on page {i+1} (has {quality_stmt_count} quality statements)")
                        return (i+1, text)
        
        logger.warning("Table of Contents not found")
        return None
    
    def parse_table_of_contents(self, toc_text: str) -> Dict[int, Tuple[str, int]]:
        """
        Parse the Table of Contents to extract quality statement entries.
        
        Args:
            toc_text: Text from the Table of Contents page
            
        Returns:
            Dictionary mapping statement number to (title, page_number)
        """
        statements = {}
        
        # Split into lines for easier processing
        lines = toc_text.split('\n')
        
        for i, line in enumerate(lines):
            # Look for quality statement patterns
            # Pattern 1: "Quality Statement N: Title ........... Page"
            # Pattern 2: "Quality Statement N: Title Page"
            
            # First check if line contains "Quality Statement"
            if 'Quality Statement' in line:
                # Try to extract number, title, and page
                
                # Method 1: Look for pattern with dots
                match = re.search(r'Quality Statement\s+(\d+):\s*([^\.]+?)\.+\s*(\d+)', line)
                
                if not match:
                    # Method 2: Look for pattern without dots (spaces as separator)
                    # This is tricky because title might have numbers
                    # Look for the last number in the line as the page number
                    match = re.search(r'Quality Statement\s+(\d+):\s*(.+)', line)
                    if match:
                        stmt_num = int(match.group(1))
                        rest = match.group(2)
                        
                        # Find the last number in the string (likely the page number)
                        page_numbers = re.findall(r'\d+', rest)
                        if page_numbers:
                            page = int(page_numbers[-1])
                            # Remove the page number from the title
                            title = re.sub(r'\s*' + str(page) + r'\s*$', '', rest).strip()
                            
                            statements[stmt_num] = (title, page)
                            logger.info(f"Found Statement {stmt_num}: {title} on page {page}")
                else:
                    stmt_num = int(match.group(1))
                    title = match.group(2).strip()
                    page = int(match.group(3))
                    
                    statements[stmt_num] = (title, page)
                    logger.info(f"Found Statement {stmt_num}: {title} on page {page}")
        
        # If we didn't find statements with "Quality Statement", try simpler patterns
        if not statements:
            logger.info("Trying alternative TOC parsing patterns...")
            
            for line in lines:
                # Look for numbered statements (e.g., "1. Title ... Page")
                match = re.search(r'^(\d+)\.\s+([^\.]+?)\.+\s*(\d+)', line)
                if match:
                    stmt_num = int(match.group(1))
                    title = match.group(2).strip()
                    page = int(match.group(3))
                    
                    # Only consider it a quality statement if number is reasonable (1-20)
                    if 1 <= stmt_num <= 20:
                        statements[stmt_num] = (title, page)
                        logger.info(f"Found Statement {stmt_num}: {title} on page {page}")
        
        return statements
    
    def extract_statement_pages(self, pdf_path: str, start_page: int, end_page: Optional[int] = None) -> str:
        """
        Extract text from specific pages of the PDF.
        
        Args:
            pdf_path: Path to the PDF
            start_page: Starting page (1-indexed)
            end_page: Ending page (1-indexed), or None for just one page
            
        Returns:
            Extracted text
        """
        text = ""
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Convert to 0-indexed
            start_idx = start_page - 1
            end_idx = end_page - 1 if end_page else start_idx
            
            # Ensure valid range
            end_idx = min(end_idx, len(reader.pages) - 1)
            
            for i in range(start_idx, end_idx + 1):
                if i >= 0 and i < len(reader.pages):
                    text += reader.pages[i].extract_text() + "\n\n"
        
        return text
    
    def infer_statement_boundaries(self, toc_statements: Dict[int, Tuple[str, int]], 
                                  pdf_path: str) -> Dict[int, Tuple[int, int]]:
        """
        Infer page boundaries for each quality statement from TOC.
        
        Args:
            toc_statements: Dictionary from parse_table_of_contents
            pdf_path: Path to PDF to get total pages
            
        Returns:
            Dictionary mapping statement number to (start_page, end_page)
        """
        boundaries = {}
        
        # Get total pages in PDF
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
        
        # Sort statements by number
        sorted_statements = sorted(toc_statements.items())
        
        for i, (stmt_num, (title, start_page)) in enumerate(sorted_statements):
            # End page is one before next statement starts
            if i < len(sorted_statements) - 1:
                next_start = sorted_statements[i + 1][1][1]
                end_page = next_start - 1
            else:
                # For last statement, look for appendix or estimate 3-4 pages
                # Check if there's an appendix entry in TOC
                end_page = min(start_page + 3, total_pages)
            
            boundaries[stmt_num] = (start_page, end_page)
            logger.info(f"Statement {stmt_num} boundaries: pages {start_page}-{end_page}")
        
        return boundaries
    
    async def extract_statement_with_llm(self, text: str, stmt_num: int, title: str) -> Optional[QualityStatement]:
        """
        Use LLM to extract structured information from statement text.
        
        Args:
            text: Raw text of the quality statement section
            stmt_num: Statement number
            title: Statement title from TOC
            
        Returns:
            Extracted QualityStatement or None if extraction fails
        """
        try:
            # Add context about expected statement
            context_prompt = f"You are extracting Quality Statement {stmt_num}: {title}\n\n"
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.extraction_prompt},
                    {"role": "user", "content": context_prompt + text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1  # Low temperature for consistency
            )
            
            data = json.loads(response.choices[0].message.content)
            
            # Create QualityStatement object
            statement = QualityStatement(
                number=data.get('number', stmt_num),
                title=data.get('title', title),
                brief_statement=data.get('brief_statement', ''),
                full_statement=data.get('full_statement', ''),
                background=data.get('background', ''),
                for_patients=data.get('for_patients', ''),
                for_clinicians=data.get('for_clinicians', ''),
                for_health_services=data.get('for_health_services', ''),
                indicators=data.get('indicators', []),
                sources=data.get('sources', [])
            )
            
            return statement
            
        except Exception as e:
            logger.error(f"Error extracting statement {stmt_num}: {e}")
            return None
    
    def extract_document_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from the document front matter.
        
        Args:
            pdf_path: Path to the PDF
            
        Returns:
            Dictionary with metadata
        """
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract from first 5 pages
            front_matter = ""
            for i in range(min(5, len(reader.pages))):
                front_matter += reader.pages[i].extract_text()
            
            # Extract title (usually contains condition name)
            title = ""
            # Look for common condition names in the front matter
            condition_patterns = [
                r'(Chronic\s+Obstructive\s+Pulmonary\s+Disease)',
                r'(COPD)',
                r'(Chronic\s+Pain)',
                r'(Heart\s+Failure)',
                r'(Diabetes)',
                r'(Depression)',
                r'(Anxiety)',
                r'(Hypertension)',
                r'(Asthma)',
                r'(Palliative\s+Care)',
                r'(Schizophrenia)',
                r'(Opioid)',
                r'(Quality\s+Standard[^\.]+)',  # Fallback to capture full quality standard title
            ]
            
            for pattern in condition_patterns:
                match = re.search(pattern, front_matter, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    break
            
            # Extract year
            year = None
            year_match = re.search(r'20(2[0-5]|1[0-9])', front_matter)
            if year_match:
                year = int(year_match.group(0))
            
            # Extract scope
            scope = ""
            scope_match = re.search(r'Scope[:\s]+([^.]+\.)', front_matter, re.IGNORECASE)
            if scope_match:
                scope = scope_match.group(1).strip()
            
            return {
                'title': title,
                'year': year,
                'scope': scope,
                'total_pages': len(reader.pages)
            }
    
    async def extract_document(self, pdf_path: str, 
                             output_path: Optional[str] = None,
                             max_statements: Optional[int] = None) -> QualityStandardDocument:
        """
        Extract complete Quality Standard document.
        
        Args:
            pdf_path: Path to the PDF file
            output_path: Optional path to save JSON output
            max_statements: Optional limit on number of statements to extract
            
        Returns:
            Extracted QualityStandardDocument
        """
        logger.info(f"Extracting Quality Standard from: {pdf_path}")
        
        # Find Table of Contents page
        toc_result = self.find_table_of_contents_page(pdf_path)
        if not toc_result:
            raise ValueError("Could not find Table of Contents in PDF")
        
        toc_page_num, toc_text = toc_result
        
        # Parse Table of Contents
        toc_statements = self.parse_table_of_contents(toc_text)
        
        if not toc_statements:
            logger.error("No quality statements found in Table of Contents")
            # Log the TOC text for debugging
            logger.debug(f"TOC text:\n{toc_text[:1000]}")
            raise ValueError("Could not parse quality statements from Table of Contents")
        
        logger.info(f"Found {len(toc_statements)} quality statements in TOC")
        
        # Infer statement boundaries
        boundaries = self.infer_statement_boundaries(toc_statements, pdf_path)
        
        # Extract metadata
        metadata = self.extract_document_metadata(pdf_path)
        
        # Extract each statement
        statements = []
        items_to_extract = list(toc_statements.items())
        if max_statements:
            items_to_extract = items_to_extract[:max_statements]
        
        for stmt_num, (title, _) in items_to_extract:
            start_page, end_page = boundaries[stmt_num]
            
            logger.info(f"Extracting Statement {stmt_num}: {title} (pages {start_page}-{end_page})")
            
            # Extract pages
            text = self.extract_statement_pages(pdf_path, start_page, end_page)
            
            # Extract with LLM
            statement = await self.extract_statement_with_llm(text, stmt_num, title)
            
            if statement:
                statements.append(statement)
                logger.info(f"Successfully extracted Statement {stmt_num}")
            else:
                logger.warning(f"Failed to extract Statement {stmt_num}")
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # Create document object
        document = QualityStandardDocument(
            title=metadata['title'] or Path(pdf_path).stem,
            year=metadata['year'],
            scope=metadata['scope'],
            total_statements=len(statements),
            statements=statements,
            source_file=str(pdf_path)
        )
        
        # Save if requested
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(document.to_dict(), f, indent=2)
            logger.info(f"Saved extraction to {output_file}")
        
        logger.info(f"Extraction complete: {len(statements)}/{len(toc_statements)} statements extracted")
        
        return document


async def test_extractor():
    """Test the improved extractor on sample PDFs."""
    
    # Test PDFs
    test_pdfs = [
        "data/dr_opa_agent/raw/oh_quality_std/qs-chronic-pain-quality-standard-en.pdf",
        "data/dr_opa_agent/raw/oh_quality_std/qs-chronic-obstructive-pulmonary-disease-quality-standard-2023-en.pdf",
        "data/dr_opa_agent/raw/oh_quality_std/qs-heart-failure-quality-standard-en.pdf"
    ]
    
    extractor = QualityStandardsExtractorV2()
    
    for pdf_path in test_pdfs:
        if not Path(pdf_path).exists():
            logger.warning(f"PDF not found: {pdf_path}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Testing: {Path(pdf_path).name}")
        print('='*60)
        
        try:
            # Extract with limit for testing
            output_name = Path(pdf_path).stem + "_extracted.json"
            output_path = f"data/dr_opa_agent/processed/quality_standards/extracted/{output_name}"
            
            document = await extractor.extract_document(
                pdf_path, 
                output_path, 
                max_statements=3  # Limit for testing
            )
            
            print(f"✓ Extracted: {document.title}")
            print(f"  Year: {document.year}")
            print(f"  Statements extracted: {document.total_statements}")
            
            for stmt in document.statements[:2]:  # Show first 2
                print(f"\n  Statement {stmt.number}: {stmt.title}")
                brief = stmt.brief_statement[:80] + "..." if len(stmt.brief_statement) > 80 else stmt.brief_statement
                print(f"    Brief: {brief}")
                print(f"    Has subsections: Patient={bool(stmt.for_patients)}, "
                      f"Clinical={bool(stmt.for_clinicians)}, "
                      f"Indicators={len(stmt.indicators)}")
        
        except Exception as e:
            print(f"✗ Failed: {e}")
            logger.error(f"Failed to extract {pdf_path}: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_extractor())