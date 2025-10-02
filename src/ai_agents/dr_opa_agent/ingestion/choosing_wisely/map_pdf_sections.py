"""
Script to map Choosing Wisely Canada PDF sections and find specialty page ranges.

This script analyzes a PDF to find where each specialty section starts and ends
by looking for specialty name headers from the provided list.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import PyPDF2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PDFSectionMapper:
    """Maps specialty sections in the Choosing Wisely Canada PDF."""
    
    def __init__(self, pdf_path: str, specialties_file: Optional[str] = None):
        """
        Initialize the mapper.
        
        Args:
            pdf_path: Path to the Choosing Wisely PDF
            specialties_file: Path to text file with specialty list (one per line)
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self.specialties = []
        
        # Load specialties from text file if provided
        if specialties_file:
            self.load_specialties_from_file(specialties_file)
    
    def load_specialties_from_file(self, file_path: str):
        """Load specialty list from text file."""
        try:
            with open(file_path, 'r') as f:
                self.specialties = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self.specialties)} specialties from file")
        except Exception as e:
            logger.error(f"Error loading specialties file: {e}")
    
    def extract_all_text_with_pages(self) -> List[Tuple[int, str]]:
        """
        Extract all text from PDF with page numbers.
        
        Returns:
            List of tuples (page_number, text)
        """
        pages_text = []
        with open(self.pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                # Page numbers are 1-indexed for human readability
                pages_text.append((page_num + 1, text))
                
        logger.info(f"Extracted text from {total_pages} pages")
        return pages_text
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for better matching.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Remove multiple spaces, normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = text.replace('\n', ' ').replace('\r', ' ')
        return text.strip()
    
    def find_section_headers_by_marker(self, pages_text: List[Tuple[int, str]]) -> Dict[str, int]:
        """
        Find section headers using the 'Last updated:' marker which reliably indicates section starts.
        
        Args:
            pages_text: List of (page_number, text) tuples
            
        Returns:
            Dictionary mapping specialty name to starting page
        """
        specialty_starts = {}
        
        for page_num, text in pages_text:
            # Look for 'Last updated:' in first 500 chars (header area)
            if 'Last updated:' in text[:500]:
                # Extract text before 'Last updated'
                try:
                    before_marker = text[:text.index('Last updated:')]
                    lines = before_marker.split('\n')
                    
                    # Find the specialty name (usually first substantial line)
                    specialty = None
                    for line in lines:
                        line = line.strip()
                        # Skip numbers, empty lines, and very short lines
                        if line and not line.isdigit() and len(line) > 3:
                            # Clean up common formatting issues
                            if 'Things Clinicians' not in line:
                                specialty = line
                                break
                    
                    if specialty:
                        # Additional cleanup
                        specialty = specialty.replace('  ', ' ').strip()
                        # Remove leading numbers that might be page numbers
                        specialty = re.sub(r'^\d+\s*', '', specialty)
                        
                        if specialty and len(specialty) > 3:
                            specialty_starts[specialty] = page_num
                            logger.info(f"Found section '{specialty}' on page {page_num}")
                            
                except ValueError:
                    # 'Last updated' not found in expected position
                    pass
        
        return specialty_starts
    
    def find_specialty_headers(self, pages_text: List[Tuple[int, str]]) -> Dict[str, int]:
        """
        Find where each specialty section starts.
        
        Args:
            pages_text: List of (page_number, text) tuples
            
        Returns:
            Dictionary mapping specialty name to starting page
        """
        specialty_starts = {}
        
        for specialty in self.specialties:
            for page_num, text in pages_text:
                if self.find_specialty_on_page(text, specialty):
                    if specialty not in specialty_starts:
                        specialty_starts[specialty] = page_num
                        logger.info(f"Found '{specialty}' on page {page_num}")
                        break
        
        # Log specialties not found
        not_found = set(self.specialties) - set(specialty_starts.keys())
        if not_found:
            logger.warning(f"Specialties not found in PDF: {not_found}")
        
        return specialty_starts
    
    def determine_page_ranges(self, specialty_starts: Dict[str, int], total_pages: int) -> Dict[str, Tuple[int, int]]:
        """
        Determine the page range for each specialty.
        
        Args:
            specialty_starts: Dictionary mapping specialty to starting page
            total_pages: Total number of pages in PDF
            
        Returns:
            Dictionary mapping specialty to (start_page, end_page) tuple
        """
        page_ranges = {}
        
        # Sort specialties by their starting page
        sorted_specialties = sorted(specialty_starts.items(), key=lambda x: x[1])
        
        for i, (specialty, start_page) in enumerate(sorted_specialties):
            # End page is one before the next specialty starts
            # or the last page if this is the last specialty
            if i < len(sorted_specialties) - 1:
                end_page = sorted_specialties[i + 1][1] - 1
            else:
                end_page = total_pages
            
            page_ranges[specialty] = (start_page, end_page)
            logger.info(f"{specialty}: pages {start_page}-{end_page} ({end_page - start_page + 1} pages)")
        
        return page_ranges
    
    def validate_sections(self, page_ranges: Dict[str, Tuple[int, int]], 
                         pages_text: List[Tuple[int, str]]) -> Dict[str, Dict]:
        """
        Validate that sections contain expected content.
        
        Args:
            page_ranges: Dictionary of specialty page ranges
            pages_text: List of all page texts
            
        Returns:
            Dictionary mapping specialty to validation details
        """
        validation_results = {}
        
        # Convert pages_text list to dict for easier lookup
        text_by_page = {page: text for page, text in pages_text}
        
        for specialty, (start_page, end_page) in page_ranges.items():
            # Combine text from all pages in range
            section_text = ""
            for page in range(start_page, min(end_page + 1, len(text_by_page) + 1)):
                if page in text_by_page:
                    section_text += text_by_page[page] + "\n"
            
            # Look for recommendation indicators
            recommendation_keywords = [
                "Don't", "Avoid", "recommend", "unnecessary", 
                "routine", "should not", "is not", "are not"
            ]
            
            found_keywords = [kw for kw in recommendation_keywords if kw.lower() in section_text.lower()]
            
            # Count numbered recommendations (1., 2., etc.)
            numbered_items = re.findall(r'\n\s*(\d+)\s*\.', section_text)
            
            validation_results[specialty] = {
                "has_recommendations": len(found_keywords) > 0,
                "keywords_found": found_keywords,
                "num_numbered_items": len(numbered_items),
                "text_length": len(section_text),
                "likely_valid": len(found_keywords) > 2 and len(numbered_items) > 0
            }
            
            if not validation_results[specialty]["likely_valid"]:
                logger.warning(f"Section '{specialty}' may not contain valid recommendations")
        
        return validation_results
    
    def map_pdf_sections(self, output_path: Optional[str] = None) -> Dict[str, Tuple[int, int]]:
        """
        Main method to map all PDF sections.
        
        Args:
            output_path: Optional path to save the mapping
            
        Returns:
            Dictionary mapping specialty to page ranges
        """
        logger.info(f"Mapping sections in {self.pdf_path}")
        
        # Extract all text with page numbers
        pages_text = self.extract_all_text_with_pages()
        total_pages = len(pages_text)
        
        # Use the more reliable marker-based detection
        specialty_starts = self.find_section_headers_by_marker(pages_text)
        
        # If no sections found with marker, fall back to text matching
        if not specialty_starts:
            logger.warning("No sections found with 'Last updated:' marker, trying text matching...")
            specialty_starts = self.find_specialty_headers(pages_text)
        
        if not specialty_starts:
            logger.error("No specialty sections found in PDF")
            return {}
        
        # Determine page ranges
        page_ranges = self.determine_page_ranges(specialty_starts, total_pages)
        
        # Validate sections
        validation = self.validate_sections(page_ranges, pages_text)
        
        # Create output
        output = {
            "pdf_path": str(self.pdf_path),
            "total_pages": total_pages,
            "total_specialties_found": len(page_ranges),
            "page_ranges": {
                specialty: {
                    "start_page": start,
                    "end_page": end,
                    "num_pages": end - start + 1,
                    "validation": validation.get(specialty, {})
                }
                for specialty, (start, end) in page_ranges.items()
            }
        }
        
        # Save if output path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(output, f, indent=2)
            logger.info(f"Saved mapping to {output_path}")
        
        # Print summary
        logger.info(f"Found {len(page_ranges)} specialty sections in PDF")
        valid_sections = sum(1 for s, v in validation.items() if v.get('likely_valid', False))
        logger.info(f"Valid sections with recommendations: {valid_sections}/{len(page_ranges)}")
        
        return page_ranges


def main():
    """Main function to run the mapping."""
    import sys
    
    # Hardcoded paths for the Choosing Wisely data
    pdf_path = "data/dr_opa_agent/raw/choosing_wisely/Choosing-Wisely-Canada-collection-of-lists-July-6-2022.pdf"
    specialties_file = "data/dr_opa_agent/raw/choosing_wisely/section_list.txt"
    output_path = "data/dr_opa_agent/raw/choosing_wisely/section_mapping.json"
    
    try:
        mapper = PDFSectionMapper(pdf_path, specialties_file)
        page_ranges = mapper.map_pdf_sections(output_path)
        
        print(f"\n{'='*60}")
        print(f"Found {len(page_ranges)} specialty sections:")
        print(f"{'='*60}")
        
        for specialty, (start, end) in sorted(page_ranges.items(), key=lambda x: x[1][0]):
            num_pages = end - start + 1
            print(f"  {specialty:<40} pages {start:3d}-{end:3d} ({num_pages:2d} pages)")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())