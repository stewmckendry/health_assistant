"""
Quality Standards extractor v3 - Extracts both front matter and quality statements.

Enhanced extractor that captures:
1. Front matter (scope, why needed, definitions, etc.)
2. Table of Contents
3. All quality statements with subsections
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
class FrontMatter:
    """Represents the front matter content of a Quality Standard."""
    executive_summary: str
    scope: str
    why_needed: str
    how_measured: str
    definitions: str
    principles: str
    for_patients: str  # How patients can use this standard
    for_clinicians: str  # How clinicians can use this standard
    system_support: str  # How the system can support implementation
    
    def to_dict(self) -> Dict:
        return asdict(self)


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
    """Represents a complete Quality Standard document with front matter."""
    title: str
    year: Optional[int]
    front_matter: FrontMatter
    total_statements: int
    statements: List[QualityStatement]
    source_file: str
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'year': self.year,
            'front_matter': self.front_matter.to_dict(),
            'total_statements': self.total_statements,
            'statements': [stmt.to_dict() for stmt in self.statements],
            'source_file': self.source_file
        }


class QualityStandardsExtractorV3:
    """Enhanced extractor with front matter extraction."""
    
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
        
        # Front matter extraction prompt
        self.front_matter_prompt = """You are extracting front matter content from an Ontario Health Quality Standard document.

Extract the following sections from the provided text:

1. **Executive Summary**: The brief overview of the quality standard (may be called "Quality Statements to Improve Care" section)
2. **Scope**: What the quality standard covers, who it applies to (from "Scope of This Quality Standard" section)
3. **Why This Quality Standard Is Needed**: Statistics, prevalence, care gaps, rationale
4. **How Success Can Be Measured**: System-level indicators and measurement approach (from "How to Measure Overall Success" section)
5. **Definitions**: Key terms, acronyms, and their definitions (may be in various sections)
6. **Values and Guiding Principles**: Core principles guiding the standard (from "Values That Are the Foundation" section)
7. **How to Use - For Patients**: Guidance for patients on using the quality standard
8. **How to Use - For Clinicians**: Guidance for clinicians and organizations
9. **System Support**: How the health care system can support implementation

Return as JSON with this structure:
{
    "executive_summary": "Summary text or quality statements overview",
    "scope": "Scope description",
    "why_needed": "Rationale and statistics", 
    "how_measured": "Overall success measurement approach",
    "definitions": "Key definitions and terminology",
    "principles": "Values and guiding principles",
    "for_patients": "How patients can use this standard",
    "for_clinicians": "How clinicians can use this standard",
    "system_support": "How the system can support implementation"
}

