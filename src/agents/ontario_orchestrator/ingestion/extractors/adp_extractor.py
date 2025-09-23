#!/usr/bin/env python3
"""
Enhanced ADP (Assistive Devices Program) PDF Extractor
Extracts subsection-level chunks with light structured data extraction for V1
"""

import re
import json
import logging
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import concurrent.futures

try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'pdfplumber'])
    import pdfplumber

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ADPSection:
    """Represents an ADP policy section"""
    adp_doc: str
    part: Optional[str]
    section_id: str
    title: str
    raw_text: str
    policy_uid: str
    topics: List[str]
    funding: List[Dict]
    exclusions: List[Dict]
    page_num: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "adp_doc": self.adp_doc,
            "part": self.part,
            "section_id": self.section_id,
            "title": self.title,
            "raw_text": self.raw_text,
            "policy_uid": self.policy_uid,
            "topics": self.topics,
            "funding": self.funding,
            "exclusions": self.exclusions,
            "page_num": self.page_num
        }

class EnhancedADPExtractor:
    """Extract subsection chunks and minimal structured data from ADP PDFs"""
    
    # Regex patterns for section detection
    SECTION_RE = re.compile(
        r'^(?P<section>\d{3}(?:\.\d{2})?)\s+(?P<title>[^\n]+)',  # "100 Purpose of the Manual"
        re.MULTILINE
    )
    
    PART_RE = re.compile(r'^Part\s+(?P<part>\d+)\b.*', re.MULTILINE)
    
    # Topics detection keywords
    TOPIC_KEYWORDS = {
        "eligibility": ["eligible", "eligibility", "qualify", "qualifies", "meet criteria"],
        "exclusions": ["not eligible", "excluded", "does not fund", "not covered", "exceptions"],
        "funding": ["client pays", "approved price", "funding", "cost", "payment", "%", "percent"],
        "warranty": ["warranty", "guarantee", "service", "repair"],
        "roles": ["vendor", "prescriber", "authorizer", "practitioner", "responsibility"],
        "leasing": ["lease", "CEP", "rental", "continuous eligibility"],
        "requirements": ["required", "must", "shall", "necessary", "mandatory"]
    }
    
    # Funding patterns
    FUNDING_PATTERNS = [
        (re.compile(r'client\s+pays?\s+(\d+)\s*%', re.I), 'percentage'),
        (re.compile(r'(\d+)\s*%\s+.*?(client|consumer)', re.I), 'percentage'),
        (re.compile(r'approved\s+price', re.I), 'approved_price'),
        (re.compile(r'(lease|CEP|continuous\s+eligibility)', re.I), 'lease'),
        (re.compile(r'repair', re.I), 'repair'),
        (re.compile(r'accessories', re.I), 'accessories'),
        (re.compile(r'speaking\s+valve|voice\s+restoration', re.I), 'special_case'),
    ]
    
    # Exclusion patterns and canonical phrases
    EXCLUSION_PATTERNS = [
        (re.compile(r'not\s+eligible|does\s+not\s+fund|excluded|not\s+covered', re.I), 'general'),
        (re.compile(r'training|exercise|therapy.*only', re.I), 'training/exercise/therapy only'),
        (re.compile(r'education|school|work|recreation.*only', re.I), 'education/work/recreation only'),
        (re.compile(r'alternative\s+transportation|community\s+travel\s+only|intermittent\s+use', re.I), 
         'alternative transport / intermittent use'),
        (re.compile(r'backup|spare|duplicate', re.I), 'backup/spare/duplicate'),
        (re.compile(r'cosmetic|aesthetic', re.I), 'cosmetic purposes'),
    ]
    
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        
    def load_pdf_text(self, path: str) -> Tuple[str, Dict[int, str]]:
        """Load text from PDF, return full text and page mapping"""
        full_text = []
        page_texts = {}
        
        try:
            with pdfplumber.open(path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    page_texts[i + 1] = text
                    full_text.append(f"\n--- Page {i + 1} ---\n{text}")
                    
            return "\n".join(full_text), page_texts
        except Exception as e:
            logger.error(f"Error loading PDF {path}: {e}")
            raise
            
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        # Remove page headers/footers (common patterns)
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'Ministry of Health.*?Policy.*?Manual', '', text, flags=re.I)
        return text.strip()
    
    def detect_topics(self, body: str) -> List[str]:
        """Detect topics present in section body"""
        topics = []
        body_lower = body.lower()
        
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(keyword in body_lower for keyword in keywords):
                topics.append(topic)
                
        return topics
    
    def harvest_funding(self, body: str) -> List[Dict]:
        """Extract funding rules from section body"""
        funding_rules = []
        seen = set()
        
        # Split into sentences for context
        sentences = re.split(r'[.!?]\s+', body)
        
        for sentence in sentences:
            for pattern, pattern_type in self.FUNDING_PATTERNS:
                match = pattern.search(sentence)
                if match:
                    # Determine scenario
                    sentence_lower = sentence.lower()
                    if 'lease' in sentence_lower or 'cep' in sentence_lower:
                        scenario = 'lease'
                    elif 'repair' in sentence_lower:
                        scenario = 'repair'
                    elif 'accessor' in sentence_lower:
                        scenario = 'accessories'
                    else:
                        scenario = 'purchase'
                    
                    # Extract client share percentage if present
                    client_share = None
                    if pattern_type == 'percentage' and match.groups():
                        try:
                            client_share = float(match.group(1))
                        except:
                            pass
                    
                    # Create rule entry
                    rule_key = f"{scenario}:{client_share}"
                    if rule_key not in seen:
                        rule = {
                            "scenario": scenario,
                            "client_share_percent": client_share,
                            "details": sentence[:200].strip()  # First 200 chars
                        }
                        funding_rules.append(rule)
                        seen.add(rule_key)
                        
        return funding_rules
    
    def harvest_exclusions(self, body: str) -> List[Dict]:
        """Extract exclusion phrases from section body"""
        exclusions = []
        seen = set()
        
        # Split into sentences for context
        sentences = re.split(r'[.!?]\s+', body)
        
        for sentence in sentences:
            for pattern, canonical_phrase in self.EXCLUSION_PATTERNS:
                if pattern.search(sentence):
                    if canonical_phrase not in seen:
                        # Try to determine what it applies to
                        applies_to = None
                        sentence_lower = sentence.lower()
                        if 'mobility' in sentence_lower or 'wheelchair' in sentence_lower:
                            applies_to = 'mobility'
                        elif 'communication' in sentence_lower or 'aac' in sentence_lower:
                            applies_to = 'communication_aids'
                        elif 'power' in sentence_lower:
                            applies_to = 'power_wheelchair'
                            
                        exclusion = {
                            "phrase": canonical_phrase,
                            "applies_to": applies_to
                        }
                        exclusions.append(exclusion)
                        seen.add(canonical_phrase)
                        
        return exclusions
    
    def find_current_part(self, text: str, position: int) -> Optional[str]:
        """Find the current part number at given position"""
        # Look backwards for the most recent Part declaration
        text_before = text[:position]
        parts = list(self.PART_RE.finditer(text_before))
        if parts:
            return parts[-1].group('part')
        return None
    
    def extract_section_body(self, text: str, start: int, end: Optional[int] = None) -> str:
        """Extract section body text, handling overlap"""
        if end is None:
            body = text[start:]
        else:
            body = text[start:end]
            
        # Clean up the body text
        body = self.clean_text(body)
        
        # Limit to reasonable size (about 600 tokens)
        max_chars = 3000
        if len(body) > max_chars:
            body = body[:max_chars] + "..."
            
        return body
    
    def infer_doc_kind(self, path: str) -> str:
        """Infer document type from filename"""
        path_lower = str(path).lower()
        if 'communication' in path_lower or 'comm' in path_lower:
            return 'comm_aids'
        elif 'mobility' in path_lower:
            return 'mobility'
        elif 'core' in path_lower or 'procedure' in path_lower:
            return 'core_manual'
        else:
            logger.warning(f"Could not infer document type from {path}, defaulting to 'core_manual'")
            return 'core_manual'
    
    def extract(self, path: str, adp_doc: Optional[str] = None) -> List[ADPSection]:
        """Extract all sections from ADP PDF"""
        if adp_doc is None:
            adp_doc = self.infer_doc_kind(path)
            
        logger.info(f"Extracting from {path} as {adp_doc}")
        
        # Load PDF
        full_text, page_texts = self.load_pdf_text(path)
        
        # Find all sections
        sections = []
        section_matches = list(self.SECTION_RE.finditer(full_text))
        
        logger.info(f"Found {len(section_matches)} sections")
        
        for i, match in enumerate(section_matches):
            # Get section details
            section_id = match.group('section')
            title = match.group('title').strip()
            
            # Find section boundaries
            start = match.end()
            end = section_matches[i + 1].start() if i + 1 < len(section_matches) else None
            
            # Extract body
            body = self.extract_section_body(full_text, start, end)
            
            # Find current part
            part = self.find_current_part(full_text, match.start())
            
            # Create policy UID
            policy_uid = f"adp:{adp_doc}:{section_id}"
            
            # Detect topics
            topics = self.detect_topics(body)
            
            # Harvest structured data
            funding = self.harvest_funding(body)
            exclusions = self.harvest_exclusions(body)
            
            # Find page number (approximate)
            page_num = None
            for pnum, ptext in page_texts.items():
                if section_id in ptext and title[:30] in ptext:
                    page_num = pnum
                    break
            
            # Create section object
            section = ADPSection(
                adp_doc=adp_doc,
                part=part,
                section_id=section_id,
                title=title,
                raw_text=body,
                policy_uid=policy_uid,
                topics=topics,
                funding=funding,
                exclusions=exclusions,
                page_num=page_num
            )
            
            sections.append(section)
            
        logger.info(f"Extracted {len(sections)} sections from {path}")
        return sections
    
    def save_results(self, sections: List[ADPSection], output_path: str):
        """Save extraction results to JSON"""
        data = {
            "sections": [s.to_dict() for s in sections],
            "metadata": {
                "total_sections": len(sections),
                "unique_parts": len(set(s.part for s in sections if s.part)),
                "topics_coverage": list(set(t for s in sections for t in s.topics)),
                "funding_rules_count": sum(len(s.funding) for s in sections),
                "exclusions_count": sum(len(s.exclusions) for s in sections)
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved results to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Extract ADP policy sections from PDF')
    parser.add_argument('pdf_path', type=str, help='Path to ADP PDF')
    parser.add_argument('--doc-type', type=str, choices=['comm_aids', 'mobility', 'core_manual'],
                       help='Document type (auto-detected if not specified)')
    parser.add_argument('--output', type=str, help='Output JSON file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Extract sections
    extractor = EnhancedADPExtractor()
    sections = extractor.extract(args.pdf_path, args.doc_type)
    
    # Save if output specified
    if args.output:
        extractor.save_results(sections, args.output)
    else:
        # Print summary
        print(f"\nExtracted {len(sections)} sections")
        print(f"Topics found: {set(t for s in sections for t in s.topics)}")
        print(f"Funding rules: {sum(len(s.funding) for s in sections)}")
        print(f"Exclusions: {sum(len(s.exclusions) for s in sections)}")
        
        # Sample first few sections
        print("\nFirst 3 sections:")
        for s in sections[:3]:
            print(f"  {s.section_id}: {s.title}")
            print(f"    Topics: {', '.join(s.topics)}")
            print(f"    Funding rules: {len(s.funding)}")
            print(f"    Exclusions: {len(s.exclusions)}")

if __name__ == "__main__":
    main()