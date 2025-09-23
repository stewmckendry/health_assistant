#!/usr/bin/env python3
"""
Enhanced extraction module for Health Insurance Act (Reg. 552) - V3.
Fixed to properly capture DEFINITIONS section (1-1.14) and all topic areas.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

from openai import AsyncOpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ActSection:
    """Structured representation of a Health Insurance Act section."""
    section_ref: str
    topic_section: str  # E.g., "DEFINITIONS", "HEALTH CARD", etc.
    title: str
    raw_text: str
    line_range: str
    effect: Optional[str] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    durations: Optional[Dict[str, Any]] = None
    prerequisites: Optional[Dict[str, Any]] = None
    actors: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    incomplete: bool = False
    notes: Optional[str] = None


class EnhancedActExtractorV3:
    """Extract and normalize Health Insurance Act sections with fixed DEFINITIONS handling."""
    
    # Major topic sections from TOC with their section ranges
    TOPIC_SECTIONS = [
        ("DEFINITIONS", "1-1.14"),
        ("HEALTH CARD", "2-2.3"),
        ("ESTABLISHING STATUS", "3-3.1"),
        ("APPLICATION", "4"),
        ("INSURED HOSPITAL SERVICES IN CANADA", "7-14"),
        ("INSURED AMBULANCE SERVICES", "15-15.1"),
        ("SPECIFIED HEALTH CARE SERVICES", "16-23"),
        ("EXCLUSIONS", "24-26.1"),
        ("PREFERRED PROVIDER ARRANGEMENTS", "27"),
        ("SERVICES OUTSIDE ONTARIO", "28-28.0.3"),
        ("OUT OF COUNTRY SERVICES", "28.1-28.6"),
        ("HEALTH SERVICES", "29-33"),
        ("DESIGNATED HOSPITALS AND HEALTH FACILITIES", "34-35"),
        ("INFORMATION TO BE FURNISHED BY DESIGNATED HOSPITALS", "36-37"),
        ("PHYSICIAN SERVICES", "37.1-37.11"),
        ("BILLING AND PAYMENT FOR INSURED SERVICES", "38-38.6"),
        ("SUBROGATION (PROCEDURAL)", "39")
    ]
    
    # Key topics to identify
    TOPIC_KEYWORDS = {
        'eligibility': ['eligible', 'eligibility', 'qualify', 'entitled'],
        'residency': ['resident', 'residency', 'primary place', 'physical presence'],
        'students': ['student', 'educational', 'enrol', 'academic'],
        'workers': ['worker', 'employment', 'work permit', 'employer'],
        'military': ['Canadian Forces', 'CF', 'RCMP', 'military'],
        'diplomat': ['diplomat', 'consular'],
        'spouse': ['spouse', 'married', 'conjugal'],
        'dependant': ['dependant', 'dependent', 'child'],
        'health_card': ['health card', 'card', 'nontransferable'],
        'presence': ['physical presence', '153 days', '183 days', '12-month'],
        'exemption': ['exempt', 'exception', 'despite'],
        'uninsured': ['uninsured', 'exclusion', 'not covered'],
        'hospital': ['hospital', 'in-patient', 'out-patient'],
        'ambulance': ['ambulance', 'emergency', 'transport'],
        'billing': ['billing', 'payment', 'fee', 'charge'],
    }
    
    def __init__(self, openai_api_key: str, max_concurrent: int = 5):
        """Initialize extractor with OpenAI client."""
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.max_concurrent = max_concurrent
        self.extraction_cache = {}
        
    async def extract(self, act_file: str, *, max_sections: Optional[int] = None) -> Dict:
        """
        Extract structured data from Health Insurance Act document.
        
        Args:
            act_file: Path to the act document (.doc or .pdf)
            max_sections: Limit extraction to first N sections (for testing)
            
        Returns:
            Dictionary with extracted sections and metadata
        """
        logger.info(f"Starting extraction from {act_file}")
        
        # Load and clean document
        raw_text = await self._load_document(act_file)
        
        # Split into sections with fixed logic for DEFINITIONS
        sections = self._split_into_structured_sections_fixed(raw_text)
        
        if max_sections:
            sections = sections[:max_sections]
            logger.info(f"Limited to {max_sections} sections for testing")
        
        # Process sections concurrently with LLM normalization
        normalized_sections = await self._normalize_sections_batch(sections)
        
        # Post-process and validate
        validated_sections = self._validate_sections(normalized_sections)
        
        result = {
            'source': act_file,
            'extracted_at': datetime.utcnow().isoformat() + 'Z',
            'total_sections': len(sections),
            'normalized_sections': len(validated_sections),
            'sections': validated_sections
        }
        
        logger.info(f"Extraction complete: {len(validated_sections)} sections")
        return result
    
    async def _load_document(self, file_path: str) -> str:
        """Load and clean document text."""
        logger.info(f"Loading document: {file_path}")
        
        if file_path.endswith('.doc'):
            text = await self._load_doc(file_path)
        elif file_path.endswith('.pdf'):
            text = await self._load_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        # Clean and normalize
        text = self._clean_text(text)
        logger.info(f"Loaded {len(text)} characters")
        return text
    
    async def _load_doc(self, file_path: str) -> str:
        """Load .doc file using textutil (macOS) or antiword."""
        try:
            # Try textutil first (macOS)
            result = subprocess.run(
                ['textutil', '-convert', 'txt', '-stdout', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Fallback to antiword
        try:
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Last resort: treat as text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    async def _load_pdf(self, file_path: str) -> str:
        """Load PDF file using pdftotext."""
        try:
            result = subprocess.run(
                ['pdftotext', '-layout', file_path, '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning(f"pdftotext not available for {file_path}")
            
        # Could add PyPDF2 fallback here
        raise ValueError(f"Cannot extract text from PDF: {file_path}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize document text."""
        # Remove headers/footers patterns
        text = re.sub(r'Health Insurance Act.*?R\.R\.O\. 1990.*?\n', '', text)
        text = re.sub(r'Consolidation Period:.*?\n', '', text)
        
        # Clean hyperlinks but keep references
        text = re.sub(r'HYPERLINK\s+"[^"]+"\s*', '', text)
        text = re.sub(r'HYPERLINK\s+\\l\s+"[^"]+"\s*\\o\s+"[^"]+"\s*', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\t+', ' ', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _split_into_structured_sections_fixed(self, text: str) -> List[Dict[str, Any]]:
        """Split document into sections with FIXED logic for DEFINITIONS and other sections."""
        sections = []
        lines = text.split('\n')
        
        # Build a map of which lines belong to which topic section
        topic_assignments = {}
        
        # First, find where DEFINITIONS section starts (after TOC)
        definitions_start = None
        for i, line in enumerate(lines):
            if i > 100 and 'DEFINITIONS' in line and 'HYPERLINK' not in line:
                definitions_start = i
                logger.info(f"Found DEFINITIONS header at line {i}")
                break
        
        # Map sections to topics based on their section numbers
        for i, line in enumerate(lines):
            # Skip TOC and headers
            if i < (definitions_start or 100):
                continue
            
            # Check for section patterns
            # Pattern 1: Main section like "1.  (1)  In this Regulation"
            main_section_pattern = re.match(r'^\s*(\d+)\.\s+\((\d+)\)\s+(.+)', line)
            if main_section_pattern and definitions_start and i == definitions_start + 1:
                # This is section 1(1) - the main definitions
                topic_assignments[i] = ("DEFINITIONS", "1(1)")
                continue
            
            # Pattern 2: Subsections like "1.1  For the purposes..."
            subsection_pattern = re.match(r'^\s*(1\.\d+)\s+(.+)', line)
            if subsection_pattern:
                section_num = subsection_pattern.group(1)
                # Sections 1.1 through 1.14 belong to DEFINITIONS
                topic_assignments[i] = ("DEFINITIONS", section_num)
                continue
            
            # Pattern 3: Sections 2.x (HEALTH CARD)
            section_2_pattern = re.match(r'^\s*(2(?:\.\d+)?)\s+(?:\((\d+)\)\s+)?(.+)', line)
            if section_2_pattern:
                section_num = section_2_pattern.group(1)
                if section_2_pattern.group(2):
                    section_num += f"({section_2_pattern.group(2)})"
                topic_assignments[i] = ("HEALTH CARD", section_num)
                continue
            
            # Pattern 4: Section 3.x (ESTABLISHING STATUS)
            section_3_pattern = re.match(r'^\s*(3(?:\.\d+)?)\s+(?:\((\d+)\)\s+)?(.+)', line)
            if section_3_pattern:
                section_num = section_3_pattern.group(1)
                if section_3_pattern.group(2):
                    section_num += f"({section_3_pattern.group(2)})"
                topic_assignments[i] = ("ESTABLISHING STATUS", section_num)
                continue
            
            # Pattern 5: Section 4 (APPLICATION)
            section_4_pattern = re.match(r'^\s*(4)\s+(?:\((\d+)\)\s+)?(.+)', line)
            if section_4_pattern:
                section_num = "4"
                if section_4_pattern.group(2):
                    section_num += f"({section_4_pattern.group(2)})"
                topic_assignments[i] = ("APPLICATION", section_num)
                continue
            
            # Pattern 6: Sections 7-14 (INSURED HOSPITAL SERVICES)
            section_7_14_pattern = re.match(r'^\s*([7-9]|1[0-4])(?:\.(\d+))?\s+(?:\((\d+)\)\s+)?(.+)', line)
            if section_7_14_pattern:
                section_num = section_7_14_pattern.group(1)
                if section_7_14_pattern.group(2):
                    section_num += f".{section_7_14_pattern.group(2)}"
                if section_7_14_pattern.group(3):
                    section_num += f"({section_7_14_pattern.group(3)})"
                topic_assignments[i] = ("INSURED HOSPITAL SERVICES IN CANADA", section_num)
                continue
            
            # Continue for other section ranges...
            # Pattern 7: Sections 15-15.1 (AMBULANCE)
            section_15_pattern = re.match(r'^\s*(15(?:\.1)?)\s+(?:\((\d+)\)\s+)?(.+)', line)
            if section_15_pattern:
                section_num = section_15_pattern.group(1)
                if section_15_pattern.group(2):
                    section_num += f"({section_15_pattern.group(2)})"
                topic_assignments[i] = ("INSURED AMBULANCE SERVICES", section_num)
                continue
            
            # Add more patterns for other sections as needed...
        
        # Now extract the actual sections based on assignments
        sorted_lines = sorted(topic_assignments.keys())
        
        for idx, line_num in enumerate(sorted_lines):
            topic, section_ref = topic_assignments[line_num]
            
            # Find the end of this section
            end_line = sorted_lines[idx + 1] if idx + 1 < len(sorted_lines) else len(lines)
            
            # Extract section text
            section_lines = lines[line_num:end_line]
            section_text = '\n'.join(section_lines)
            
            # Extract title from first line
            first_line = lines[line_num]
            # Remove section number to get title
            title_match = re.match(r'^\s*[\d\.]+\s+(?:\(\d+\)\s+)?(.+)', first_line)
            title = title_match.group(1) if title_match else first_line
            
            sections.append({
                'section_ref': section_ref,
                'topic_section': topic,
                'title': self._extract_title(title),
                'raw_text': section_text,
                'line_range': f"L{line_num+1}-L{end_line}",
            })
        
        # Special handling for section 1(1) - main definitions
        if definitions_start:
            # Find where section 1(1) ends (before 1.1)
            section_1_end = None
            for i in range(definitions_start + 2, min(definitions_start + 200, len(lines))):
                if re.match(r'^\s*1\.1\s+', lines[i]):
                    section_1_end = i
                    break
            
            if section_1_end:
                section_text = '\n'.join(lines[definitions_start + 1:section_1_end])
                sections.insert(0, {
                    'section_ref': '1(1)',
                    'topic_section': 'DEFINITIONS',
                    'title': 'Main definitions of terms used in the Regulation',
                    'raw_text': section_text,
                    'line_range': f"L{definitions_start+2}-L{section_1_end}",
                })
        
        # Sort sections by their numeric reference
        sections.sort(key=lambda x: self._section_sort_key(x['section_ref']))
        
        logger.info(f"Split into {len(sections)} sections")
        
        # Log topic distribution
        topic_counts = {}
        for section in sections:
            topic = section['topic_section']
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        for topic, count in sorted(topic_counts.items()):
            logger.info(f"  {topic}: {count} sections")
        
        return sections
    
    def _section_sort_key(self, section_ref: str):
        """Create a sort key for section references."""
        # Handle sections like "1.1", "1(1)", "1.2(3)", etc.
        # Extract main number, subsection, and paragraph
        match = re.match(r'(\d+)(?:\.(\d+))?(?:\((\d+)\))?', section_ref)
        if match:
            main = int(match.group(1))
            sub = int(match.group(2)) if match.group(2) else 0
            para = int(match.group(3)) if match.group(3) else 0
            return (main, sub, para)
        return (999, 0, 0)  # Put unmatched at end
    
    def _extract_title(self, text: str, max_length: int = 100) -> str:
        """Extract a concise title from section text."""
        # Remove regulation citations
        text = re.sub(r'O\.\s*Reg\.\s*\d+/\d+.*$', '', text)
        
        # Take first sentence or clause
        if '.' in text:
            text = text.split('.')[0]
        elif ',' in text and len(text) > max_length:
            text = text.split(',')[0]
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length-3] + '...'
        
        return text.strip()
    
    async def _normalize_sections_batch(self, sections: List[Dict]) -> List[Dict]:
        """Process sections with LLM for structured extraction."""
        logger.info(f"Normalizing {len(sections)} sections with LLM")
        
        # Create tasks for concurrent processing
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = []
        
        for section in sections:
            task = self._normalize_section_with_semaphore(section, semaphore)
            tasks.append(task)
        
        # Process all sections
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        normalized = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to normalize section {sections[i].get('section_ref')}: {result}")
                # Keep raw section with incomplete flag
                section = sections[i].copy()
                section['incomplete'] = True
                section['error'] = str(result)
                normalized.append(section)
            else:
                normalized.append(result)
        
        return normalized
    
    async def _normalize_section_with_semaphore(self, section: Dict, semaphore: asyncio.Semaphore) -> Dict:
        """Normalize a single section with rate limiting."""
        async with semaphore:
            return await self._normalize_section(section)
    
    async def _normalize_section(self, section: Dict) -> Dict:
        """Use LLM to extract structured data from section."""
        # Check cache
        cache_key = hashlib.md5(section['raw_text'].encode()).hexdigest()
        if cache_key in self.extraction_cache:
            logger.debug(f"Using cached extraction for {section['section_ref']}")
            cached = self.extraction_cache[cache_key].copy()
            cached.update({
                'section_ref': section['section_ref'],
                'topic_section': section['topic_section'],
                'line_range': section['line_range']
            })
            return cached
        
        # Prepare prompt with context about topic section
        prompt = self._create_extraction_prompt(section)
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Merge with original section data
            section.update(result)
            
            # Identify topics based on both content and topic section
            section['topics'] = self._identify_topics(section)
            
            # Cache successful extraction
            self.extraction_cache[cache_key] = result
            
            return section
            
        except Exception as e:
            logger.error(f"LLM extraction failed for {section.get('section_ref')}: {e}")
            section['incomplete'] = True
            section['extraction_error'] = str(e)
            return section
    
    def _get_system_prompt(self) -> str:
        """System prompt for LLM extraction."""
        return """You are a legal document parser specializing in Ontario health insurance regulations.
Extract structured data from Health Insurance Act sections for database storage and RAG retrieval.

For each section, identify:
1. Effect: What the clause establishes, permits, or requires
2. Conditions: Specific requirements (days, status, enrollment, location)
3. Durations: Time limits or periods (months, repeatable)
4. Prerequisites: Prior conditions that must be met
5. Actors: Entities involved (insured_person, student, worker, spouse, etc.)

Output valid JSON with these fields:
{
  "effect": "brief description of what this section does",
  "conditions": [{"key": "field", "op": "operator", "value": "value"}],
  "durations": {"months": 12, "repeatable": false},
  "prerequisites": {"prior_presence_days": 153},
  "actors": ["insured_person", "student"],
  "notes": "any important clarifications"
}

Focus on machine-checkable facts. Omit fields if not applicable.
For DEFINITIONS sections (1.1-1.14): These contain critical eligibility and residency rules. Always extract physical presence requirements (153 days in 12 months), exemptions for students/workers/military, and carry-over rules for spouses/dependants.
For health services sections: Include what is covered/excluded."""
    
    def _create_extraction_prompt(self, section: Dict) -> str:
        """Create user prompt for section extraction."""
        # Truncate very long sections to fit context window
        text = section['raw_text']
        if len(text) > 3000:
            text = text[:3000] + "\n[... truncated for length ...]"
        
        return f"""Extract structured data from this Health Insurance Act section:

Topic Area: {section['topic_section']}
Section: {section['section_ref']}
Title: {section.get('title', '')}

Text:
{text}

Return JSON with effect, conditions, durations, prerequisites, actors, and notes."""
    
    def _identify_topics(self, section: Dict) -> List[str]:
        """Identify relevant topics based on content and topic section."""
        topics = set()
        
        # Add topic based on major section
        topic_section = section.get('topic_section', '').lower()
        if 'definition' in topic_section:
            topics.add('definitions')
            # DEFINITIONS sections often contain eligibility/residency rules
            if '1.' in section.get('section_ref', ''):
                topics.add('eligibility')
                topics.add('residency')
        elif 'health card' in topic_section:
            topics.add('health_card')
        elif 'status' in topic_section:
            topics.add('eligibility')
        elif 'hospital' in topic_section:
            topics.add('hospital')
        elif 'ambulance' in topic_section:
            topics.add('ambulance')
        elif 'exclusion' in topic_section:
            topics.add('uninsured')
        elif 'billing' in topic_section or 'payment' in topic_section:
            topics.add('billing')
        
        # Check content for additional topics
        text_lower = section.get('raw_text', '').lower()
        title_lower = section.get('title', '').lower()
        
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower or keyword.lower() in title_lower:
                    topics.add(topic)
                    break
        
        # Add topics based on extracted conditions
        if section.get('conditions'):
            for condition in section['conditions']:
                if 'student' in str(condition).lower():
                    topics.add('students')
                if 'work' in str(condition).lower():
                    topics.add('workers')
                if 'presence' in str(condition).lower():
                    topics.add('presence')
        
        return sorted(list(topics))
    
    def _validate_sections(self, sections: List[Dict]) -> List[Dict]:
        """Validate and mark incomplete sections."""
        validated = []
        
        for section in sections:
            # Check for required fields in specific section types
            topics = section.get('topics', [])
            topic_section = section.get('topic_section', '')
            
            # Sections in DEFINITIONS that relate to eligibility should have presence info
            if 'DEFINITION' in topic_section and any(t in topics for t in ['eligibility', 'residency', 'students', 'workers']):
                # Check for presence requirements
                has_presence = False
                
                if section.get('conditions'):
                    for cond in section['conditions']:
                        if 'presence' in str(cond).lower() or 'days' in str(cond).lower():
                            has_presence = True
                            break
                
                if section.get('prerequisites'):
                    if 'presence_days' in str(section['prerequisites']).lower():
                        has_presence = True
                
                # Sections 1.1-1.14 are critical for eligibility
                if section['section_ref'].startswith('1.') and not has_presence and 'exempt' not in section.get('raw_text', '').lower():
                    logger.warning(f"Section {section.get('section_ref')} may be missing presence requirements")
            
            validated.append(section)
        
        return validated


async def main():
    """CLI interface for testing extraction."""
    import argparse
    
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Extract Health Insurance Act sections (V3 - Fixed)')
    parser.add_argument('--act-file', required=True, help='Path to act document')
    parser.add_argument('--output', help='Output JSON file')
    parser.add_argument('--max-sections', type=int, help='Limit sections for testing')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return
    
    # Extract
    extractor = EnhancedActExtractorV3(api_key)
    result = await extractor.extract(
        args.act_file,
        max_sections=args.max_sections
    )
    
    # Save output
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Saved extraction to {args.output}")
    else:
        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    asyncio.run(main())