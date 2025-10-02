"""
Quality Standards extractor using LLM-based extraction for Ontario Health PDFs.

This extractor:
1. Uses Table of Contents to identify quality statement locations
2. Extracts each quality statement with all subsections
3. Uses LLM to structure the content into standardized format
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


class QualityStandardsExtractor:
    """Extracts quality statements from Ontario Health Quality Standards PDFs."""
    
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
    
    def parse_table_of_contents(self, pdf_path: str) -> Dict[int, Tuple[str, int]]:
        """
        Parse the Table of Contents to find quality statement locations.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary mapping statement number to (title, page_number)
        """
        statements = {}
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Table of Contents is usually in first 5 pages
            toc_text = ""
            for i in range(min(5, len(reader.pages))):
                toc_text += reader.pages[i].extract_text()
            
            # Pattern to match quality statements in TOC
            # Example: "Quality Statement 1:  Comprehensive Assessment  8"
            # Note: Some PDFs use spaces instead of dots as separators
            patterns = [
                r'Quality Statement\s+(\d+):\s*([^\d]+?)\s+(\d+)',  # Space separator
                r'Quality Statement\s+(\d+):\s*([^\.]+?)\.+\s*(\d+)'  # Dot separator
            ]
            
            # Try each pattern
            for pattern in patterns:
                matches = re.findall(pattern, toc_text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    for match in matches:
                        stmt_num = int(match[0])
                        title = match[1].strip()
                        page = int(match[2])
                        statements[stmt_num] = (title, page)
                        logger.info(f"Found in TOC: Statement {stmt_num}: {title} on page {page}")
                    break  # Stop if we found matches with this pattern
        
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
                if i < len(reader.pages):
                    text += reader.pages[i].extract_text() + "\n"
        
        return text
    
    def determine_statement_boundaries(self, toc_statements: Dict[int, Tuple[str, int]]) -> Dict[int, Tuple[int, int]]:
        """
        Determine page boundaries for each quality statement.
        
        Args:
            toc_statements: Dictionary from parse_table_of_contents
            
        Returns:
            Dictionary mapping statement number to (start_page, end_page)
        """
        boundaries = {}
        sorted_statements = sorted(toc_statements.items())
        
        for i, (stmt_num, (title, start_page)) in enumerate(sorted_statements):
            # End page is one before next statement, or estimate 3 pages if last
            if i < len(sorted_statements) - 1:
                next_start = sorted_statements[i + 1][1][1]
                end_page = next_start - 1
            else:
                # Last statement - typically 3-4 pages
                end_page = start_page + 3
            
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
            title_patterns = [
                r'(?:Quality Standard[\s\n]+)?([A-Za-z\s]+(?:Disorder|Disease|Care|Pain|Failure|Diabetes|COPD|Depression|Anxiety))',
                r'^([A-Z][A-Za-z\s]+)$'  # Title case line
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, front_matter, re.MULTILINE)
                if match:
                    title = match.group(1).strip()
                    if len(title) > 5 and len(title) < 100:
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
        
        # Parse Table of Contents
        toc_statements = self.parse_table_of_contents(pdf_path)
        
        if not toc_statements:
            logger.error("No quality statements found in Table of Contents")
            raise ValueError("Could not parse Table of Contents")
        
        # Get statement boundaries
        boundaries = self.determine_statement_boundaries(toc_statements)
        
        # Extract metadata
        metadata = self.extract_document_metadata(pdf_path)
        
        # Extract each statement
        statements = []
        items_to_extract = list(toc_statements.items())
        if max_statements:
            items_to_extract = items_to_extract[:max_statements]
        
        for stmt_num, (title, _) in items_to_extract:
            start_page, end_page = boundaries[stmt_num]
            
            logger.info(f"Extracting Statement {stmt_num}: {title}")
            
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
            title=metadata['title'],
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
    
    async def extract_all_documents(self, pdf_dir: str, 
                                   output_dir: Optional[str] = None,
                                   limit: Optional[int] = None) -> List[QualityStandardDocument]:
        """
        Extract all Quality Standards PDFs in a directory.
        
        Args:
            pdf_dir: Directory containing PDFs
            output_dir: Directory to save JSON outputs
            limit: Maximum number of PDFs to process
            
        Returns:
            List of extracted documents
        """
        pdf_path = Path(pdf_dir)
        pdf_files = list(pdf_path.glob("*.pdf"))
        
        if limit:
            pdf_files = pdf_files[:limit]
        
        logger.info(f"Processing {len(pdf_files)} PDF files")
        
        documents = []
        for pdf_file in pdf_files:
            try:
                output_path = None
                if output_dir:
                    output_path = Path(output_dir) / f"{pdf_file.stem}.json"
                
                document = await self.extract_document(str(pdf_file), output_path)
                documents.append(document)
                
            except Exception as e:
                logger.error(f"Failed to process {pdf_file.name}: {e}")
        
        return documents


async def test_extractor():
    """Test the extractor on a sample PDF."""
    
    # Test on COPD Quality Standard
    pdf_path = "data/dr_opa_agent/raw/oh_quality_std/qs-chronic-obstructive-pulmonary-disease-quality-standard-2023-en.pdf"
    output_path = "data/dr_opa_agent/processed/quality_standards/extracted/copd_test.json"
    
    extractor = QualityStandardsExtractor()
    
    # Extract just first 3 statements for testing
    document = await extractor.extract_document(pdf_path, output_path, max_statements=3)
    
    print(f"\nExtracted: {document.title}")
    print(f"Year: {document.year}")
    print(f"Total Statements: {document.total_statements}")
    
    for stmt in document.statements:
        print(f"\nStatement {stmt.number}: {stmt.title}")
        print(f"  Brief: {stmt.brief_statement[:100]}...")
        print(f"  Has patient info: {len(stmt.for_patients) > 0}")
        print(f"  Has clinical info: {len(stmt.for_clinicians) > 0}")
        print(f"  Indicators: {len(stmt.indicators)}")


if __name__ == "__main__":
    asyncio.run(test_extractor())