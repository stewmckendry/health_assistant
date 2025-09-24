"""CEP clinical tools ingester.

Ingests extracted CEP tool data into SQLite and Chroma databases
using the parent-child chunking strategy.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

# Import from parent package
from ..base_ingester import BaseOPAIngester
from .extractor import CEPExtractor, extract_cep_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CEPIngester(BaseOPAIngester):
    """Ingester for CEP clinical tools."""
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize CEP ingester.
        
        Args:
            db_path: Path to SQLite database
            chroma_path: Path to Chroma vector store
            openai_api_key: OpenAI API key for embeddings
        """
        # Load API key from environment if not provided
        if not openai_api_key:
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                # Try loading from .env file
                from dotenv import load_dotenv
                load_dotenv('/Users/liammckendry/health_assistant_dr_off_worktree/.env')
                openai_api_key = os.getenv('OPENAI_API_KEY')
        
        super().__init__(
            source_org='cep',
            db_path=db_path or "data/processed/dr_opa/opa.db",
            chroma_path=chroma_path or "data/processed/dr_opa/chroma",
            openai_api_key=openai_api_key
        )
        
        self.extractor = CEPExtractor()
        self.raw_dir = Path("data/dr_opa_agent/raw/cep")
        self.processed_dir = Path("data/dr_opa_agent/processed/cep")
    
    def fetch_document(self, url: str) -> tuple[str, str]:
        """Fetch and normalize CEP tool document.
        
        Args:
            url: Tool URL
            
        Returns:
            Tuple of (normalized_text, document_format)
        """
        # For CEP tools, we primarily work with pre-crawled HTML
        # This method is required by base class but not primary workflow
        import requests
        
        headers = {
            'User-Agent': 'Dr-OPA-Agent/1.0 (Ontario Practice Advice; Medical Education)'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
            
            # Extract tool info from URL
            import re
            match = re.search(r'/tool/([^/]+)/', url)
            if match:
                tool_slug = match.group(1)
                tool_info = {'slug': tool_slug, 'name': tool_slug.replace('-', ' ').title()}
            else:
                tool_info = {'slug': 'unknown', 'name': 'Unknown Tool'}
            
            # Extract content
            document = self.extractor.extract_from_html(html, url, tool_info)
            
            # Return summary as normalized text
            return document.get('summary', ''), 'html'
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return "", 'html'
    
    def ingest_tool(self, tool_slug: str) -> Dict[str, Any]:
        """Ingest a single CEP tool.
        
        Args:
            tool_slug: Tool slug (e.g., 'dementia-diagnosis')
            
        Returns:
            Ingestion statistics
        """
        try:
            logger.info(f"Ingesting CEP tool: {tool_slug}")
            
            # Load extracted data if exists, otherwise extract
            extracted_file = self.processed_dir / f"{tool_slug}_extracted.json"
            
            if extracted_file.exists():
                logger.info(f"Loading existing extraction: {extracted_file}")
                with open(extracted_file) as f:
                    document = json.load(f)
            else:
                # Extract from HTML
                html_file = self.raw_dir / f"{tool_slug}.html"
                meta_file = self.raw_dir / f"{tool_slug}_meta.json"
                
                if not html_file.exists():
                    raise FileNotFoundError(f"HTML file not found: {html_file}")
                
                # Load metadata
                with open(meta_file) as f:
                    tool_info = json.load(f)
                
                # Extract
                document = extract_cep_tool(html_file, tool_info)
                
                # Save extraction
                self.extractor.save_extracted_data(document)
            
            # Prepare document metadata for database
            doc_metadata = {
                'source_org': 'cep',
                'source_url': document['source_url'],
                'title': document['title'],
                'document_type': 'clinical_tool',
                'effective_date': document.get('last_updated'),
                'topics': [document['tool_category']] + document.get('keywords', []),
                'content_hash': document.get('content_hash', ''),
                'metadata_json': {
                    'category': document['tool_category'],
                    'features': document.get('features', {}),
                    'has_assessment_tools': bool(document.get('key_content', {}).get('assessment_tools')),
                    'navigation_items': len(document.get('navigation', [])),
                    'section_count': len(document.get('sections', [])),
                    'reference_count': len(document.get('references', []))
                },
                'ingested_at': datetime.now().isoformat()
            }
            
            # Create content for chunking
            # For CEP tools, we create specialized chunks:
            # 1. Overview chunk (summary + navigation)
            # 2. Section chunks (key content only)
            # 3. Reference chunks (for clinical guidance)
            
            chunks_to_store = []
            
            # 1. Create overview parent chunk
            overview_content = self._create_overview_content(document)
            overview_chunk = {
                'section_id': f"{document['document_id']}_overview",
                'document_id': document['document_id'],
                'chunk_type': 'parent',
                'section_heading': f"{document['title']} - Overview",
                'section_text': overview_content,
                'metadata': {
                    'source_org': 'cep',
                    'document_type': 'clinical_tool',
                    'chunk_role': 'overview',
                    'tool_category': document['tool_category'],
                    'has_navigation': True,
                    'source_url': document['source_url']
                }
            }
            chunks_to_store.append(overview_chunk)
            
            # 2. Create section chunks (as children of overview)
            for idx, section in enumerate(document.get('sections', [])[:10]):  # Limit sections
                section_content = self._create_section_content(section, document)
                section_chunk = {
                    'section_id': f"{document['document_id']}_section_{idx}",
                    'document_id': document['document_id'],
                    'chunk_type': 'child',
                    'parent_id': overview_chunk['section_id'],
                    'section_heading': section.get('heading', f"Section {idx+1}"),
                    'section_text': section_content,
                    'section_idx': idx,
                    'metadata': {
                        'source_org': 'cep',
                        'document_type': 'clinical_tool',
                        'chunk_role': 'section',
                        'section_level': section.get('level', 2),
                        'anchor': section.get('anchor', ''),
                        'source_url': document['source_url'] + (section.get('anchor', '') or '')
                    }
                }
                chunks_to_store.append(section_chunk)
            
            # 3. Create key content chunk if significant content exists
            if document.get('key_content'):
                key_content_text = self._create_key_content_text(document['key_content'])
                if key_content_text:
                    key_chunk = {
                        'section_id': f"{document['document_id']}_key_content",
                        'document_id': document['document_id'],
                        'chunk_type': 'child',
                        'parent_id': overview_chunk['section_id'],
                        'section_heading': 'Key Clinical Content',
                        'section_text': key_content_text,
                        'metadata': {
                            'source_org': 'cep',
                            'document_type': 'clinical_tool',
                            'chunk_role': 'key_content',
                            'source_url': document['source_url']
                        }
                    }
                    chunks_to_store.append(key_chunk)
            
            # Store document in database
            document_id = self._store_document(doc_metadata)
            
            # Prepare chunks for batch storage
            chunks_for_storage = []
            for chunk in chunks_to_store:
                chunks_for_storage.append({
                    'chunk_id': chunk['section_id'],
                    'text': chunk['section_text'],
                    'chunk_type': chunk['chunk_type'],
                    'parent_id': chunk.get('parent_id'),
                    'section_heading': chunk['section_heading'],
                    'section_idx': chunk.get('section_idx', 0),
                    'chunk_idx': chunk.get('chunk_idx', 0),
                    'metadata': chunk['metadata']
                })
            
            # Store chunks with embeddings
            stored_count = self.store_chunks_with_embeddings(chunks_for_storage, document_id)
            
            # Generate statistics
            stats = {
                'tool_slug': tool_slug,
                'document_id': document['document_id'],
                'title': document['title'],
                'chunks_created': len(chunks_to_store),
                'chunks_stored': stored_count,
                'sections': len(document.get('sections', [])),
                'navigation_items': len(document.get('navigation', [])),
                'has_key_content': bool(document.get('key_content')),
                'features': document.get('features', {}),
                'ingested_at': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully ingested {tool_slug}: {stored_count}/{len(chunks_to_store)} chunks stored")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error ingesting tool {tool_slug}: {e}")
            raise
    
    def _create_overview_content(self, document: Dict[str, Any]) -> str:
        """Create overview content for parent chunk."""
        parts = []
        
        # Title and summary
        parts.append(f"# {document['title']}")
        parts.append(f"\n{document.get('summary', '')}")
        
        # Category and metadata
        parts.append(f"\n**Category:** {document.get('tool_category', 'general').replace('_', ' ').title()}")
        if document.get('last_updated'):
            parts.append(f"**Last Updated:** {document['last_updated']}")
        parts.append(f"**URL:** {document['source_url']}")
        
        # Features
        features = document.get('features', {})
        active_features = [k.replace('has_', '').replace('_', ' ').title() 
                          for k, v in features.items() if v]
        if active_features:
            parts.append(f"\n**Available Features:** {', '.join(active_features)}")
        
        # Navigation structure
        navigation = document.get('navigation', [])
        if navigation:
            parts.append("\n## Tool Navigation")
            for nav in navigation[:10]:  # Limit items
                if nav.get('type') == 'heading_h2':
                    parts.append(f"- {nav['title']}")
                elif nav.get('type') == 'heading_h3':
                    parts.append(f"  - {nav['title']}")
        
        # Key assessment tools
        key_content = document.get('key_content', {})
        if key_content.get('assessment_tools'):
            parts.append(f"\n**Assessment Tools:** {', '.join(key_content['assessment_tools'])}")
        
        # Clinical capabilities
        capabilities = []
        if key_content.get('has_diagnostic_criteria'):
            capabilities.append('Diagnostic Criteria')
        if key_content.get('has_treatment_guidance'):
            capabilities.append('Treatment Guidance')
        if key_content.get('has_referral_criteria'):
            capabilities.append('Referral Criteria')
        
        if capabilities:
            parts.append(f"**Clinical Content:** {', '.join(capabilities)}")
        
        # Section overview
        sections = document.get('sections', [])
        if sections:
            parts.append(f"\n## Sections ({len(sections)})")
            for section in sections[:5]:  # Show first 5
                parts.append(f"- {section['heading']}")
                if section.get('summary'):
                    parts.append(f"  {section['summary'][:100]}...")
        
        return '\n'.join(parts)
    
    def _create_section_content(self, section: Dict[str, Any], document: Dict[str, Any]) -> str:
        """Create content for section chunk."""
        parts = []
        
        # Section heading
        parts.append(f"## {section['heading']}")
        
        # Link back to tool
        parts.append(f"*From: [{document['title']}]({document['source_url']}{section.get('anchor', '')})*")
        
        # Section summary
        if section.get('summary'):
            parts.append(f"\n{section['summary']}")
        
        # Subsections
        if section.get('subsections'):
            parts.append("\n### Subsections:")
            for subsection in section['subsections']:
                parts.append(f"- {subsection['heading']}")
        
        # Add direct link
        if section.get('anchor'):
            full_url = document['source_url'] + section['anchor']
            parts.append(f"\n[View Full Section]({full_url})")
        
        return '\n'.join(parts)
    
    def _create_key_content_text(self, key_content: Dict[str, Any]) -> str:
        """Create text from key content."""
        if not key_content:
            return ""
        
        parts = []
        
        # Assessment tools
        if key_content.get('assessment_tools'):
            parts.append(f"**Validated Assessment Tools:**")
            for tool in key_content['assessment_tools']:
                parts.append(f"- {tool}")
        
        # Red flags
        if key_content.get('red_flags'):
            parts.append(f"\n**Red Flags / Warning Signs:**")
            for flag in key_content['red_flags']:
                parts.append(f"- {flag}")
        
        # Clinical capabilities
        capabilities = []
        if key_content.get('has_diagnostic_criteria'):
            capabilities.append("Contains diagnostic criteria")
        if key_content.get('has_treatment_guidance'):
            capabilities.append("Provides treatment guidance")
        if key_content.get('has_referral_criteria'):
            capabilities.append("Includes referral criteria")
        
        if capabilities:
            parts.append(f"\n**Clinical Content Available:**")
            for cap in capabilities:
                parts.append(f"- {cap}")
        
        return '\n'.join(parts) if parts else ""
    
    def ingest_all_tools(self) -> Dict[str, Any]:
        """Ingest all available CEP tools.
        
        Returns:
            Summary statistics
        """
        # Find all extracted files
        extracted_files = list(self.processed_dir.glob("*_extracted.json"))
        
        if not extracted_files:
            logger.warning("No extracted files found. Run extraction first.")
            return {}
        
        logger.info(f"Found {len(extracted_files)} extracted tools to ingest")
        
        results = []
        failed = []
        
        for extracted_file in extracted_files:
            tool_slug = extracted_file.stem.replace('_extracted', '')
            
            try:
                stats = self.ingest_tool(tool_slug)
                results.append(stats)
                logger.info(f"✓ Ingested {tool_slug}")
            except Exception as e:
                logger.error(f"✗ Failed to ingest {tool_slug}: {e}")
                failed.append({'tool': tool_slug, 'error': str(e)})
        
        # Summary
        summary = {
            'total_tools': len(extracted_files),
            'successfully_ingested': len(results),
            'failed': len(failed),
            'total_chunks': sum(r['chunks_stored'] for r in results),
            'failed_tools': failed,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save summary
        summary_file = self.processed_dir / "ingestion_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\nIngestion Summary:")
        logger.info(f"  Total tools: {summary['total_tools']}")
        logger.info(f"  Successfully ingested: {summary['successfully_ingested']}")
        logger.info(f"  Failed: {summary['failed']}")
        logger.info(f"  Total chunks stored: {summary['total_chunks']}")
        logger.info(f"  Summary saved to: {summary_file}")
        
        return summary


def main():
    """Test ingestion with single tool."""
    import asyncio
    from .crawler import CEPCrawler
    
    # Ensure we have the dementia tool crawled
    crawler = CEPCrawler()
    
    # Check if already crawled
    html_file = Path("data/dr_opa_agent/raw/cep/dementia-diagnosis.html")
    if not html_file.exists():
        print("Crawling dementia diagnosis tool first...")
        asyncio.run(crawler.crawl_single('dementia-diagnosis'))
    
    # Extract
    meta_file = Path("data/dr_opa_agent/raw/cep/dementia-diagnosis_meta.json")
    with open(meta_file) as f:
        tool_info = json.load(f)
    
    extracted = extract_cep_tool(str(html_file), tool_info)
    
    # Save extraction
    extractor = CEPExtractor()
    extractor.save_extracted_data(extracted)
    
    # Ingest
    ingester = CEPIngester()
    stats = ingester.ingest_tool('dementia-diagnosis')
    
    print("\nIngestion Statistics:")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()