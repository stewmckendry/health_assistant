#!/usr/bin/env python3
"""CPSO document ingestion script.

This script:
1. Extracts CPSO documents using the CPSO extractor
2. Chunks the content using parent-child strategy
3. Generates embeddings
4. Stores in SQLite and Chroma databases
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse

from ..base_ingester import BaseOPAIngester
from .extractor import CPSOExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CPSOIngester(BaseOPAIngester):
    """Ingester for CPSO documents."""
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize CPSO ingester.
        
        Args:
            db_path: Path to SQLite database
            chroma_path: Path to Chroma vector store
            openai_api_key: OpenAI API key for embeddings
        """
        super().__init__(
            source_org='cpso',
            db_path=db_path or "data/processed/dr_opa/opa.db",
            chroma_path=chroma_path or "data/processed/dr_opa/chroma",
            openai_api_key=openai_api_key
        )
        
        self.extractor = CPSOExtractor(use_llm=False)
    
    def fetch_document(self, url: str) -> tuple[str, str]:
        """Fetch and normalize CPSO document.
        
        Args:
            url: Document URL
            
        Returns:
            Tuple of (normalized_text, document_format)
        """
        # Extract document
        document = extract_cpso_document(url, use_llm=False)
        
        # Return content and format
        return document.get('content', ''), 'html'
    
    def ingest_document(self, url: str) -> Dict[str, Any]:
        """Ingest a single CPSO document.
        
        Args:
            url: CPSO document URL
            
        Returns:
            Ingestion statistics
        """
        try:
            logger.info(f"Ingesting CPSO document: {url}")
            
            # Extract document
            document = extract_cpso_document(url, use_llm=False)
            
            # Prepare metadata
            metadata = {
                'source_url': url,
                'source_org': 'cpso',
                'title': document.get('title', 'Untitled'),
                'document_type': document.get('document_type', 'guidance'),
                'policy_level': document.get('policy_level'),
                'content_hash': document.get('content_hash', ''),
                'ingested_at': datetime.now().isoformat()
            }
            
            # Add dates from metadata if available
            if document.get('metadata'):
                doc_meta = document['metadata']
                if 'approval_date' in doc_meta:
                    metadata['published_date'] = doc_meta['approval_date']
                if 'review_date' in doc_meta:
                    metadata['updated_date'] = doc_meta['review_date']
            
            # Extract topics from content
            metadata['topics'] = self._extract_topics(
                document.get('content', ''),
                url
            )
            
            # Store document record
            doc_id = self._store_document(metadata)
            
            # Create parent-child chunks from sections
            all_chunks = []
            
            sections = document.get('sections', [])
            if sections:
                # Process structured sections
                for section_idx, section in enumerate(sections):
                    # Create parent chunk for section
                    parent_id = self._generate_chunk_id(
                        section['heading'],
                        f"parent_{section_idx}"
                    )
                    
                    # Add control tokens
                    control_tokens = self.CONTROL_TOKEN_TEMPLATE.format(
                        org='cpso',
                        topic=','.join(metadata.get('topics', [])),
                        date=metadata.get('published_date', 'unknown'),
                        doc_type=metadata.get('document_type', 'guidance')
                    )
                    
                    parent_text = f"{control_tokens}\n\n## {section['heading']}\n\n{section['content']}"
                    
                    parent_chunk = {
                        'chunk_id': parent_id,
                        'text': parent_text[:self.PARENT_CHUNK_SIZE * 4],
                        'chunk_type': 'parent',
                        'section_idx': section_idx,
                        'section_heading': section['heading'],
                        'metadata': {**metadata, 'chunk_type': 'parent'}
                    }
                    all_chunks.append(parent_chunk)
                    
                    # Create child chunks from section content
                    if section['content']:
                        children = self._create_child_chunks(
                            section['content'],
                            parent_id,
                            section_idx,
                            section['heading'],
                            metadata
                        )
                        all_chunks.extend(children)
                    
                    # Process subsections
                    for subsection in section.get('subsections', []):
                        if subsection['content']:
                            children = self._create_child_chunks(
                                subsection['content'],
                                parent_id,
                                section_idx,
                                subsection['heading'],
                                metadata
                            )
                            all_chunks.extend(children)
            else:
                # Fallback: chunk the entire content
                logger.warning("No sections found, chunking entire content")
                parent_chunks, child_chunks = self.create_parent_child_chunks(
                    document.get('content', ''),
                    metadata
                )
                all_chunks.extend(parent_chunks)
                all_chunks.extend(child_chunks)
            
            # Generate embeddings and store
            if all_chunks:
                self.store_chunks_with_embeddings(all_chunks, doc_id)
            
            # Check for superseded documents
            if metadata.get('topics'):
                for topic in metadata['topics']:
                    self.check_and_mark_superseded(
                        topic,
                        metadata.get('published_date'),
                        doc_id
                    )
            
            # Save processed files
            self._save_processed_files(url, document, metadata, all_chunks)
            
            return {
                'success': True,
                'document_id': doc_id,
                'chunks_created': len(all_chunks),
                'title': metadata['title']
            }
            
        except Exception as e:
            logger.error(f"Error ingesting {url}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_processed_files(
        self,
        url: str,
        document: Dict[str, Any],
        metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ):
        """Save processed files for inspection."""
        # Create directories
        processed_dir = Path("data/dr_opa_agent/processed/cpso")
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from title
        title = metadata.get('title', 'untitled')
        filename_base = title.lower().replace(' ', '_')
        filename_base = ''.join(c for c in filename_base if c.isalnum() or c == '_')[:50]
        
        # Save extracted document
        doc_file = processed_dir / f"{filename_base}.json"
        with open(doc_file, 'w', encoding='utf-8') as f:
            json.dump(document, f, indent=2)
        logger.info(f"Saved extracted document: {doc_file}")
        
        # Save metadata
        meta_file = processed_dir / f"{filename_base}_metadata.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Save chunks for inspection
        chunks_file = processed_dir / f"{filename_base}_chunks.json"
        chunks_data = []
        for chunk in chunks:
            chunks_data.append({
                'chunk_id': chunk['chunk_id'],
                'chunk_type': chunk['chunk_type'],
                'section_heading': chunk.get('section_heading'),
                'text_preview': chunk['text'][:200] + '...' if len(chunk['text']) > 200 else chunk['text'],
                'text_length': len(chunk['text'])
            })
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2)
        logger.info(f"Saved {len(chunks)} chunks: {chunks_file}")


