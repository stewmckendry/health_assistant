"""
Map Quality Standards PDF sections to identify quality statement boundaries.

Quality Standards PDFs have a consistent structure:
- Front matter (pages 1-7): Title, Summary, TOC, Scope
- Quality Statements (pages 8-50+): Numbered statements with subsections
- Appendices (pages 50+): Glossary, References

Each Quality Statement follows this pattern:
- "Quality Statement N: [Title]" header
- Brief statement (bold text)
- Background/rationale
- "What This Quality Statement Means" sections for Patients/Clinicians/Health Services
- Quality Indicators
- Additional Resources
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import PyPDF2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QualityStandardsSectionMapper:
    """Maps quality statement sections in Ontario Health Quality Standards PDFs."""
    
    # Patterns to identify key sections
    QUALITY_STATEMENT_PATTERN = r'Quality Statement\s+(\d+)\s*:?\s*([^\n]+)?'
    APPENDIX_PATTERNS = [
        r'Appendix',
        r'References',
        r'Glossary',
        r'About Ontario Health',
        r'Acknowledgements'
    ]
    
    # Subsection markers within quality statements
    SUBSECTION_MARKERS = {
        'background': [
            'Background',
            'Rationale',
            'Sources'
        ],
        'for_patients': [
            'What This Quality Statement Means',
            'For Patients',
            'Patients Should'
        ],
        'for_clinicians': [
            'For Clinicians',
            'Clinicians Should',
            'Health Care Professionals'
        ],
        'for_health_services': [
            'For Health Services',
            'Health Services Should',
            'Organizations Should'
        ],
        'indicators': [
            'Quality Indicators',
            'Indicators',
            'How to Measure'
        ]
    }
    
    def __init__(self, pdf_path: str):
        """
        Initialize the mapper with a PDF path.
        
        Args:
            pdf_path: Path to the Quality Standards PDF
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self.pdf_reader = None
        self.total_pages = 0
        self.pages_text = []
        
    def load_pdf(self) -> List[Tuple[int, str]]:
        """
        Load PDF and extract text from all pages.
        
        Returns:
            List of tuples (page_number, text) where page_number is 1-indexed
        """
        pages_text = []
        
        with open(self.pdf_path, 'rb') as file:
            self.pdf_reader = PyPDF2.PdfReader(file)
            self.total_pages = len(self.pdf_reader.pages)
            
            for page_num in range(self.total_pages):
                page = self.pdf_reader.pages[page_num]
                text = page.extract_text()
                # Store with 1-indexed page number for human readability
                pages_text.append((page_num + 1, text))
                
        self.pages_text = pages_text
        logger.info(f"Loaded {self.total_pages} pages from {self.pdf_path.name}")
        return pages_text
    
    def find_quality_statements(self) -> Dict[int, Dict]:
        """
        Find all quality statement sections in the PDF.
        
        Returns:
            Dictionary mapping statement number to metadata:
            {
                1: {
                    'title': 'Statement Title',
                    'start_page': 8,
                    'end_page': 12,
                    'subsections': {...}
                }
            }
        """
        if not self.pages_text:
            self.load_pdf()
        
        statements = {}
        current_statement = None
        
        for page_num, text in self.pages_text:
            # Check if this page starts a new quality statement
            match = re.search(self.QUALITY_STATEMENT_PATTERN, text, re.IGNORECASE)
            
            if match:
                # Save previous statement's end page
                if current_statement and current_statement['number'] in statements:
                    statements[current_statement['number']]['end_page'] = page_num - 1
                
                # Start new statement
                stmt_num = int(match.group(1))
                stmt_title = match.group(2).strip() if match.group(2) else ""
                
                current_statement = {
                    'number': stmt_num,
                    'title': stmt_title,
                    'start_page': page_num
                }
                
                statements[stmt_num] = {
                    'title': stmt_title,
                    'start_page': page_num,
                    'end_page': None,  # Will be set when next statement found
                    'subsections': self.find_subsections_on_page(text)
                }
                
                logger.info(f"Found Quality Statement {stmt_num}: '{stmt_title}' on page {page_num}")
            
            # Check if we've reached appendices (end of quality statements)
            elif any(re.search(pattern, text[:500], re.IGNORECASE) for pattern in self.APPENDIX_PATTERNS):
                if current_statement and current_statement['number'] in statements:
                    statements[current_statement['number']]['end_page'] = page_num - 1
                logger.info(f"Reached appendices on page {page_num}")
                break
            
            # If we're in a statement, check for subsections on this page
            elif current_statement:
                subsections = self.find_subsections_on_page(text)
                if subsections:
                    # Merge with existing subsections
                    for key, value in subsections.items():
                        if key not in statements[current_statement['number']]['subsections']:
                            statements[current_statement['number']]['subsections'][key] = value
        
        # Set end page for last statement if not set
        if current_statement and current_statement['number'] in statements:
            if statements[current_statement['number']]['end_page'] is None:
                # Find last content page before appendices
                for page_num, text in reversed(self.pages_text):
                    if not any(re.search(pattern, text[:500], re.IGNORECASE) 
                              for pattern in self.APPENDIX_PATTERNS):
                        statements[current_statement['number']]['end_page'] = page_num
                        break
        
        return statements
    
    def find_subsections_on_page(self, text: str) -> Dict[str, bool]:
        """
        Find which subsections are present on a page.
        
        Args:
            text: Page text to search
            
        Returns:
            Dictionary indicating which subsections were found
        """
        found_subsections = {}
        
        for subsection_key, markers in self.SUBSECTION_MARKERS.items():
            for marker in markers:
                if marker.lower() in text.lower():
                    found_subsections[subsection_key] = True
                    break
        
        return found_subsections
    
    def extract_metadata(self) -> Dict[str, any]:
        """
        Extract document metadata from front matter.
        
        Returns:
            Dictionary with document metadata
        """
        if not self.pages_text:
            self.load_pdf()
        
        # Combine first 5 pages for metadata extraction
        front_matter = ""
        for page_num, text in self.pages_text[:5]:
            front_matter += text + "\n"
        
        metadata = {
            'filename': self.pdf_path.name,
            'total_pages': self.total_pages,
            'title': self.extract_title(front_matter),
            'year': self.extract_year(front_matter),
            'scope': self.extract_scope(front_matter)
        }
        
        return metadata
    
    def extract_title(self, text: str) -> str:
        """Extract document title from front matter."""
        # Usually the first prominent text line
        lines = text.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if len(line) > 10 and not any(skip in line.lower() for skip in 
                                         ['ontario health', 'quality standard', 'page']):
                # Likely the condition title
                if any(keyword in line.lower() for keyword in 
                      ['diabetes', 'copd', 'heart', 'pain', 'depression', 'anxiety']):
                    return line
        return ""
    
    def extract_year(self, text: str) -> Optional[int]:
        """Extract publication year from front matter."""
        # Look for 4-digit year (2020-2025)
        year_matches = re.findall(r'20[2][0-5]', text)
        if year_matches:
            return int(year_matches[0])
        return None
    
    def extract_scope(self, text: str) -> str:
        """Extract scope statement from front matter."""
        # Look for scope section
        scope_match = re.search(r'Scope[:\s]+([^.]+\.)', text, re.IGNORECASE)
        if scope_match:
            return scope_match.group(1).strip()
        return ""
    
    def validate_mapping(self, statements: Dict[int, Dict]) -> Dict[str, any]:
        """
        Validate the quality of the mapping.
        
        Args:
            statements: Mapped quality statements
            
        Returns:
            Validation report
        """
        validation = {
            'total_statements': len(statements),
            'statements_with_titles': sum(1 for s in statements.values() if s['title']),
            'average_pages_per_statement': 0,
            'missing_subsections': [],
            'warnings': []
        }
        
        if statements:
            # Calculate average pages per statement
            total_pages = sum(
                (s['end_page'] - s['start_page'] + 1) 
                for s in statements.values() 
                if s['end_page']
            )
            validation['average_pages_per_statement'] = total_pages / len(statements)
            
            # Check for missing subsections
            for num, stmt in statements.items():
                missing = []
                for key in ['background', 'for_patients', 'for_clinicians']:
                    if key not in stmt['subsections']:
                        missing.append(key)
                if missing:
                    validation['missing_subsections'].append({
                        'statement': num,
                        'missing': missing
                    })
            
            # Warnings
            if validation['average_pages_per_statement'] < 2:
                validation['warnings'].append("Statements seem too short - may be missing content")
            if validation['average_pages_per_statement'] > 10:
                validation['warnings'].append("Statements seem too long - may be incorrectly bounded")
            if len(statements) < 5:
                validation['warnings'].append("Few statements found - may be missing some")
            if len(statements) > 20:
                validation['warnings'].append("Many statements found - may have false positives")
        
        return validation
    
    def map_document(self, output_path: Optional[str] = None) -> Dict[str, any]:
        """
        Main method to map the entire Quality Standards document.
        
        Args:
            output_path: Optional path to save the mapping JSON
            
        Returns:
            Complete mapping dictionary
        """
        logger.info(f"Mapping Quality Standards document: {self.pdf_path.name}")
        
        # Extract components
        metadata = self.extract_metadata()
        statements = self.find_quality_statements()
        validation = self.validate_mapping(statements)
        
        # Build complete mapping
        mapping = {
            'metadata': metadata,
            'quality_statements': statements,
            'validation': validation,
            'extraction_method': 'pattern_based',
            'patterns_used': {
                'statement_pattern': self.QUALITY_STATEMENT_PATTERN,
                'appendix_patterns': self.APPENDIX_PATTERNS
            }
        }
        
        # Save if requested
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(mapping, f, indent=2)
            logger.info(f"Saved mapping to {output_file}")
        
        # Log summary
        logger.info(f"Mapping complete: Found {len(statements)} quality statements")
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"Validation warning: {warning}")
        
        return mapping


