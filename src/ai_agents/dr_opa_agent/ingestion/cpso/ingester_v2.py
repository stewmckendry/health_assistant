"""Improved CPSO ingester with proper parent/child chunking and metadata enrichment.

Fixes:
- Adds section_path metadata (hierarchical breadcrumbs)
- Adds effective_date extraction
- Adds topics extraction
- Enforces parent chunk size limits (400-800 words)
- Creates children for overflow content
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CPSOIngesterV2:
    """Improved CPSO ingester with rich metadata and proper chunking."""

    # Override chunking parameters
    PARENT_MIN_WORDS = 400
    PARENT_MAX_WORDS = 800
    CHILD_MIN_WORDS = 150
    CHILD_MAX_WORDS = 300

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize improved CPSO ingester (ChromaDB only, no SQL)."""
        if not openai_api_key:
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                from dotenv import load_dotenv
                load_dotenv()
                openai_api_key = os.getenv('OPENAI_API_KEY')

        # Initialize without SQL database
        import chromadb
        from chromadb.config import Settings
        import openai as openai_module

        self.source_org = 'cpso'
        self.processed_dir = Path("data/dr_opa_agent/processed/cpso")

        # Set up Chroma
        if chroma_path is None:
            chroma_path = "data/dr_opa_agent/chroma"
        Path(chroma_path).mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Create or get collection for OPA corpus
        collection_name = "opa_cpso_corpus"
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Using existing Chroma collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"source": "dr_opa", "organization": "cpso"}
            )
            logger.info(f"Created new Chroma collection: {collection_name}")

        # Set up OpenAI client for embeddings
        self.openai_client = openai_module.OpenAI(api_key=openai_api_key)
        self.EMBEDDING_MODEL = "text-embedding-3-small"
        self.EMBEDDING_BATCH_SIZE = 100

    def fetch_document(self, url: str) -> tuple[str, str]:
        """Fetch document from URL (required by base class)."""
        return "", "html"

    def ingest_from_processed_json(self, json_file: Path) -> Dict[str, Any]:
        """Ingest a CPSO policy from processed JSON.

        Args:
            json_file: Path to processed JSON file

        Returns:
            Ingestion statistics
        """
        try:
            logger.info(f"Ingesting CPSO policy: {json_file.stem}")

            with open(json_file) as f:
                data = json.load(f)

            # Extract enhanced metadata
            metadata = self._extract_enhanced_metadata(data)

            # Generate simple document ID (no database storage)
            doc_id = hashlib.sha256(metadata['source_url'].encode()).hexdigest()[:16]

            # Create chunks from sections
            chunks = self._create_chunks_from_sections(data, metadata)

            # Store chunks directly in ChromaDB (skip SQLite)
            stored_count = self._store_chunks_chroma_only(chunks)

            stats = {
                'file': json_file.name,
                'document_id': doc_id,
                'title': metadata['title'],
                'chunks_created': len(chunks),
                'chunks_stored': stored_count,
                'sections': len(data.get('sections', [])),
                'ingested_at': datetime.now().isoformat()
            }

            logger.info(f"✓ Ingested {json_file.stem}: {stored_count} chunks stored")

            return stats

        except Exception as e:
            logger.error(f"Error ingesting {json_file.stem}: {e}")
            raise

    def _extract_enhanced_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract enhanced metadata from processed JSON."""
        title = data.get('title', 'Unknown Policy')
        doc_type = data.get('document_type', 'policy')
        content = data.get('content', '')

        # Extract effective date from content
        effective_date = None
        date_patterns = [
            r'Effective:\s*([A-Z][a-z]+ \d{1,2}, \d{4})',
            r'Effective Date:\s*([A-Z][a-z]+ \d{4})',
            r'Last Updated:\s*([A-Z][a-z]+ \d{4})',
            r'Updated:\s*([A-Z][a-z]+ \d{4})'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                effective_date = match.group(1)
                break

        # Extract topics from title and content
        topics = self._extract_topics(title, content)

        # Determine policy level
        policy_level = self._determine_policy_level(title, doc_type)

        metadata = {
            'source_url': data.get('source_url', ''),
            'source_org': 'cpso',
            'title': title,
            'document_type': doc_type,
            'effective_date': effective_date,
            'topics': topics,
            'policy_level': policy_level,
            'content_hash': data.get('content_hash', hashlib.sha256(content.encode()).hexdigest()),
            'ingested_at': datetime.now().isoformat()
        }

        return metadata

    def _extract_topics(self, title: str, content: str) -> List[str]:
        """Extract topics from title and content."""
        topics = []

        text = (title + ' ' + content).lower()

        topic_keywords = {
            'virtual_care': ['virtual', 'telehealth', 'telemedicine'],
            'consent': ['consent', 'capacity', 'substitute decision'],
            'privacy': ['privacy', 'confidential', 'personal health information', 'phi'],
            'prescribing': ['prescrib', 'medication', 'drug', 'opioid'],
            'medical_records': ['medical record', 'documentation', 'chart'],
            'professional_misconduct': ['misconduct', 'boundary', 'sexual'],
            'continuity_of_care': ['continuity', 'transfer of care', 'referral'],
            'billing': ['billing', 'fee', 'uninsured service'],
            'delegation': ['delegation', 'controlled act'],
            'ending_relationship': ['ending', 'terminating', 'physician-patient relationship'],
            'social_media': ['social media', 'online', 'internet'],
            'advertising': ['advertising', 'marketing'],
            'medical_assistance_dying': ['maid', 'medical assistance in dying'],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)

        return topics

    def _determine_policy_level(self, title: str, doc_type: str) -> str:
        """Determine if this is policy, advice, or statement."""
        title_lower = title.lower()

        if 'advice to the profession' in title_lower:
            return 'advice'
        elif 'statement' in title_lower or 'position' in title_lower:
            return 'statement'
        elif doc_type == 'policy':
            return 'expectation'
        else:
            return 'general'

    def _create_chunks_from_sections(
        self,
        data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create parent/child chunks from sections with section_path."""
        chunks = []
        sections = data.get('sections', [])

        if not sections:
            # If no sections, chunk the full content
            content = data.get('content', '')
            if content:
                return self._chunk_full_content(content, metadata)
            return chunks

        # Build section hierarchy for section_path
        for sec_idx, section in enumerate(sections):
            section_heading = section.get('heading', f'Section {sec_idx + 1}')
            section_content = section.get('content', '')
            section_level = section.get('level', 2)

            if not section_content:
                continue

            # Build section_path (hierarchical breadcrumbs)
            section_path = f"{metadata['title']} > {section_heading}"

            # Count words
            words = section_content.split()
            word_count = len(words)

            # If section fits in parent size, create one parent
            if word_count <= self.PARENT_MAX_WORDS:
                parent_text = f"## {section_heading}\n\n{section_content}"
                # Use document title + section heading + index for unique ID
                unique_key = f"{metadata['title']}_{section_heading}_{sec_idx}"
                parent_id = f"cpso_{hashlib.md5(unique_key.encode()).hexdigest()[:12]}"

                parent_chunk = {
                    'chunk_id': parent_id,
                    'text': parent_text,
                    'chunk_type': 'parent',
                    'section_heading': section_heading,
                    'section_idx': sec_idx,
                    'chunk_idx': 0,
                    'metadata': {
                        **metadata,
                        'chunk_type': 'parent',
                        'section_title': section_heading,
                        'section_path': section_path,
                        'section_level': section_level
                    }
                }
                chunks.append(parent_chunk)

            else:
                # Section too large - create parent + children
                parent_words = words[:self.PARENT_MAX_WORDS]
                parent_text = f"## {section_heading}\n\n{' '.join(parent_words)}"
                unique_key = f"{metadata['title']}_{section_heading}_{sec_idx}"
                parent_id = f"cpso_{hashlib.md5(unique_key.encode()).hexdigest()[:12]}"

                parent_chunk = {
                    'chunk_id': parent_id,
                    'text': parent_text,
                    'chunk_type': 'parent',
                    'section_heading': section_heading,
                    'section_idx': sec_idx,
                    'chunk_idx': 0,
                    'metadata': {
                        **metadata,
                        'chunk_type': 'parent',
                        'parent_id': parent_id,
                        'section_title': section_heading,
                        'section_path': section_path,
                        'section_level': section_level
                    }
                }
                chunks.append(parent_chunk)

                # Create children for remaining content
                remaining_words = words[self.PARENT_MAX_WORDS:]
                child_idx = 0

                while remaining_words:
                    child_words = remaining_words[:self.CHILD_MAX_WORDS]
                    child_text = ' '.join(child_words)
                    unique_child_key = f"{metadata['title']}_{section_heading}_{sec_idx}_child_{child_idx}"
                    child_id = f"cpso_{hashlib.md5(unique_child_key.encode()).hexdigest()[:12]}"

                    child_chunk = {
                        'chunk_id': child_id,
                        'parent_id': parent_id,
                        'text': child_text,
                        'chunk_type': 'child',
                        'section_heading': section_heading,
                        'section_idx': sec_idx,
                        'chunk_idx': child_idx + 1,
                        'metadata': {
                            **metadata,
                            'chunk_type': 'child',
                            'parent_id': parent_id,
                            'section_title': section_heading,
                            'section_path': section_path,
                            'section_level': section_level,
                            'child_index': child_idx
                        }
                    }
                    chunks.append(child_chunk)

                    remaining_words = remaining_words[self.CHILD_MAX_WORDS:]
                    child_idx += 1

            # Process subsections if present
            subsections = section.get('subsections', [])
            for sub_idx, subsection in enumerate(subsections):
                sub_heading = subsection.get('heading', f'Subsection {sub_idx + 1}')
                sub_content = subsection.get('content', '')

                if not sub_content:
                    continue

                # Build hierarchical path for subsection
                subsection_path = f"{section_path} > {sub_heading}"

                sub_words = sub_content.split()
                sub_word_count = len(sub_words)

                if sub_word_count <= self.CHILD_MAX_WORDS:
                    # Subsection as child chunk
                    unique_sub_key = f"{metadata['title']}_{section_heading}_{sub_heading}_{sec_idx}_sub_{sub_idx}"
                    sub_id = f"cpso_{hashlib.md5(unique_sub_key.encode()).hexdigest()[:12]}"

                    sub_chunk = {
                        'chunk_id': sub_id,
                        'parent_id': parent_id,
                        'text': f"### {sub_heading}\n\n{sub_content}",
                        'chunk_type': 'child',
                        'section_heading': sub_heading,
                        'section_idx': sec_idx,
                        'chunk_idx': len([c for c in chunks if c.get('parent_id') == parent_id]) + 1,
                        'metadata': {
                            **metadata,
                            'chunk_type': 'child',
                            'parent_id': parent_id,
                            'section_title': sub_heading,
                            'section_path': subsection_path,
                            'section_level': section_level + 1
                        }
                    }
                    chunks.append(sub_chunk)

        logger.info(f"Created {len(chunks)} chunks ({sum(1 for c in chunks if c['chunk_type']=='parent')} parents, {sum(1 for c in chunks if c['chunk_type']=='child')} children)")

        return chunks

    def _chunk_full_content(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk full content when no sections available."""
        chunks = []
        words = content.split()

        # Create parent chunks of PARENT_MAX_WORDS
        chunk_idx = 0
        pos = 0

        while pos < len(words):
            chunk_words = words[pos:pos + self.PARENT_MAX_WORDS]
            chunk_text = ' '.join(chunk_words)
            unique_chunk_key = f"{metadata['title']}_chunk_{chunk_idx}"
            chunk_id = f"cpso_{hashlib.md5(unique_chunk_key.encode()).hexdigest()[:12]}"

            chunk = {
                'chunk_id': chunk_id,
                'text': chunk_text,
                'chunk_type': 'parent',
                'section_heading': metadata['title'],
                'section_idx': 0,
                'chunk_idx': chunk_idx,
                'metadata': {
                    **metadata,
                    'chunk_type': 'parent',
                    'section_title': 'Full Document',
                    'section_path': f"{metadata['title']} > Full Document"
                }
            }
            chunks.append(chunk)

            pos += self.PARENT_MAX_WORDS
            chunk_idx += 1

        return chunks

    def _store_chunks_chroma_only(self, chunks: List[Dict[str, Any]]) -> int:
        """Store chunks directly in ChromaDB without SQLite database.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Number of chunks successfully stored
        """
        if not chunks or not self.openai_client:
            return 0

        # Prepare texts for embedding
        texts = [chunk['text'] for chunk in chunks]

        # Generate embeddings with OpenAI
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = []

        try:
            for i in range(0, len(texts), self.EMBEDDING_BATCH_SIZE):
                batch = texts[i:i + self.EMBEDDING_BATCH_SIZE]
                response = self.openai_client.embeddings.create(
                    input=batch,
                    model=self.EMBEDDING_MODEL
                )
                batch_embeddings = [e.embedding for e in response.data]
                embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

        stored_count = 0
        for chunk, embedding in zip(chunks, embeddings):
            try:
                # Prepare metadata for ChromaDB (convert lists to strings)
                chroma_metadata = {}
                for key, value in chunk['metadata'].items():
                    if isinstance(value, list):
                        chroma_metadata[key] = ','.join(map(str, value))
                    elif value is None:
                        chroma_metadata[key] = ''
                    else:
                        chroma_metadata[key] = str(value)

                # Store in ChromaDB
                self.collection.add(
                    ids=[chunk['chunk_id']],
                    embeddings=[embedding],
                    documents=[chunk['text']],
                    metadatas=[chroma_metadata]
                )

                stored_count += 1

            except Exception as e:
                logger.error(f"Error storing chunk {chunk['chunk_id']}: {e}")

        logger.info(f"Successfully stored {stored_count}/{len(chunks)} chunks in ChromaDB")

        return stored_count

    def ingest_all_policies(self) -> Dict[str, Any]:
        """Ingest all CPSO policies from processed JSON files."""
        # Find all processed JSON files (not _chunks.json)
        json_files = [f for f in self.processed_dir.glob("*.json")
                      if not f.name.endswith('_chunks.json')]

        if not json_files:
            logger.warning("No processed JSON files found")
            return {}

        logger.info(f"Found {len(json_files)} CPSO policies to ingest")

        results = []
        failed = []

        for json_file in json_files:
            try:
                stats = self.ingest_from_processed_json(json_file)
                results.append(stats)
                logger.info(f"✓ {json_file.stem}: {stats['chunks_stored']} chunks")
            except Exception as e:
                logger.error(f"✗ {json_file.stem}: {e}")
                failed.append({'file': json_file.name, 'error': str(e)})

        # Summary
        summary = {
            'total_policies': len(json_files),
            'successfully_ingested': len(results),
            'failed': len(failed),
            'total_chunks': sum(r['chunks_stored'] for r in results),
            'failed_policies': failed,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"\n=== Ingestion Summary ===")
        logger.info(f"Total policies: {summary['total_policies']}")
        logger.info(f"Successfully ingested: {summary['successfully_ingested']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Total chunks stored: {summary['total_chunks']}")

        return summary


def main():
    """Re-ingest all CPSO policies with improved chunking."""
    ingester = CPSOIngesterV2()
    summary = ingester.ingest_all_policies()

    print("\nIngestion Complete!")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
