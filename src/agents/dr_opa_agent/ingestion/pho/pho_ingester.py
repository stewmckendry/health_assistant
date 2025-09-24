"""PHO document ingestion module for IPAC and clinical guidance.

This module handles ingestion of PHO (Public Health Ontario) documents,
particularly IPAC (Infection Prevention and Control) guidance for clinical offices.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from ..base_ingester import BaseOPAIngester
from .pho_extractor import PHOExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PHOIngester(BaseOPAIngester):
    """Ingester for PHO clinical guidance documents."""
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize PHO ingester.
        
        Args:
            db_path: Path to SQLite database
            chroma_path: Path to Chroma vector store
            openai_api_key: OpenAI API key for embeddings
        """
        # Initialize base class with PHO as source org
        super().__init__(
            source_org='pho',
            db_path=db_path or "data/processed/dr_opa/opa.db",
            chroma_path=chroma_path or "data/processed/dr_opa/chroma",
            openai_api_key=openai_api_key
        )
        
        self.extractor = PHOExtractor()
        
        # PHO-specific metadata defaults
        self.default_metadata = {
            'source_org': 'pho',
            'organization_full': 'Public Health Ontario',
            'jurisdiction': 'Ontario',
            'country': 'Canada'
        }
    
    def fetch_document(self, pdf_path: str) -> tuple[str, str]:
        """Fetch and extract PHO PDF document.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (normalized_text, document_format)
        """
        # Extract document using PHO extractor
        document = self.extractor.extract_document(Path(pdf_path))
        
        # Return content and format
        return document.get('content', ''), 'pdf'
    
    def ingest_document(self, pdf_path: str) -> Dict[str, Any]:
        """Ingest a single PHO document.
        
        Args:
            pdf_path: Path to PHO PDF document
            
        Returns:
            Ingestion statistics
        """
        try:
            logger.info(f"Ingesting PHO document: {pdf_path}")
            
            # Extract document
            document = self.extractor.extract_document(Path(pdf_path))
            
            # Prepare comprehensive metadata
            metadata = self._prepare_metadata(document, pdf_path)
            
            # Store document record in database
            doc_id = self._store_document(metadata)
            
            # Create parent-child chunks from sections
            all_chunks = self._create_document_chunks(document, metadata, doc_id)
            
            # Generate embeddings and store in vector database
            if all_chunks and self.openai_client:
                self.store_chunks_with_embeddings(all_chunks, doc_id)
                logger.info(f"Created {len(all_chunks)} chunks with embeddings")
            else:
                logger.warning("Skipping embeddings - no OpenAI client configured")
            
            # Save processed files for inspection
            self._save_processed_files(pdf_path, document, metadata, all_chunks)
            
            # Log success
            logger.info(f"✓ Successfully ingested: {metadata['title']}")
            logger.info(f"  - Document ID: {doc_id}")
            logger.info(f"  - Sections: {len(document.get('sections', []))}")
            logger.info(f"  - Chunks: {len(all_chunks)}")
            
            return {
                'success': True,
                'document_id': doc_id,
                'title': metadata['title'],
                'sections_created': len(document.get('sections', [])),
                'chunks_created': len(all_chunks),
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error ingesting {pdf_path}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'pdf_path': pdf_path
            }
    
    def _prepare_metadata(self, document: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        """Prepare comprehensive metadata for document storage.
        
        Args:
            document: Extracted document structure
            pdf_path: Path to source PDF
            
        Returns:
            Complete metadata dictionary
        """
        # Start with default PHO metadata
        metadata = self.default_metadata.copy()
        
        # Add document metadata
        doc_meta = document.get('metadata', {})
        
        metadata.update({
            'document_id': self._generate_document_id(pdf_path),
            'title': document.get('title', 'PHO Clinical Guidance'),
            'source_url': f"https://www.publichealthontario.ca/en/health-topics/infection-prevention-control/clinical-office-practice",
            'source_file': str(pdf_path),
            'document_type': doc_meta.get('document_type', 'ipac-guidance'),
            'topics': doc_meta.get('topics', ['ipac', 'clinical-office']),
            'published_date': doc_meta.get('published_date'),
            'revision_date': doc_meta.get('revision_date'),
            'effective_date': doc_meta.get('effective_date') or doc_meta.get('revision_date'),
            'version': doc_meta.get('version'),
            'page_count': doc_meta.get('page_count'),
            'content_hash': hashlib.sha256(
                document.get('content', '').encode()
            ).hexdigest(),
            'ingested_at': datetime.now().isoformat(),
            'is_superseded': False  # PHO documents typically update in place
        })
        
        # Special handling for IPAC documents
        if 'ipac' in metadata['document_type'] or 'infection' in metadata['title'].lower():
            metadata['practice_area'] = 'infection-control'
            metadata['clinical_setting'] = 'office-practice'
        
        return metadata
    
    def _create_document_chunks(
        self,
        document: Dict[str, Any],
        metadata: Dict[str, Any],
        doc_id: str
    ) -> List[Dict[str, Any]]:
        """Create parent-child chunks from document sections.
        
        Args:
            document: Extracted document
            metadata: Document metadata
            doc_id: Document ID
            
        Returns:
            List of chunk dictionaries
        """
        all_chunks = []
        
        # Get sections from document
        sections = document.get('sections', [])
        
        if not sections:
            logger.warning("No sections found, creating chunks from full content")
            # Fallback: chunk the entire content
            parent_chunks, child_chunks = self.create_parent_child_chunks(
                document.get('content', ''),
                metadata
            )
            all_chunks.extend(parent_chunks)
            all_chunks.extend(child_chunks)
            return all_chunks
        
        # Process each section
        for section_idx, section in enumerate(sections):
            # Create parent chunk for main section
            parent_id = self._generate_chunk_id(
                section['heading'],
                f"parent_{section_idx}"
            )
            
            # Add control tokens for better retrieval
            control_tokens = self.CONTROL_TOKEN_TEMPLATE.format(
                org='pho',
                topic=','.join(metadata.get('topics', [])),
                date=metadata.get('effective_date', 'unknown'),
                doc_type=metadata.get('document_type', 'guidance')
            )
            
            # Combine section content with subsections for parent
            full_section_text = section.get('full_content', section.get('content', ''))
            
            parent_text = f"{control_tokens}\n\n## {section['heading']}\n\n{full_section_text}"
            
            # Create parent chunk
            parent_chunk = {
                'chunk_id': parent_id,
                'document_id': doc_id,
                'text': parent_text[:self.PARENT_CHUNK_SIZE * 4],  # ~10000 chars
                'chunk_type': 'parent',
                'section_idx': section_idx,
                'section_heading': section['heading'],
                'metadata': {
                    **metadata,
                    'chunk_type': 'parent',
                    'section_idx': section_idx,
                    'section_heading': section['heading']
                }
            }
            all_chunks.append(parent_chunk)
            
            # Create child chunks from section content
            if full_section_text:
                children = self._create_child_chunks(
                    full_section_text,
                    parent_id,
                    section_idx,
                    section['heading'],
                    metadata
                )
                all_chunks.extend(children)
            
            # Process subsections as additional children
            for subsection in section.get('subsections', []):
                if subsection.get('content'):
                    subsection_children = self._create_child_chunks(
                        subsection['content'],
                        parent_id,
                        section_idx,
                        f"{section['heading']} - {subsection['heading']}",
                        metadata
                    )
                    all_chunks.extend(subsection_children)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(sections)} sections")
        return all_chunks
    
    def _create_child_chunks(
        self,
        content: str,
        parent_id: str,
        section_idx: int,
        section_heading: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create child chunks from content.
        
        Args:
            content: Text content to chunk
            parent_id: Parent chunk ID
            section_idx: Section index
            section_heading: Section heading
            metadata: Document metadata
            
        Returns:
            List of child chunk dictionaries
        """
        chunks = []
        
        # Split content into smaller chunks
        chunk_size = self.CHILD_CHUNK_SIZE * 4  # ~2000 chars
        overlap = self.CHUNK_OVERLAP * 4  # ~400 chars
        
        for i in range(0, len(content), chunk_size - overlap):
            chunk_text = content[i:i + chunk_size]
            
            # Skip very small chunks
            if len(chunk_text) < 100:
                continue
            
            chunk_id = self._generate_chunk_id(
                section_heading,
                f"child_{section_idx}_{i // chunk_size}"
            )
            
            chunk = {
                'chunk_id': chunk_id,
                'parent_id': parent_id,
                'document_id': metadata.get('document_id'),
                'text': chunk_text,
                'chunk_type': 'child',
                'section_idx': section_idx,
                'chunk_idx': i // chunk_size,
                'section_heading': section_heading,
                'metadata': {
                    **metadata,
                    'chunk_type': 'child',
                    'parent_id': parent_id,
                    'section_idx': section_idx,
                    'chunk_idx': i // chunk_size,
                    'section_heading': section_heading
                }
            }
            chunks.append(chunk)
        
        return chunks
    
    def _generate_document_id(self, pdf_path: str) -> str:
        """Generate unique document ID from path and content."""
        import uuid
        path_hash = hashlib.md5(str(pdf_path).encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:6]
        return f"pho_{timestamp}_{path_hash}_{unique_id}"
    
    def _generate_chunk_id(self, heading: str, suffix: str) -> str:
        """Generate unique chunk ID."""
        import uuid
        heading_hash = hashlib.md5(heading.encode()).hexdigest()[:6]
        unique_suffix = uuid.uuid4().hex[:8]
        return f"pho_chunk_{heading_hash}_{suffix}_{unique_suffix}"
    
    def _save_processed_files(
        self,
        pdf_path: str,
        document: Dict[str, Any],
        metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ):
        """Save processed files for inspection and debugging."""
        # Create output directory
        processed_dir = Path("data/dr_opa_agent/processed/pho")
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate base filename
        pdf_name = Path(pdf_path).stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"{pdf_name}_{timestamp}"
        
        # Save extracted document
        doc_file = processed_dir / f"{base_name}_extracted.json"
        with open(doc_file, 'w', encoding='utf-8') as f:
            # Save document without full content for readability
            doc_save = document.copy()
            if 'content' in doc_save and len(doc_save['content']) > 1000:
                doc_save['content'] = doc_save['content'][:1000] + "... [truncated]"
            json.dump(doc_save, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved extracted document: {doc_file}")
        
        # Save metadata
        meta_file = processed_dir / f"{base_name}_metadata.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved metadata: {meta_file}")
        
        # Save chunk summary
        chunks_file = processed_dir / f"{base_name}_chunks.json"
        chunk_summary = []
        for chunk in chunks[:50]:  # Save first 50 for inspection
            chunk_summary.append({
                'chunk_id': chunk['chunk_id'],
                'chunk_type': chunk['chunk_type'],
                'parent_id': chunk.get('parent_id'),
                'section_heading': chunk.get('section_heading'),
                'text_preview': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text'],
                'text_length': len(chunk['text'])
            })
        
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_chunks': len(chunks),
                'chunk_samples': chunk_summary
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved chunk summary: {chunks_file}")


def ingest_pho_document(pdf_path: str, openai_api_key: Optional[str] = None):
    """Convenience function to ingest a single PHO document.
    
    Args:
        pdf_path: Path to PHO PDF document
        openai_api_key: Optional OpenAI API key for embeddings
        
    Returns:
        Ingestion result dictionary
    """
    # Get API key from environment if not provided
    if not openai_api_key:
        openai_api_key = os.getenv('OPENAI_API_KEY')
    
    ingester = PHOIngester(openai_api_key=openai_api_key)
    return ingester.ingest_document(pdf_path)


def main():
    """Main entry point for PHO document ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest PHO clinical guidance documents')
    parser.add_argument(
        'pdf_path',
        nargs='?',
        default='data/dr_opa_agent/raw/pho/bp-clinical-office-practice.pdf',
        help='Path to PHO PDF document'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key for embeddings'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('/Users/liammckendry/health_assistant_dr_off_worktree/.env')
    
    # Ingest document
    result = ingest_pho_document(args.pdf_path, args.api_key)
    
    # Print results
    if result['success']:
        print("\n✅ Ingestion successful!")
        print(f"  Title: {result['title']}")
        print(f"  Document ID: {result['document_id']}")
        print(f"  Sections: {result['sections_created']}")
        print(f"  Chunks: {result['chunks_created']}")
        print(f"\nMetadata:")
        for key, value in result['metadata'].items():
            if key != 'content_hash':
                print(f"  {key}: {value}")
    else:
        print(f"\n❌ Ingestion failed: {result['error']}")


if __name__ == "__main__":
    main()