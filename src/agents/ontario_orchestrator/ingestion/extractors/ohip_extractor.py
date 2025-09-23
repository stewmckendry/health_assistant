#!/usr/bin/env python3
"""Enhanced subsection extraction with better table handling and chunking."""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dotenv import load_dotenv
load_dotenv()

import logging
import asyncio
import json
import re
import time
import pdfplumber
from typing import Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TOCEntry:
    section_code: Optional[str]
    title: str
    page_ref: str
    level: int
    specialty_code: Optional[str] = None
    parent_section: Optional[str] = None

class EnhancedSubsectionExtractor:
    def __init__(self, openai_api_key: str, max_concurrent: int = 5):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.max_concurrent = max_concurrent
        self.pdf_file = None
        self.page_mapping = {}
        self.section_ranges = {}
        # Optimized limits for faster processing
        self.max_chars_per_chunk = 35000  # Increased from 20000 for fewer chunks
        self.max_pages_per_chunk = 40     # Increased from 30
        
    def load_cleaned_page_ranges(self) -> Dict[str, Dict]:
        """Load cleaned page ranges for main sections."""
        page_ranges_file = Path('data/processed/cleaned_page_ranges.json')
        
        if page_ranges_file.exists():
            print('\nLoading cleaned page ranges...')
            with open(page_ranges_file) as f:
                data = json.load(f)
                ranges = data['ranges']
                print(f'  Loaded {len(ranges)} main section ranges')
                return ranges
        else:
            print('\nCleaned page ranges not found')
            return {}
    
    def build_page_reference_mapping(self, pdf_file: str) -> Dict[str, int]:
        """Build mapping from page references to actual PDF page numbers."""
        # Check for cached mapping first
        cache_file = Path('data/processed/page_reference_mapping.json')
        
        if cache_file.exists():
            logger.info('Loading cached page reference mapping...')
            with open(cache_file) as f:
                mapping = json.load(f)
            logger.info(f'Loaded mapping for {len(mapping)} page references')
            return mapping
        
        # Build mapping if not cached
        logger.info('Building page reference mapping (this will be cached for future runs)...')
        mapping = {}
        
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    footer_pattern = r'\b([A-Z]{1,2}\d{1,4})\b'
                    footer_text = text[-200:]
                    matches = re.findall(footer_pattern, footer_text)
                    for match in matches:
                        if match not in mapping:
                            mapping[match] = page_num
                            if len(mapping) % 50 == 0:
                                logger.info(f'  Mapped {len(mapping)} page references...')
        
        # Cache the mapping for future use
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(mapping, f, indent=2)
        
        logger.info(f'Built and cached mapping for {len(mapping)} page references')
        return mapping
    
    def get_subsection_page_range(self, subsection: Dict, all_entries: List[Dict], 
                                 page_mapping: Dict[str, int], section_ranges: Dict[str, Dict]) -> Optional[Tuple[int, int]]:
        """Determine actual page range for a subsection."""
        page_ref = subsection['page_ref']
        parent = subsection.get('parent')
        
        # Get start page from page reference
        if page_ref not in page_mapping:
            match = re.match(r'([A-Z]{1,2})(\d+)', page_ref)
            if not match:
                return None
            
            section_code = match.group(1)
            ref_num = int(match.group(2))
            
            if section_code in section_ranges:
                section_start = section_ranges[section_code]['start']
                start_page = section_start + ref_num - 1
            else:
                return None
        else:
            start_page = page_mapping[page_ref]
        
        # Find end page
        end_page = None
        subsection_idx = None
        for idx, entry in enumerate(all_entries):
            if (entry['page_ref'] == page_ref and 
                entry['title'] == subsection['title'] and
                entry['level'] == subsection['level']):
                subsection_idx = idx
                break
        
        if subsection_idx is not None:
            for idx in range(subsection_idx + 1, len(all_entries)):
                next_entry = all_entries[idx]
                
                if next_entry['level'] == 0:
                    break
                    
                if next_entry['level'] == 1 and next_entry.get('parent') == parent:
                    next_page_ref = next_entry['page_ref']
                    if next_page_ref in page_mapping:
                        end_page = page_mapping[next_page_ref] - 1
                        break
                    else:
                        match = re.match(r'([A-Z]{1,2})(\d+)', next_page_ref)
                        if match and match.group(1) == parent:
                            ref_num = int(match.group(2))
                            if parent in section_ranges:
                                section_start = section_ranges[parent]['start']
                                end_page = section_start + ref_num - 2
                                break
        
        if end_page is None and parent and parent in section_ranges:
            end_page = section_ranges[parent]['end']
        
        if start_page and end_page and start_page <= end_page:
            return (start_page, end_page)
        
        return None
    
    def detect_table_structure(self, text: str) -> Dict:
        """Detect and analyze table structures in the text."""
        table_indicators = {
            'multi_column': False,
            'has_h_p_columns': False,
            'has_asst_surg_anae': False,
            'has_time_requirements': False,
            'has_fee_amounts': False,
            'table_sections': []
        }
        
        # Check for H/P column structure
        if re.search(r'\bH\s+P\b|\bHospital\s+Professional\b', text):
            table_indicators['has_h_p_columns'] = True
            table_indicators['multi_column'] = True
        
        # Check for Asst/Surg/Anae columns
        if re.search(r'\bAsst\s+Surg\s+Anae\b', text):
            table_indicators['has_asst_surg_anae'] = True
            table_indicators['multi_column'] = True
        
        # Check for time requirements tables
        if re.search(r'\d+\s+minutes?\b.*before.*payable', text):
            table_indicators['has_time_requirements'] = True
        
        # Check for fee amounts
        if re.search(r'\$?\d+\.\d{2}|\d+\.\d{2}\s*$', text):
            table_indicators['has_fee_amounts'] = True
        
        # Find potential table sections (areas with aligned columns)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Look for lines with multiple numeric values or aligned columns
            if re.search(r'\d+\.\d{2}\s+\d+\.\d{2}', line) or \
               re.search(r'\s{10,}\d+\.\d{2}', line):
                table_indicators['table_sections'].append((i, line))
        
        return table_indicators
    
    async def extract_section_text_chunked(self, pdf_file: str, start_page: int, end_page: int) -> List[str]:
        """Extract text in chunks to avoid truncation."""
        def extract_pages_chunked(file_path: str, start: int, end: int) -> List[str]:
            chunks = []
            current_chunk = []
            current_size = 0
            
            with pdfplumber.open(file_path) as pdf:
                for page_num in range(start - 1, min(end, len(pdf.pages))):
                    if page_num < len(pdf.pages):
                        page_text = pdf.pages[page_num].extract_text()
                        if page_text:
                            page_content = f'--- PAGE {page_num + 1} ---\n{page_text}'
                            page_size = len(page_content)
                            
                            # Start new chunk if adding this page would exceed limits
                            if current_size + page_size > self.max_chars_per_chunk and current_chunk:
                                chunks.append('\n\n'.join(current_chunk))
                                current_chunk = []
                                current_size = 0
                            
                            current_chunk.append(page_content)
                            current_size += page_size
            
            # Add remaining chunk
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            
            return chunks
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_pages_chunked, pdf_file, start_page, end_page)
    
    async def process_subsection_chunk(self, chunk_text: str, subsection: Dict, 
                                      chunk_num: int, total_chunks: int,
                                      table_indicators: Dict) -> Dict:
        """Process a single chunk of subsection text."""
        
        title = subsection['title']
        page_ref = subsection['page_ref']
        parent = subsection.get('parent', '')
        
        # Adjust prompt based on detected table structures
        table_instructions = ""
        if table_indicators['multi_column']:
            if table_indicators['has_h_p_columns']:
                table_instructions += """
IMPORTANT: This section contains H/P (Hospital/Professional) fee columns.
Extract BOTH H and P fees when present. Look for aligned columns of numbers."""
            if table_indicators['has_asst_surg_anae']:
                table_instructions += """
IMPORTANT: This section contains Asst/Surg/Anae fee columns.
Extract ALL three fee types when present."""
        
        if table_indicators['has_time_requirements']:
            table_instructions += """
IMPORTANT: This section contains time requirement tables.
Look for services with minimum time requirements (e.g., "30 minutes", "60 minutes").
Extract the service descriptions AND the time requirements."""
        
        prompt = f"""Extract fee codes and billing information from this OHIP Schedule subsection.
This is chunk {chunk_num} of {total_chunks} for this subsection.

Subsection: {title}
Parent Section: {parent}
Page Reference: {page_ref}
{table_instructions}

IMPORTANT: Distinguish between FEE DEFINITIONS and CODE REFERENCES:

FEE DEFINITIONS (extract as fee_codes):
- Have an associated dollar amount or unit value
- Examples: "K001 - Detention ... 21.10", "A001 ... $45.00"
- These define what can be billed and for how much

CODE REFERENCES (extract as referenced_codes):
- Mentioned WITHOUT fee amounts
- Found in:
  * "APPLICABLE FEE CODES" tables
  * Payment rules (e.g., "not payable with G010, G039...")
  * Delegated procedure lists
  * Text lists like "E080, G010, G039, G040..."
- These provide billing rules/context but don't define the fee

COLUMN MEANINGS (when present):
- H = Hospital (technical component fee)
- P = Professional (physician interpretation fee)  
- T = Technical component fee
- Asst = Assistant surgeon fee (in units or dollars)
- Surg = Primary surgeon fee
- Anae = Anaesthetist fee (in units or dollars)

For FEE DEFINITIONS, extract:
- code: The exact fee code
- description: Full description of the service
- fee: Single fee amount in dollars (REQUIRED for fee definitions)
- h_fee: Hospital fee in dollars (if H column present)
- p_fee: Professional fee in dollars (if P column present)
- t_fee: Technical component fee in dollars
- asst_fee: Assistant fee (units or dollars)
- surg_fee: Surgeon fee (units or dollars)  
- anae_fee: Anaesthetist fee (units or dollars)
- units: Any unit/time requirements
- conditions: Special conditions or rules
- special_prefix: # = special approval required, + = additional fee

For CODE REFERENCES, extract:
- code: The referenced code
- context: Why it's referenced (e.g., "delegated procedure", "not payable with", "applicable for")
- description: Any description provided (if available)

Return JSON with:
{{
  "fee_codes": [...],  // Codes WITH defined fees
  "referenced_codes": [...]  // Codes WITHOUT fees (contextual references)
}}

Text:
{chunk_text}"""
        
        # Call LLM with higher token limit for complex tables
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract medical billing codes and fee tables accurately. Pay special attention to multi-column tables and time requirements."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=6000  # Increased from 4000
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f'Error processing chunk {chunk_num}: {e}')
            return {'fee_codes': [], 'error': str(e)}
    
    async def process_subsection(self, subsection: Dict, start_page: int, end_page: int, pdf_file: str) -> Dict:
        """Process a subsection with chunking for better table capture."""
        try:
            title = subsection['title']
            page_ref = subsection['page_ref']
            parent = subsection.get('parent', '')
            
            logger.info(f'Processing subsection: {title} ({page_ref}, pages {start_page}-{end_page})...')
            
            # Extract text in chunks
            text_chunks = await self.extract_section_text_chunked(pdf_file, start_page, end_page)
            
            if not text_chunks:
                logger.warning(f'No text found for subsection {title}')
                return {
                    'subsection_title': title,
                    'page_ref': page_ref,
                    'parent_section': parent,
                    'error': 'No text found',
                    'fee_codes': []
                }
            
            # Save full text for inspection
            chunk_dir = Path('data/processed/subsection_chunks_enhanced')
            chunk_dir.mkdir(parents=True, exist_ok=True)
            
            safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title[:50])
            
            # Combine all chunks for analysis
            full_text = '\n\n'.join(text_chunks)
            
            # Detect table structures
            table_indicators = self.detect_table_structure(full_text)
            
            # Save full text with table analysis
            text_file = chunk_dir / f'subsection_{parent}_{page_ref}_{safe_title}.txt'
            with open(text_file, 'w') as f:
                f.write(f"Subsection: {title}\n")
                f.write(f"Parent Section: {parent}\n")
                f.write(f"Page Reference: {page_ref}\n")
                f.write(f"Pages: {start_page} to {end_page}\n")
                f.write(f"Text chunks: {len(text_chunks)}\n")
                f.write(f"Total text length: {len(full_text)} characters\n")
                f.write(f"Table indicators: {json.dumps(table_indicators, indent=2)}\n")
                f.write("="*60 + "\n\n")
                f.write(full_text)
            
            logger.info(f'  Saved enhanced subsection text to {text_file.name}')
            logger.info(f'  Text chunks: {len(text_chunks)}, Total chars: {len(full_text)}')
            
            # Check for fee codes in text
            fee_code_pattern = r'[A-Z]\d{3,4}[A-Z]?'
            sample_codes = re.findall(fee_code_pattern, full_text[:3000])
            if sample_codes:
                logger.info(f'  Sample fee codes found: {sample_codes[:8]}')
            
            # Process each chunk
            all_fee_codes = []
            all_referenced_codes = []
            seen_codes = set()
            seen_refs = set()
            
            for i, chunk in enumerate(text_chunks, 1):
                logger.info(f'  Processing chunk {i}/{len(text_chunks)} ({len(chunk)} chars)...')
                
                result = await self.process_subsection_chunk(
                    chunk, subsection, i, len(text_chunks), table_indicators
                )
                
                # Merge fee codes (with amounts), avoiding duplicates
                for fee_code in result.get('fee_codes', []):
                    code = fee_code.get('code')
                    if code and code not in seen_codes:
                        all_fee_codes.append(fee_code)
                        seen_codes.add(code)
                
                # Also store referenced codes separately (without amounts)
                for ref_code in result.get('referenced_codes', []):
                    code = ref_code.get('code')
                    if code and code not in seen_refs:
                        all_referenced_codes.append({
                            **ref_code,
                            'source_subsection': title,
                            'source_page': page_ref
                        })
                        seen_refs.add(code)
            
            # Build final result
            final_result = {
                'subsection_title': title,
                'parent_section': parent,
                'page_ref': page_ref,
                'pages_processed': f'{start_page}-{end_page}',
                'chunks_processed': len(text_chunks),
                'table_structures_detected': table_indicators,
                'fee_codes': all_fee_codes,
                'referenced_codes': all_referenced_codes,
                'rules': [],
                'notes': []
            }
            
            # Save enhanced result
            response_file = chunk_dir / f'subsection_{parent}_{page_ref}_response.json'
            with open(response_file, 'w') as f:
                json.dump(final_result, f, indent=2)
            
            logger.info(f'  Subsection {title}: Found {len(all_fee_codes)} unique fee codes')
            
            return final_result
            
        except Exception as e:
            logger.error(f'Error processing subsection {subsection.get("title", "")}: {e}')
            return {
                'subsection_title': subsection.get('title', ''),
                'page_ref': subsection.get('page_ref', ''),
                'parent_section': subsection.get('parent', ''),
                'error': str(e),
                'fee_codes': []
            }
    
    async def process_subsections(self, toc_file: str, pdf_file: str, max_subsections: int = None, 
                                 target_sections: List[str] = None):
        """Process subsections with enhanced table handling."""
        # Load TOC
        with open(toc_file) as f:
            toc_data = json.load(f)
        
        self.pdf_file = pdf_file
        
        # Load main section ranges
        self.section_ranges = self.load_cleaned_page_ranges()
        
        # Build page reference mapping
        print('\nBuilding page reference mapping...')
        self.page_mapping = self.build_page_reference_mapping(pdf_file)
        
        # Get subsections to process
        subsections_to_process = []
        all_entries = toc_data['entries']
        
        for entry in all_entries:
            if entry['level'] == 1:
                if target_sections and entry.get('parent') not in target_sections:
                    continue
                    
                page_range = self.get_subsection_page_range(
                    entry, all_entries, self.page_mapping, self.section_ranges
                )
                
                if page_range:
                    subsections_to_process.append({
                        'entry': entry,
                        'start_page': page_range[0],
                        'end_page': page_range[1]
                    })
        
        if max_subsections:
            subsections_to_process = subsections_to_process[:max_subsections]
        
        print(f'\nProcessing {len(subsections_to_process)} subsections with enhanced extraction...')
        
        # Show sample
        print('\nSample subsections to process:')
        for item in subsections_to_process[:5]:
            entry = item['entry']
            pages = item['end_page'] - item['start_page'] + 1
            print(f'  {entry.get("parent", "")} | {entry["page_ref"]} | {entry["title"][:40]:40} | {pages:3} pages')
        
        # Process in parallel
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(item: Dict):
            async with semaphore:
                return await self.process_subsection(
                    item['entry'], 
                    item['start_page'], 
                    item['end_page'],
                    pdf_file
                )
        
        tasks = [process_with_semaphore(item) for item in subsections_to_process]
        
        # Run tasks
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Save results - create section-specific output file
        if target_sections:
            # Use section-specific filename
            sections_str = '_'.join(target_sections)
            output_file = Path(f'data/processed/section_{sections_str}_extracted.json')
        else:
            # Default filename when no specific sections
            output_file = Path('data/processed/subsections_enhanced.json')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        output_data = {
            'source_pdf': pdf_file,
            'toc_file': toc_file,
            'subsections_processed': len(results),
            'extraction_time': elapsed,
            'extraction_method': 'enhanced_chunking',
            'subsections': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        # Summary
        total_codes = sum(len(r.get('fee_codes', [])) for r in results)
        successful = sum(1 for r in results if 'error' not in r)
        with_tables = sum(1 for r in results if r.get('table_structures_detected', {}).get('multi_column'))
        
        print(f'\n' + '='*60)
        print(f'ENHANCED EXTRACTION COMPLETE')
        print(f'='*60)
        print(f'✓ Processed {len(results)} subsections in {elapsed:.1f}s')
        print(f'✓ Successful: {successful}/{len(results)}')
        print(f'✓ Multi-column tables detected: {with_tables}')
        print(f'✓ Total fee codes extracted: {total_codes}')
        print(f'✓ Saved results to: {output_file}')
        print(f'✓ Enhanced chunks saved to: data/processed/subsection_chunks_enhanced/')
        
        # Show sample results
        print('\nSample results:')
        for result in results[:5]:
            if 'error' not in result:
                codes = len(result.get('fee_codes', []))
                chunks = result.get('chunks_processed', 1)
                tables = 'Yes' if result.get('table_structures_detected', {}).get('multi_column') else 'No'
                print(f'  {result["parent_section"]:3} | {result["page_ref"]:5} | {codes:4} codes | {chunks} chunks | Tables: {tables}')

async def main():
    # Configuration
    TOC_FILE = 'data/processed/toc_extracted.json'
    PDF_FILE = "data/ontario/ohip/moh-schedule-benefit-2024-03-04.pdf"
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced OHIP subsection extraction')
    parser.add_argument('--max-subsections', type=int, default=None, 
                       help='Maximum number of subsections to process')
    parser.add_argument('--sections', nargs='+', default=None,
                       help='Specific sections to process (e.g., GP A B)')
    parser.add_argument('--test-assessment', action='store_true',
                       help='Test on GP Assessment subsection specifically')
    args = parser.parse_args()
    
    # Check if TOC exists
    if not Path(TOC_FILE).exists():
        print(f'TOC file not found: {TOC_FILE}')
        print('Run extract_toc_fast.py first to generate TOC')
        return
    
    # Extract subsections
    extractor = EnhancedSubsectionExtractor(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        max_concurrent=8  # Increased for faster parallel processing
    )
    
    # Test with specific sections or default
    if args.test_assessment:
        # Test specifically on GP Assessment which has complex tables
        target_sections = ['GP']
        # Process subsections around GP21-GP30 (Assessment section)
        await extractor.process_subsections(
            TOC_FILE, 
            PDF_FILE, 
            max_subsections=5,  # Just test a few around assessment
            target_sections=target_sections
        )
    else:
        target_sections = args.sections if args.sections else ['GP']
        await extractor.process_subsections(
            TOC_FILE, 
            PDF_FILE, 
            max_subsections=args.max_subsections,
            target_sections=target_sections
        )

if __name__ == '__main__':
    asyncio.run(main())