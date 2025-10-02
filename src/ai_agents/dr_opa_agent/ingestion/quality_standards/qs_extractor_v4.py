"""
Quality Standards PDF Extractor V4 - Enhanced with support for alternative TOC formats.

This version handles PDFs where quality statements are listed without "Statement" prefix.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import PyPDF2
from openai import AsyncOpenAI
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class FrontMatter:
    """Container for front matter content."""
    executive_summary: str
    scope: str
    why_needed: str
    how_measured: str
    definitions: str
    principles: str
    for_patients: str
    for_clinicians: str
    system_support: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QualityStatement:
    """Container for a single quality statement."""
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
    """Container for the complete quality standard document."""
    title: str
    year: Optional[int]
    front_matter: FrontMatter
    total_statements: int
    statements: List[QualityStatement]
    source_file: str
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "year": self.year,
            "front_matter": self.front_matter.to_dict(),
            "total_statements": self.total_statements,
            "statements": [stmt.to_dict() for stmt in self.statements],
            "source_file": self.source_file
        }


class QualityStandardsExtractorV4:
    """Enhanced extractor for Quality Standards PDFs with multiple TOC format support."""
    
    def __init__(self):
        """Initialize the extractor with OpenAI client."""
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60.0
        )
        
        # Front matter extraction prompt (unchanged)
        self.front_matter_prompt = """Extract the following front matter sections from this Quality Standard document:

1. Executive Summary: Brief overview of the quality standard
2. Scope: What the quality standard covers and doesn't cover  
3. Why Needed: Rationale and evidence for why this quality standard is important
4. How Measured: How quality will be measured and monitored
5. Definitions: Key terms and definitions used in the document
6. Principles: Guiding principles underlying the quality standard
7. For Patients: Information specifically for patients and families
8. For Clinicians: Information specifically for health care providers
9. System Support: System-level support needed for implementation

Return as JSON with these exact keys:
{
    "executive_summary": "...",
    "scope": "...",
    "why_needed": "...", 
    "how_measured": "...",
    "definitions": "...",
    "principles": "...",
    "for_patients": "...",
    "for_clinicians": "...",
    "system_support": "..."
}

