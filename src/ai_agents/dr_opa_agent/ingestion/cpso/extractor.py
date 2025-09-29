"""CPSO document extractor with regex and optional LLM enhancement."""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString
import requests
import hashlib

logger = logging.getLogger(__name__)


class CPSOExtractor:
    """Extract structured data from CPSO HTML documents."""
    
    def __init__(self, use_llm: bool = False, openai_api_key: Optional[str] = None):
        """Initialize CPSO extractor.
        
        Args:
            use_llm: Whether to use LLM for enhanced extraction
            openai_api_key: OpenAI API key for LLM extraction
        """
        self.use_llm = use_llm
        self.openai_api_key = openai_api_key
        
        if self.use_llm and not self.openai_api_key:
            logger.warning("LLM extraction requested but no API key provided")
            self.use_llm = False
    
    def extract_from_html(self, html: str, url: str) -> Dict[str, Any]:
        """Extract structured data from CPSO HTML.
        
        Args:
            html: Raw HTML content
            url: Source URL
            
        Returns:
            Extracted document data
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Determine document type from URL
        doc_type = self._detect_document_type(url)
        
        # Base extraction
        document = {
            'source_url': url,
            'source_org': 'cpso',
            'document_type': doc_type,
            'extracted_at': datetime.now().isoformat(),
            'content_hash': hashlib.sha256(html.encode()).hexdigest()
        }
        
        # Extract metadata
        document.update(self._extract_metadata(soup, doc_type))
        
        # Extract content
        document['content'] = self._extract_content(soup, doc_type)
        
        # Extract sections
        document['sections'] = self._extract_sections(soup, doc_type)
        
        # Detect policy level
        if doc_type == 'policy':
            document['policy_level'] = self._detect_policy_level(document['content'])
        
        # LLM enhancement if enabled
        if self.use_llm:
            document = self._enhance_with_llm(document)
        
        return document
    
    def _detect_document_type(self, url: str) -> str:
        """Detect document type from URL."""
        url_lower = url.lower()
        
        if '/advice-to-the-profession' in url_lower:
            return 'advice'
        elif '/statements-positions' in url_lower:
            return 'statement'
        elif '/policies/' in url_lower:
            return 'policy'
        else:
            return 'guidance'
    
    def _extract_metadata(self, soup: BeautifulSoup, doc_type: str) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = {}
        
        # Title
        title = soup.select_one('h1')
        if title:
            metadata['title'] = title.get_text(strip=True)
        
        # Look for metadata in specific patterns
        # Policy metadata often in a sidebar or header area
        
        # Try to find approval date
        approval_patterns = [
            r'Approved by Council:\s*([^<\n]+)',
            r'Approved:\s*([^<\n]+)',
            r'Effective Date:\s*([^<\n]+)'
        ]
        
        for pattern in approval_patterns:
            match = re.search(pattern, str(soup), re.IGNORECASE)
            if match:
                metadata['approval_date'] = self._normalize_date(match.group(1))
                break
        
        # Look for review date
        review_patterns = [
            r'Reviewed and Updated:\s*([^<\n]+)',
            r'Last Reviewed:\s*([^<\n]+)',
            r'Reviewed:\s*([^<\n]+)'
        ]
        
        for pattern in review_patterns:
            match = re.search(pattern, str(soup), re.IGNORECASE)
            if match:
                metadata['review_date'] = self._normalize_date(match.group(1))
                break
        
        # Look for policy number
        policy_num_patterns = [
            r'Policy\s+#?:\s*(\d+[-/]\d+)',
            r'Policy\s+Number:\s*(\d+[-/]\d+)'
        ]
        
        for pattern in policy_num_patterns:
            match = re.search(pattern, str(soup), re.IGNORECASE)
            if match:
                metadata['policy_number'] = match.group(1)
                break
        
        # Extract any dates found in meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            
            if 'date' in name and content:
                if 'publish' in name:
                    metadata['published_date'] = self._normalize_date(content)
                elif 'modified' in name or 'update' in name:
                    metadata['updated_date'] = self._normalize_date(content)
        
        return metadata
    
    def _extract_content(self, soup: BeautifulSoup, doc_type: str) -> str:
        """Extract main content as clean text."""
        # Find main content area
        content_selectors = [
            'main',
            '#content',
            '.content',
            '.policy-content',
            'article'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            # Fallback to body
            main_content = soup.body or soup
        
        # Work with the content directly (BeautifulSoup elements are already isolated)
        content = main_content
        
        # Remove navigation, sidebars, etc.
        for elem in content.select('nav, .navigation, .sidebar, .breadcrumb, header, footer, script, style, .skip-link'):
            elem.decompose()
        
        # Remove specific CPSO navigation elements
        for comment in content.find_all(string=lambda text: isinstance(text, str) and ('BREADCRUMBS' in text or 'PAGE TITLE AND SUMMARY SECTION' in text)):
            comment.extract()
        
        # Convert to markdown-like text
        text = self._html_to_markdown(content)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _html_to_markdown(self, element) -> str:
        """Convert HTML element to markdown-like text."""
        if isinstance(element, NavigableString):
            return str(element)
        
        if element.name in ['script', 'style']:
            return ''
        
        # Process children first
        children_text = []
        for child in element.children:
            child_text = self._html_to_markdown(child)
            if child_text:
                children_text.append(child_text)
        
        content = ''.join(children_text)
        
        # Format based on element type
        if element.name == 'h1':
            return f"\n# {content}\n\n"
        elif element.name == 'h2':
            return f"\n## {content}\n\n"
        elif element.name == 'h3':
            return f"\n### {content}\n\n"
        elif element.name == 'h4':
            return f"\n#### {content}\n\n"
        elif element.name == 'p':
            return f"{content}\n\n"
        elif element.name == 'strong' or element.name == 'b':
            return f"**{content}**"
        elif element.name == 'em' or element.name == 'i':
            return f"*{content}*"
        elif element.name == 'ul':
            items = []
            for li in element.find_all('li', recursive=False):
                li_text = self._html_to_markdown(li)
                items.append(f"- {li_text.strip()}")
            return '\n'.join(items) + '\n\n'
        elif element.name == 'ol':
            items = []
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                li_text = self._html_to_markdown(li)
                items.append(f"{i}. {li_text.strip()}")
            return '\n'.join(items) + '\n\n'
        elif element.name == 'li':
            return content
        elif element.name == 'a':
            href = element.get('href', '')
            if href and href != content:
                return f"[{content}]({href})"
            return content
        elif element.name == 'br':
            return '\n'
        elif element.name == 'hr':
            return '\n---\n\n'
        elif element.name == 'blockquote':
            lines = content.strip().split('\n')
            quoted = '\n'.join(f"> {line}" for line in lines)
            return f"{quoted}\n\n"
        elif element.name in ['div', 'section', 'article', 'main']:
            return content
        elif element.name == 'sup':
            return f"^{content}"
        else:
            return content
    
    def _extract_sections(self, soup: BeautifulSoup, doc_type: str) -> List[Dict[str, Any]]:
        """Extract document sections with hierarchy."""
        sections = []
        
        # Find main content
        main_content = None
        for selector in ['main', '#content', '.content', 'article']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            return sections
        
        # Track current section hierarchy
        current_h2 = None
        current_h3 = None
        
        # Process all elements to maintain context
        for elem in main_content.descendants:
            if not hasattr(elem, 'name'):
                continue
            
            if elem.name == 'h2':
                # New major section
                current_h2 = {
                    'level': 2,
                    'heading': elem.get_text(strip=True),
                    'content': [],
                    'subsections': []
                }
                current_h3 = None
                sections.append(current_h2)
                
            elif elem.name == 'h3' and current_h2:
                # Subsection
                current_h3 = {
                    'level': 3,
                    'heading': elem.get_text(strip=True),
                    'content': []
                }
                current_h2['subsections'].append(current_h3)
                
            elif elem.name in ['p', 'ul', 'ol'] and (current_h3 or current_h2):
                # Add content to current section
                text = self._html_to_markdown(elem).strip()
                if text:
                    if current_h3:
                        current_h3['content'].append(text)
                    elif current_h2:
                        current_h2['content'].append(text)
        
        # Clean up sections - join content
        for section in sections:
            section['content'] = '\n\n'.join(section['content'])
            for subsection in section.get('subsections', []):
                subsection['content'] = '\n\n'.join(subsection['content'])
        
        return sections
    
    def _detect_policy_level(self, content: str) -> str:
        """Detect CPSO policy level from content."""
        content_lower = content.lower()
        
        # Count regulatory language
        must_count = len(re.findall(r'\bmust\b', content_lower))
        shall_count = len(re.findall(r'\bshall\b', content_lower))
        should_count = len(re.findall(r'\bshould\b', content_lower))
        advised_count = len(re.findall(r'\badvised?\b', content_lower))
        
        # Determine level based on language
        if must_count > 0 or shall_count > 0:
            return 'expectation'
        elif should_count > 0 or advised_count > 0:
            return 'advice'
        else:
            return 'general'
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to ISO format."""
        # Clean the string
        date_str = date_str.strip()
        date_str = re.sub(r'<[^>]+>', '', date_str)  # Remove HTML tags
        date_str = date_str.strip()
        
        # Try various date patterns
        patterns = [
            (r'(\w+)\s+(\d{4})', '%B %Y'),  # "January 2024"
            (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', '%B %d %Y'),  # "January 15, 2024"
            (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),  # "2024-01-15"
        ]
        
        # For now, return as-is if we can't parse
        # In production, use dateutil.parser
        return date_str
    
    def _enhance_with_llm(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance extraction with LLM analysis."""
        # This would use OpenAI to:
        # 1. Extract dates more accurately
        # 2. Identify key requirements
        # 3. Summarize sections
        # 4. Extract specific policy expectations
        
        # Placeholder for LLM enhancement
        logger.info("LLM enhancement not yet implemented")
        return document


def extract_cpso_document(url: str, use_llm: bool = False) -> Dict[str, Any]:
    """Convenience function to extract a CPSO document.
    
    Args:
        url: CPSO document URL
        use_llm: Whether to use LLM enhancement
        
    Returns:
        Extracted document data
    """
    # Fetch HTML
    headers = {
        'User-Agent': 'Dr-OPA-Agent/1.0 (Ontario Practice Advice)'
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Extract
    extractor = CPSOExtractor(use_llm=use_llm)
    document = extractor.extract_from_html(response.text, url)
    
    return document