def ingest_cpso_documents(urls: List[str], openai_api_key: Optional[str] = None):
    """Ingest multiple CPSO documents.
    
    Args:
        urls: List of CPSO document URLs
        openai_api_key: Optional OpenAI API key for embeddings
        
    Returns:
        Ingestion statistics
    """
    # Get API key from environment if not provided
    if not openai_api_key:
        openai_api_key = os.getenv('OPENAI_API_KEY')
    
    ingester = CPSOIngester(openai_api_key=openai_api_key)
    
    results = []
    for url in urls:
        result = ingester.ingest_document(url)
        results.append(result)
        
        if result['success']:
            logger.info(f"✓ Ingested: {result['title']} ({result['chunks_created']} chunks)")
        else:
            logger.error(f"✗ Failed: {url} - {result['error']}")
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total_chunks = sum(r.get('chunks_created', 0) for r in results)
    
    logger.info(f"\nIngestion Summary:")
    logger.info(f"  Documents: {successful}/{len(urls)} successful")
    logger.info(f"  Total chunks: {total_chunks}")
    
    return results


def main():
    """Main entry point for CPSO ingestion."""
    parser = argparse.ArgumentParser(description='Ingest CPSO documents')
    parser.add_argument(
        'urls',
        nargs='*',
        help='CPSO document URLs to ingest'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run test ingestion with example documents'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key for embeddings'
    )
    
    args = parser.parse_args()
    
    if args.test:
        # Test with example documents
        test_urls = [
            "https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies/Availability-and-Coverage",
            "https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies/Advertising/Advice-to-the-Profession-Advertising",
            "https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Statements-Positions/Interprofessional-Collaboration"
        ]
        results = ingest_cpso_documents(test_urls, args.api_key)
    elif args.urls:
        results = ingest_cpso_documents(args.urls, args.api_key)
    else:
        parser.print_help()
        return
    
    # Print final results
    print("\nFinal Results:")
    for i, result in enumerate(results, 1):
        if result['success']:
            print(f"  {i}. ✓ {result['title']}: {result['chunks_created']} chunks")
        else:
            print(f"  {i}. ✗ Error: {result['error']}")


if __name__ == "__main__":
    main()