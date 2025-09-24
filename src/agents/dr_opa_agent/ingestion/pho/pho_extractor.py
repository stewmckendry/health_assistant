"""PHO document extractor for IPAC and other clinical guidance PDFs."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import PyPDF2
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class PHOExtractor:
    """Extract structured content from PHO PDF documents."""
    
    def __init__(self):
        """Initialize PHO extractor."""
        self.section_pattern = re.compile(
            r'^(\d+\.?\d*\.?\d*)\s+([A-Z][A-Za-z\s,\-]+)',
            re.MULTILINE
        )
        self.heading_pattern = re.compile(
            r'^([A-Z][A-Z\s\-]+)$',
            re.MULTILINE
        )
        
    def extract_document(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract structured content from PHO PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Structured document with sections, metadata, and content
        """
        logger.info(f"Extracting PHO document: {pdf_path}")
        
        try:
            # Read PDF
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                # Extract basic metadata
                metadata = self._extract_pdf_metadata(pdf_reader)
                
                # Extract full text
                full_text = ""
                page_texts = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    page_texts.append(page_text)
                    full_text += page_text + "\n"
                
                # Extract title and document info from first pages
                title = self._extract_title(page_texts[:3])
                doc_info = self._extract_document_info(full_text)
                
                # Extract table of contents if present
                toc = self._extract_table_of_contents(page_texts)
                
                # Extract sections based on structure
                sections = self._extract_sections(full_text, toc)
                
                # Build document structure
                document = {
                    "title": title,
                    "source_file": str(pdf_path),
                    "content": full_text,
                    "sections": sections,
                    "metadata": {
                        **metadata,
                        **doc_info,
                        "source_org": "pho",
                        "document_type": self._infer_document_type(title, pdf_path),
                        "page_count": len(pdf_reader.pages),
                        "extraction_date": datetime.now().isoformat()
                    }
                }
                
                logger.info(f"Successfully extracted {len(sections)} sections from {pdf_path.name}")
                return document
                
        except Exception as e:
            logger.error(f"Error extracting {pdf_path}: {e}")
            raise
    
    def _extract_pdf_metadata(self, pdf_reader: PyPDF2.PdfReader) -> Dict[str, Any]:
        """Extract metadata from PDF properties."""
        metadata = {}
        
        if pdf_reader.metadata:
            if '/Title' in pdf_reader.metadata:
                metadata['pdf_title'] = str(pdf_reader.metadata['/Title'])
            if '/Author' in pdf_reader.metadata:
                metadata['pdf_author'] = str(pdf_reader.metadata['/Author'])
            if '/CreationDate' in pdf_reader.metadata:
                metadata['pdf_creation_date'] = str(pdf_reader.metadata['/CreationDate'])
            if '/ModDate' in pdf_reader.metadata:
                metadata['pdf_modified_date'] = str(pdf_reader.metadata['/ModDate'])
        
        return metadata
    
    def _extract_title(self, first_pages: List[str]) -> str:
        """Extract document title from first pages."""
        # Look for title patterns
        for page_text in first_pages:
            lines = page_text.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                # Skip empty lines and page numbers
                if not line or line.isdigit() or len(line) < 10:
                    continue
                # Look for title-like text
                if 'infection prevention' in line.lower() or 'clinical' in line.lower():
                    return line
        
        return "PHO Clinical Guidance Document"
    
    def _extract_document_info(self, text: str) -> Dict[str, Any]:
        """Extract document metadata from text content."""
        info = {}
        
        # Publication date
        pub_match = re.search(r'Published:\s*(\w+\s+\d{4})', text)
        if pub_match:
            info['published_date'] = pub_match.group(1)
        
        # Revision date
        rev_match = re.search(r'(?:1st\s+)?[Rr]evision:\s*(\w+\s+\d{4})', text)
        if rev_match:
            info['revision_date'] = rev_match.group(1)
            info['effective_date'] = rev_match.group(1)  # Use revision as effective
        
        # Document version
        ver_match = re.search(r'Version\s*(\d+\.?\d*)', text)
        if ver_match:
            info['version'] = ver_match.group(1)
        
        # Extract key topics from content
        topics = []
        if 'infection prevention' in text.lower():
            topics.append('infection-prevention')
        if 'ipac' in text.lower():
            topics.append('ipac')
        if 'clinical office' in text.lower():
            topics.append('clinical-office')
        if 'sterilization' in text.lower():
            topics.append('sterilization')
        if 'ppe' in text.lower() or 'personal protective' in text.lower():
            topics.append('ppe')
        if 'hand hygiene' in text.lower():
            topics.append('hand-hygiene')
        
        info['topics'] = topics
        
        return info
    
    def _extract_table_of_contents(self, page_texts: List[str]) -> List[Dict[str, Any]]:
        """Extract table of contents structure."""
        toc = []
        
        # Find TOC page
        toc_page_idx = -1
        for idx, page_text in enumerate(page_texts[:15]):  # Check first 15 pages
            if 'TABLE OF CONTENTS' in page_text.upper() or 'Table of Contents' in page_text:
                toc_page_idx = idx
                break
        
        if toc_page_idx == -1:
            return toc
        
        # Extract TOC entries
        toc_text = page_texts[toc_page_idx]
        lines = toc_text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Match numbered sections with page numbers
            toc_match = re.match(r'^(\d+\.?\d*)\s+(.+?)\.{2,}\s*(\d+)$', line)
            if toc_match:
                toc.append({
                    'number': toc_match.group(1),
                    'title': toc_match.group(2).strip(),
                    'page': int(toc_match.group(3))
                })
            else:
                # Try lettered subsections
                letter_match = re.match(r'^([A-Z])\.\s+(.+?)\.{2,}\s*(\d+)$', line)
                if letter_match:
                    toc.append({
                        'number': letter_match.group(1),
                        'title': letter_match.group(2).strip(),
                        'page': int(letter_match.group(3))
                    })
        
        return toc
    
    def _extract_sections(self, text: str, toc: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract document sections based on structure."""
        sections = []
        
        # Split text into major sections based on patterns
        # Pattern for numbered sections (e.g., "1. SECTION TITLE")
        section_splits = re.split(r'\n(\d+\.)\s+([A-Z][A-Z\s\-]+)\n', text)
        
        current_section = None
        current_content = ""
        
        for i in range(1, len(section_splits), 3):
            if i + 2 < len(section_splits):
                section_num = section_splits[i]
                section_title = section_splits[i + 1].strip()
                section_content = section_splits[i + 2] if i + 2 < len(section_splits) else ""
                
                # Process previous section if exists
                if current_section:
                    subsections = self._extract_subsections(current_content)
                    current_section['subsections'] = subsections
                    sections.append(current_section)
                
                # Create new section
                current_section = {
                    'heading': f"{section_num} {section_title}",
                    'content': self._clean_content(section_content[:2000]),  # First part
                    'full_content': section_content,
                    'subsections': []
                }
                current_content = section_content
        
        # Don't forget the last section
        if current_section:
            subsections = self._extract_subsections(current_content)
            current_section['subsections'] = subsections
            sections.append(current_section)
        
        # If no sections found with numbered pattern, try other patterns
        if not sections:
            sections = self._extract_sections_fallback(text)
        
        return sections
    
    def _extract_subsections(self, content: str) -> List[Dict[str, str]]:
        """Extract subsections from section content."""
        subsections = []
        
        # Pattern for lettered subsections (e.g., "A. Subsection Title")
        subsection_pattern = re.compile(r'^([A-Z])\.\s+(.+?)$', re.MULTILINE)
        matches = list(subsection_pattern.finditer(content))
        
        for i, match in enumerate(matches):
            letter = match.group(1)
            title = match.group(2)
            
            # Extract content until next subsection or end
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            subsection_content = content[start:end].strip()
            
            subsections.append({
                'heading': f"{letter}. {title}",
                'content': self._clean_content(subsection_content[:1500])
            })
        
        return subsections
    
    def _extract_sections_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback method to extract sections using heading patterns."""
        sections = []
        
        # Split by major headings
        parts = re.split(r'\n([A-Z][A-Z\s\-]+)\n', text)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                heading = parts[i].strip()
                content = parts[i + 1]
                
                # Skip if too short or looks like noise
                if len(heading) < 5 or len(content) < 100:
                    continue
                
                sections.append({
                    'heading': heading,
                    'content': self._clean_content(content[:2000]),
                    'full_content': content,
                    'subsections': []
                })
        
        # If still no sections, create chunks
        if not sections:
            # Create artificial sections from content chunks
            chunk_size = 5000
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                sections.append({
                    'heading': f"Section {i // chunk_size + 1}",
                    'content': self._clean_content(chunk[:2000]),
                    'full_content': chunk,
                    'subsections': []
                })
        
        return sections
    
    def _clean_content(self, text: str) -> str:
        """Clean extracted text content."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        # Remove headers/footers if present
        text = re.sub(r'Infection Prevention and Control.*?\|\s*\w+\s+\d{4}', '', text)
        text = re.sub(r'Public Health Ontario', '', text)
        
        return text.strip()
    
    def _infer_document_type(self, title: str, file_path: Path) -> str:
        """Infer document type from title and filename."""
        title_lower = title.lower()
        filename_lower = file_path.name.lower()
        
        if 'ipac' in filename_lower or 'infection' in title_lower:
            return 'ipac-guidance'
        elif 'checklist' in title_lower:
            return 'checklist'
        elif 'fact sheet' in title_lower:
            return 'fact-sheet'
        elif 'best practice' in title_lower or 'bp-' in filename_lower:
            return 'best-practice'
        elif 'guideline' in title_lower:
            return 'guideline'
        else:
            return 'guidance'


def extract_pho_document(pdf_path: str) -> Dict[str, Any]:
    """Convenience function to extract a PHO document.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted document structure
    """
    extractor = PHOExtractor()
    return extractor.extract_document(Path(pdf_path))