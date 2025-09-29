"""CEP clinical tools extractor.

Extracts structured data from CEP tool HTML pages, focusing on 
navigation structure and key clinical content for indexing.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup, NavigableString
import hashlib

logger = logging.getLogger(__name__)


class CEPExtractor:
    """Extract structured data from CEP clinical tool pages."""
    
    def __init__(self):
        """Initialize CEP extractor."""
        self.processed_dir = Path("data/dr_opa_agent/processed/cep")
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_from_html(self, html: str, url: str, tool_info: Dict[str, str]) -> Dict[str, Any]:
        """Extract structured data from CEP tool HTML.
        
        Args:
            html: Raw HTML content
            url: Tool URL
            tool_info: Tool metadata (name, category, slug)
            
        Returns:
            Extracted tool data optimized for navigation and search
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Base extraction
        document = {
            'document_id': f"cep_{tool_info['slug'].replace('-', '_')}",
            'source_url': url,
            'source_org': 'cep',
            'document_type': 'clinical_tool',
            'tool_category': tool_info.get('category', 'general'),
            'extracted_at': datetime.now().isoformat(),
            'content_hash': hashlib.sha256(html.encode()).hexdigest()
        }
        
        # Extract metadata
        document.update(self._extract_metadata(soup, tool_info))
        
        # Extract navigation structure (section headings and anchors)
        document['navigation'] = self._extract_navigation(soup)
        
        # Extract key clinical content for indexing
        document['key_content'] = self._extract_key_content(soup)
        
        # Extract tool features
        document['features'] = self._detect_features(soup)
        
        # Extract sections with summaries
        document['sections'] = self._extract_sections(soup)
        
        # Extract references and resources
        document['references'] = self._extract_references(soup)
        
        # Generate executive summary for quick reference
        document['summary'] = self._generate_summary(document)
        
        return document
    
    def _extract_metadata(self, soup: BeautifulSoup, tool_info: Dict[str, str]) -> Dict[str, Any]:
        """Extract tool metadata."""
        metadata = {
            'title': tool_info.get('name', 'Unknown Tool'),
            'tool_slug': tool_info.get('slug', '')
        }
        
        # Try to find last updated date
        # Look for patterns like "Last Updated: July 31, 2025"
        date_patterns = [
            r'Last [Uu]pdated?:?\s*([^<\n]+)',
            r'Updated:?\s*([^<\n]+)',
            r'Revised:?\s*([^<\n]+)',
            r'Version date:?\s*([^<\n]+)'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, str(soup), re.IGNORECASE)
            if match:
                metadata['last_updated'] = match.group(1).strip()
                break
        
        # Extract any meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            
            if 'description' in name and content:
                metadata['meta_description'] = content
            elif 'keywords' in name and content:
                metadata['keywords'] = content.split(',')
        
        # Look for funding/development info
        footer = soup.find('footer') or soup.find(class_='footer')
        if footer:
            footer_text = footer.get_text()
            if 'Centre for Effective Practice' in footer_text:
                metadata['developer'] = 'Centre for Effective Practice'
            if 'Ministry of Health' in footer_text:
                metadata['funder'] = 'Ontario Ministry of Health'
        
        return metadata
    
    def _extract_navigation(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract navigation structure for deep linking."""
        navigation = []
        
        # Look for navigation menu or table of contents
        nav_selectors = [
            'nav',
            '.navigation',
            '.toc',
            '.table-of-contents',
            '[role="navigation"]'
        ]
        
        nav_element = None
        for selector in nav_selectors:
            nav_element = soup.select_one(selector)
            if nav_element:
                break
        
        if nav_element:
            # Extract links from navigation
            for link in nav_element.find_all('a'):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if href and text:
                    navigation.append({
                        'title': text,
                        'anchor': href,
                        'type': 'nav_link'
                    })
        
        # Also look for section headings with IDs (for anchoring)
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            heading_id = heading.get('id')
            heading_text = heading.get_text(strip=True)
            if heading_id and heading_text:
                navigation.append({
                    'title': heading_text,
                    'anchor': f"#{heading_id}",
                    'type': f"heading_{heading.name}",
                    'level': int(heading.name[1])
                })
        
        return navigation
    
    def _extract_key_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract key clinical content for indexing."""
        key_content = {}
        
        # Look for assessment tools
        assessment_tools = []
        tool_patterns = ['MoCA', 'MMSE', 'PHQ-9', 'GAD-7', 'Clock Drawing', 'Mini-Cog']
        content_text = soup.get_text()
        
        for tool in tool_patterns:
            if tool in content_text:
                assessment_tools.append(tool)
        
        if assessment_tools:
            key_content['assessment_tools'] = assessment_tools
        
        # Look for red flags or warning signs
        red_flags = []
        red_flag_sections = soup.find_all(text=re.compile(r'red flag|warning sign|urgent|emergency', re.I))
        for section in red_flag_sections[:3]:  # Limit to avoid noise
            parent = section.parent
            if parent:
                # Get the containing list or paragraph
                container = parent.find_parent(['ul', 'ol', 'p'])
                if container:
                    text = container.get_text(strip=True)[:200]
                    if text not in red_flags:
                        red_flags.append(text)
        
        if red_flags:
            key_content['red_flags'] = red_flags
        
        # Look for diagnostic criteria
        diagnostic_sections = soup.find_all(text=re.compile(r'diagnos|criteria|DSM|ICD', re.I))
        if diagnostic_sections:
            key_content['has_diagnostic_criteria'] = True
        
        # Look for treatment recommendations
        treatment_sections = soup.find_all(text=re.compile(r'treatment|management|therapy|intervention', re.I))
        if treatment_sections:
            key_content['has_treatment_guidance'] = True
        
        # Look for referral criteria
        referral_sections = soup.find_all(text=re.compile(r'refer|specialist|consultation', re.I))
        if referral_sections:
            key_content['has_referral_criteria'] = True
        
        return key_content
    
    def _detect_features(self, soup: BeautifulSoup) -> Dict[str, bool]:
        """Detect tool features like calculators, algorithms, etc."""
        features = {
            'has_algorithm': False,
            'has_calculator': False,
            'has_checklist': False,
            'has_flowchart': False,
            'has_tables': False,
            'has_forms': False,
            'has_patient_resources': False,
            'has_videos': False
        }
        
        content_text = soup.get_text().lower()
        
        # Check for algorithms/flowcharts
        if any(word in content_text for word in ['algorithm', 'flowchart', 'decision tree']):
            features['has_algorithm'] = True
        
        # Check for calculators
        if any(word in content_text for word in ['calculator', 'calculate', 'score', 'scoring']):
            features['has_calculator'] = True
        
        # Check for checklists
        if 'checklist' in content_text or soup.find_all('input', type='checkbox'):
            features['has_checklist'] = True
        
        # Check for tables
        if soup.find_all('table'):
            features['has_tables'] = True
        
        # Check for forms
        if soup.find_all('form') or soup.find_all('input'):
            features['has_forms'] = True
        
        # Check for patient resources
        if any(phrase in content_text for phrase in ['patient handout', 'patient resource', 'patient education']):
            features['has_patient_resources'] = True
        
        # Check for videos
        if soup.find_all('video') or 'youtube' in str(soup) or 'vimeo' in str(soup):
            features['has_videos'] = True
        
        return features
    
    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract section summaries for navigation."""
        sections = []
        
        # Find main content area
        main_content = soup.find('main') or soup.find(class_='content') or soup.body
        if not main_content:
            return sections
        
        current_section = None
        
        for element in main_content.descendants:
            if not hasattr(element, 'name'):
                continue
            
            # Track H2 sections (main sections)
            if element.name == 'h2':
                # Save previous section if exists
                if current_section and current_section.get('content'):
                    current_section['summary'] = self._summarize_content(current_section['content'])
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    'heading': element.get_text(strip=True),
                    'anchor': f"#{element.get('id', '')}" if element.get('id') else None,
                    'level': 2,
                    'content': [],
                    'subsections': []
                }
            
            # Track H3 subsections
            elif element.name == 'h3' and current_section:
                subsection = {
                    'heading': element.get_text(strip=True),
                    'anchor': f"#{element.get('id', '')}" if element.get('id') else None,
                    'level': 3
                }
                current_section['subsections'].append(subsection)
            
            # Collect content for current section
            elif element.name in ['p', 'ul', 'ol', 'table'] and current_section:
                text = element.get_text(strip=True)
                if text and len(text) > 20:  # Filter out very short snippets
                    current_section['content'].append(text[:500])  # Limit length
        
        # Don't forget the last section
        if current_section and current_section.get('content'):
            current_section['summary'] = self._summarize_content(current_section['content'])
            sections.append(current_section)
        
        # Clean up sections - only keep essential fields
        for section in sections:
            section.pop('content', None)  # Remove raw content, keep only summary
        
        return sections[:15]  # Limit number of sections to avoid bloat
    
    def _extract_references(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract references and external resources."""
        references = []
        
        # Look for reference section
        ref_sections = soup.find_all(['div', 'section'], class_=re.compile(r'reference|citation|source', re.I))
        
        for ref_section in ref_sections:
            # Extract reference links
            for link in ref_section.find_all('a'):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if href and text and ('http' in href or 'doi' in href):
                    references.append({
                        'title': text[:200],
                        'url': href,
                        'type': 'academic' if 'doi' in href or 'pubmed' in href else 'web'
                    })
        
        # Also look for numbered references like [1], [2], etc.
        numbered_refs = soup.find_all(text=re.compile(r'\[\d+\]'))
        if numbered_refs:
            # Find the references list (usually at bottom)
            for element in soup.find_all(['ol', 'ul']):
                if 'reference' in str(element.get('class', [])).lower():
                    for li in element.find_all('li'):
                        ref_text = li.get_text(strip=True)
                        if ref_text:
                            references.append({
                                'title': ref_text[:200],
                                'url': None,
                                'type': 'citation'
                            })
        
        return references[:20]  # Limit to top 20 references
    
    def _summarize_content(self, content_list: List[str]) -> str:
        """Generate a brief summary from content list."""
        if not content_list:
            return ""
        
        # Take first 2-3 content pieces
        summary_parts = content_list[:3]
        summary = ' '.join(summary_parts)
        
        # Truncate to reasonable length
        if len(summary) > 500:
            summary = summary[:497] + "..."
        
        return summary
    
    def _generate_summary(self, document: Dict[str, Any]) -> str:
        """Generate executive summary of the tool."""
        parts = []
        
        # Title
        parts.append(f"{document.get('title', 'Clinical Tool')}")
        
        # Category
        category = document.get('tool_category', '').replace('_', ' ').title()
        if category:
            parts.append(f"Category: {category}")
        
        # Key features
        features = document.get('features', {})
        feature_list = [k.replace('has_', '').replace('_', ' ') for k, v in features.items() if v]
        if feature_list:
            parts.append(f"Features: {', '.join(feature_list[:3])}")
        
        # Assessment tools
        key_content = document.get('key_content', {})
        if key_content.get('assessment_tools'):
            tools = key_content['assessment_tools'][:3]
            parts.append(f"Tools: {', '.join(tools)}")
        
        # Section count
        sections = document.get('sections', [])
        if sections:
            parts.append(f"{len(sections)} main sections")
        
        return ". ".join(parts)
    
    def save_extracted_data(self, document: Dict[str, Any], output_file: Optional[str] = None):
        """Save extracted data to JSON file.
        
        Args:
            document: Extracted document data
            output_file: Output file path (optional)
        """
        if not output_file:
            slug = document.get('tool_slug', 'unknown')
            output_file = self.processed_dir / f"{slug}_extracted.json"
        else:
            output_file = Path(output_file)
        
        with open(output_file, 'w') as f:
            json.dump(document, f, indent=2)
        
        logger.info(f"Saved extracted data to {output_file}")
        
        return output_file


def extract_cep_tool(html_file: str, tool_info: Dict[str, str]) -> Dict[str, Any]:
    """Convenience function to extract a CEP tool.
    
    Args:
        html_file: Path to HTML file
        tool_info: Tool metadata
        
    Returns:
        Extracted tool data
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    url = f"https://tools.cep.health/tool/{tool_info['slug']}/"
    
    extractor = CEPExtractor()
    document = extractor.extract_from_html(html, url, tool_info)
    
    return document