Extract the actual content, not just a description. If a section is not found, use an empty string."""
        
        # Quality statement extraction prompt (same as v2)
        self.statement_prompt = """You are extracting content from an Ontario Health Quality Standard document.

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
    
    def extract_pages(self, pdf_path: str, start_page: int, end_page: int) -> str:
        """
        Extract text from specific pages of the PDF.
        
        Args:
            pdf_path: Path to the PDF
            start_page: Starting page (1-indexed)
            end_page: Ending page (1-indexed)
            
        Returns:
            Extracted text
        """
        text = ""
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Convert to 0-indexed
            start_idx = start_page - 1
            end_idx = end_page - 1
            
            # Ensure valid range
            end_idx = min(end_idx, len(reader.pages) - 1)
            
            for i in range(max(0, start_idx), end_idx + 1):
                if i < len(reader.pages):
                    text += reader.pages[i].extract_text() + "\n\n"
        
        return text
    
    async def extract_front_matter(self, pdf_path: str, first_statement_page: int) -> FrontMatter:
        """
        Extract front matter content from the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            first_statement_page: Page where first quality statement begins
            
        Returns:
            Extracted FrontMatter object
        """
        logger.info(f"Extracting front matter (pages 1 to {first_statement_page-1})")
        
        # Extract ALL pages before the first quality statement
        # This ensures we capture all front matter sections including:
        # - About This Quality Standard
        # - What Is a Quality Standard?
        # - Values/Foundation
        # - Quality Statements summary
        # - Scope
        # - Why Needed
        # - How to Use (for patients, clinicians, organizations)
        # - How System Can Support
        # - How to Measure Success
        all_front_matter = self.extract_pages(pdf_path, 1, first_statement_page - 1)
        
        try:
            # Use LLM to extract structured front matter
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.front_matter_prompt},
                    {"role": "user", "content": all_front_matter}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            data = json.loads(response.choices[0].message.content)
            
            front_matter = FrontMatter(
                executive_summary=data.get('executive_summary', ''),
                scope=data.get('scope', ''),
                why_needed=data.get('why_needed', ''),
                how_measured=data.get('how_measured', ''),
                definitions=data.get('definitions', ''),
                principles=data.get('principles', ''),
                for_patients=data.get('for_patients', ''),
                for_clinicians=data.get('for_clinicians', ''),
                system_support=data.get('system_support', '')
            )
            
            logger.info("Successfully extracted front matter")
            return front_matter
            
        except Exception as e:
            logger.error(f"Error extracting front matter: {e}")
            # Return empty front matter on error
            return FrontMatter('', '', '', '', '', '', '', '', '')
    
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
        
        for line in lines:
            # Look for quality statement patterns
            if 'Quality Statement' in line:
                # Try multiple patterns
                patterns = [
                    r'Quality Statement\s+(\d+):\s*([^\.]+?)\.+\s*(\d+)',  # With dots
                    r'Quality Statement\s+(\d+):\s*([^\d]+?)\s+(\d+)',     # With spaces
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        stmt_num = int(match.group(1))
                        title = match.group(2).strip()
                        page = int(match.group(3))
                        
                        statements[stmt_num] = (title, page)
                        logger.info(f"Found Statement {stmt_num}: {title} on page {page}")
                        break
        
        return statements
    
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
                # For last statement, estimate 3-4 pages
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
                    {"role": "system", "content": self.statement_prompt},
                    {"role": "user", "content": context_prompt + text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
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
    
    def extract_document_title(self, pdf_path: str, front_matter: FrontMatter) -> str:
        """
        Extract document title from PDF name and front matter.
        
        Args:
            pdf_path: Path to PDF
            front_matter: Extracted front matter
            
        Returns:
            Document title
        """
        # Try to extract from front matter scope
        if front_matter.scope:
            # Look for condition names in scope
            conditions = [
                'Chronic Obstructive Pulmonary Disease', 'COPD',
                'Chronic Pain', 'Heart Failure', 'Diabetes',
                'Depression', 'Anxiety', 'Hypertension', 'Asthma',
                'Palliative Care', 'Schizophrenia', 'Opioid'
            ]
            
            for condition in conditions:
                if condition.lower() in front_matter.scope.lower():
                    return condition
        
        # Fallback to filename
        filename = Path(pdf_path).stem
        # Clean up filename
        title = filename.replace('qs-', '').replace('-quality-standard', '')
        title = title.replace('-en', '').replace('-', ' ')
        return title.title()
    
    async def extract_document(self, pdf_path: str, 
                             output_path: Optional[str] = None,
                             max_statements: Optional[int] = None) -> QualityStandardDocument:
        """
        Extract complete Quality Standard document including front matter.
        
        Args:
            pdf_path: Path to the PDF file
            output_path: Optional path to save JSON output
            max_statements: Optional limit on number of statements to extract
            
        Returns:
            Extracted QualityStandardDocument with front matter
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
            raise ValueError("Could not parse quality statements from Table of Contents")
        
        logger.info(f"Found {len(toc_statements)} quality statements in TOC")
        
        # Infer statement boundaries
        boundaries = self.infer_statement_boundaries(toc_statements, pdf_path)
        
        # Get first statement page for front matter extraction
        first_statement_page = min(page for _, page in toc_statements.values()) if toc_statements else 999
        
        # Extract front matter (everything before first quality statement)
        front_matter = await self.extract_front_matter(pdf_path, first_statement_page)
        
        # Extract title and metadata
        title = self.extract_document_title(pdf_path, front_matter)
        
        # Extract year from front matter or filename
        year = None
        year_match = re.search(r'20(2[0-5]|1[0-9])', front_matter.scope + ' ' + str(pdf_path))
        if year_match:
            year = int(year_match.group(0))
        
        # Extract each statement
        statements = []
        items_to_extract = list(toc_statements.items())
        if max_statements:
            items_to_extract = items_to_extract[:max_statements]
        
        for stmt_num, (stmt_title, _) in items_to_extract:
            start_page, end_page = boundaries[stmt_num]
            
            logger.info(f"Extracting Statement {stmt_num}: {stmt_title} (pages {start_page}-{end_page})")
            
            # Extract pages
            text = self.extract_pages(pdf_path, start_page, end_page)
            
            # Extract with LLM
            statement = await self.extract_statement_with_llm(text, stmt_num, stmt_title)
            
            if statement:
                statements.append(statement)
                logger.info(f"Successfully extracted Statement {stmt_num}")
            else:
                logger.warning(f"Failed to extract Statement {stmt_num}")
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # Create document object with front matter
        document = QualityStandardDocument(
            title=title,
            year=year,
            front_matter=front_matter,
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


async def test_enhanced_extractor():
    """Test the enhanced extractor with front matter extraction."""
    
    # Test on chronic pain PDF
    pdf_path = "data/dr_opa_agent/raw/oh_quality_std/qs-chronic-pain-quality-standard-en.pdf"
    output_path = "data/dr_opa_agent/processed/quality_standards/extracted/chronic_pain_v3.json"
    
    extractor = QualityStandardsExtractorV3()
    
    try:
        # Extract with front matter (limit to 2 statements for testing)
        document = await extractor.extract_document(pdf_path, output_path, max_statements=2)
        
        print(f"\n{'='*60}")
        print("ENHANCED EXTRACTION RESULTS")
        print('='*60)
        print(f"Document: {document.title}")
        print(f"Year: {document.year}")
        
        print(f"\nFRONT MATTER:")
        print(f"  Scope: {document.front_matter.scope[:150]}..." if document.front_matter.scope else "  Scope: Not found")
        print(f"  Why Needed: {document.front_matter.why_needed[:150]}..." if document.front_matter.why_needed else "  Why Needed: Not found")
        print(f"  How Measured: {document.front_matter.how_measured[:150]}..." if document.front_matter.how_measured else "  How Measured: Not found")
        print(f"  Has Definitions: {'Yes' if document.front_matter.definitions else 'No'}")
        print(f"  Has Principles: {'Yes' if document.front_matter.principles else 'No'}")
        
        print(f"\nQUALITY STATEMENTS: {document.total_statements}")
        for stmt in document.statements:
            print(f"  {stmt.number}. {stmt.title}")
            print(f"     Brief: {stmt.brief_statement[:100]}...")
        
        print('='*60)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_enhanced_extractor())