def test_mapper(pdf_path: str):
    """
    Test the mapper on a single PDF.
    
    Args:
        pdf_path: Path to Quality Standards PDF
    """
    mapper = QualityStandardsSectionMapper(pdf_path)
    mapping = mapper.map_document()
    
    print(f"\n{'='*60}")
    print(f"Quality Standards Mapping: {Path(pdf_path).name}")
    print(f"{'='*60}")
    print(f"Title: {mapping['metadata']['title']}")
    print(f"Year: {mapping['metadata']['year']}")
    print(f"Total Pages: {mapping['metadata']['total_pages']}")
    print(f"\nQuality Statements Found: {len(mapping['quality_statements'])}")
    print(f"{'='*60}")
    
    for num, stmt in sorted(mapping['quality_statements'].items()):
        pages = f"pages {stmt['start_page']}-{stmt['end_page']}" if stmt['end_page'] else f"page {stmt['start_page']}"
        subsections = ', '.join(stmt['subsections'].keys()) if stmt['subsections'] else 'none detected'
        print(f"  Statement {num}: {stmt['title'][:50]}...")
        print(f"    Location: {pages}")
        print(f"    Subsections found: {subsections}")
    
    print(f"\n{'='*60}")
    print("Validation Results:")
    print(f"{'='*60}")
    validation = mapping['validation']
    print(f"  Avg pages per statement: {validation['average_pages_per_statement']:.1f}")
    if validation['warnings']:
        print("  Warnings:")
        for warning in validation['warnings']:
            print(f"    - {warning}")
    
    return mapping