If a section is not found, use an empty string."""

        # Statement extraction prompt (unchanged)
        self.statement_prompt = """Extract the following information from this Quality Statement section:

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
        """Extract text from specific pages of the PDF."""
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
    
    def find_table_of_contents_page(self, pdf_path: str) -> Optional[Tuple[int, str]]:
        """Find the Table of Contents page in the PDF."""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Typically in first 10 pages
            for i in range(min(10, len(reader.pages))):
                text = reader.pages[i].extract_text()
                
                # Look for "Table of Contents" header
                if "Table of Contents" in text:
                    # Check if this page has quality statements
                    quality_stmt_count = text.count("Quality Statement")
                    
                    # Also check for alternative format (items under "Quality Statements to Improve Care")
                    if quality_stmt_count == 0:
                        # Look for section with numbered items
                        if "Quality Statements to Improve Care" in text:
                            # Count potential statement entries (looking for patterns with page numbers)
                            # Pattern: text followed by dots and page number
                            pattern = r'[A-Z][^\.]+\.+\s*\d{1,3}'
                            matches = re.findall(pattern, text)
                            if len(matches) >= 3:  # At least 3 items that look like TOC entries
                                logger.info(f"Found alternative TOC format on page {i+1}")
                                return (i+1, text)
                    
                    if quality_stmt_count > 0:
                        logger.info(f"Found Table of Contents on page {i+1}")
                        return (i+1, text)
                    elif "Quality Statement" in text.replace("\n", " "):
                        # Sometimes broken across lines
                        logger.info(f"Found likely Table of Contents on page {i+1} (has {quality_stmt_count} quality statements)")
                        return (i+1, text)
        
        logger.warning("Table of Contents not found")
        return None
    
    def parse_table_of_contents(self, toc_text: str) -> Dict[int, Tuple[str, int]]:
        """
        Parse the Table of Contents to extract quality statement entries.
        Now handles both standard format and alternative format.
        """
        statements = {}
        
        # First try standard format (with "Quality Statement X:")
        lines = toc_text.split('\n')
        
        for line in lines:
            # Standard format: Quality Statement X: Title
            if 'Quality Statement' in line:
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
        
        # If no statements found, try alternative format
        if not statements:
            logger.info("Trying alternative TOC format...")
            
            # Find the section with quality statements
            in_statements_section = False
            stmt_num = 0
            
            for i, line in enumerate(lines):
                # Look for the quality statements section
                if "Quality Statements to Improve Care" in line and i < len(lines) - 1:
                    # Check if next line has dots/page numbers (indicates subsection, not items)
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    if "..." in next_line or re.search(r'\.\s*\d+$', next_line):
                        continue  # This is the TOC entry for the section itself
                    in_statements_section = True
                    continue
                
                # Look for section end markers
                if in_statements_section:
                    if any(marker in line for marker in ["Appendices", "Emerging Practice", "References", "About Us"]):
                        break
                    
                    # Try to parse statement entries
                    # Pattern 1: Title with dots and page number
                    pattern1 = r'^([A-Z][^\.]+?)\.+\s*(\d{1,3})\s*$'
                    # Pattern 2: Title with page number (no dots)
                    pattern2 = r'^([A-Z][^\d]+?)\s+(\d{1,3})\s*$'
                    
                    for pattern in [pattern1, pattern2]:
                        match = re.match(pattern, line.strip())
                        if match:
                            stmt_num += 1
                            title = match.group(1).strip()
                            page = int(match.group(2))
                            
                            # Clean up title
                            title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
                            
                            statements[stmt_num] = (title, page)
                            logger.info(f"Found Statement {stmt_num}: {title} on page {page}")
                            break
        
        return statements
    
    def infer_statement_boundaries(self, toc_statements: Dict[int, Tuple[str, int]], 
                                  pdf_path: str) -> Dict[int, Tuple[int, int]]:
        """Infer page boundaries for each quality statement from TOC."""
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
                # For last statement, look for appendices or estimate
                end_page = min(start_page + 4, total_pages)
            
            boundaries[stmt_num] = (start_page, end_page)
            logger.info(f"Statement {stmt_num} boundaries: pages {start_page}-{end_page}")
        
        return boundaries
    
    async def extract_front_matter(self, pdf_path: str, first_statement_page: int) -> FrontMatter:
        """Extract front matter content from the PDF."""
        logger.info(f"Extracting front matter (pages 1 to {first_statement_page-1})")
        
        # Extract all pages before first statement
        all_front_matter = self.extract_pages(pdf_path, 1, first_statement_page - 1)
        
        # Use LLM to structure the content
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.front_matter_prompt},
                {"role": "user", "content": all_front_matter}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=3000
        )
        
        data = json.loads(response.choices[0].message.content)
        
        logger.info("Successfully extracted front matter")
        return FrontMatter(**data)
    
    async def extract_statement_with_llm(self, text: str, stmt_num: int, title: str) -> Optional[QualityStatement]:
        """Use LLM to extract structured information from statement text."""
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
                temperature=0.1,
                max_tokens=2000
            )
            
            data = json.loads(response.choices[0].message.content)
            
            # Ensure statement number and title match
            data["number"] = stmt_num
            if not data.get("title"):
                data["title"] = title
            
            return QualityStatement(**data)
            
        except Exception as e:
            logger.error(f"Failed to extract statement {stmt_num}: {e}")
            return None
    
    async def extract_document(self, pdf_path: str, output_path: str) -> QualityStandardDocument:
        """
        Extract complete Quality Standard document with front matter and statements.
        """
        logger.info(f"Extracting Quality Standard from: {pdf_path}")
        
        # Find Table of Contents
        toc_result = self.find_table_of_contents_page(pdf_path)
        if not toc_result:
            raise ValueError("Could not find Table of Contents")
        
        toc_page, toc_text = toc_result
        
        # Parse TOC to get quality statements
        toc_statements = self.parse_table_of_contents(toc_text)
        
        if not toc_statements:
            logger.error("No quality statements found in Table of Contents")
            raise ValueError("Could not parse quality statements from Table of Contents")
        
        logger.info(f"Found {len(toc_statements)} quality statements in TOC")
        
        # Infer page boundaries
        boundaries = self.infer_statement_boundaries(toc_statements, pdf_path)
        
        # Extract front matter (everything before first statement)
        first_statement_page = min(page for _, page in toc_statements.values())
        front_matter = await self.extract_front_matter(pdf_path, first_statement_page)
        
        # Extract each quality statement
        statements = []
        
        for stmt_num in sorted(toc_statements.keys()):
            title, _ = toc_statements[stmt_num]
            start_page, end_page = boundaries[stmt_num]
            
            logger.info(f"Extracting Statement {stmt_num}: {title} (pages {start_page}-{end_page})")
            
            # Extract text for this statement
            stmt_text = self.extract_pages(pdf_path, start_page, end_page)
            
            # Use LLM to structure the content
            statement = await self.extract_statement_with_llm(stmt_text, stmt_num, title)
            
            if statement:
                statements.append(statement)
                logger.info(f"Successfully extracted Statement {stmt_num}")
            else:
                logger.warning(f"Failed to extract Statement {stmt_num}")
        
        # Extract document title from PDF
        title = "Unknown Quality Standard"
        year = None
        
        # Try to extract title from first page
        first_page_text = self.extract_pages(pdf_path, 1, 1)
        title_match = re.search(r'([\w\s\-,&]+?)(?:Quality Standard|QUALITY STANDARD)', first_page_text)
        if title_match:
            title = title_match.group(1).strip()
        
        # Try to extract year
        year_match = re.search(r'20\d{2}', first_page_text)
        if year_match:
            year = int(year_match.group())
        
        # Create document
        document = QualityStandardDocument(
            title=title,
            year=year,
            front_matter=front_matter,
            total_statements=len(statements),
            statements=statements,
            source_file=pdf_path
        )
        
        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(document.to_dict(), f, indent=2)
        
        logger.info(f"Saved extraction to {output_path}")
        logger.info(f"Extraction complete: {len(statements)}/{len(toc_statements)} statements extracted")
        
        return document