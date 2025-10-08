"""Improved CEP clinical tools ingester with parent/child chunking.

Fixes 0% recall issue by creating properly-sized chunks with full content.
"""

import os
import sys
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


class CEPIngesterV2:
    """Improved CEP ingester with proper parent/child chunking.

    Changes from V1:
    - Extracts FULL section content, not just summaries
    - Creates parent chunks of 400-800 words
    - Creates child chunks of 150-300 words
    - Preserves tool names, descriptions, and usage instructions together
    - Enriches metadata for better retrieval
    """

    # Override chunking parameters for CEP tools
    PARENT_MIN_WORDS = 400
    PARENT_MAX_WORDS = 800
    CHILD_MIN_WORDS = 150
    CHILD_MAX_WORDS = 300

    # Boilerplate sections to skip during extraction
    BOILERPLATE_SECTIONS = [
        'references', 'referencesnew',
        'acknowledgment', 'acknowledgement', 'acknowledgments',
        'legal', 'permission to use', 'permission', 'disclaimer'
    ]

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """Initialize improved CEP ingester (ChromaDB only, no SQL)."""
        # Load API key from environment if not provided
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

        self.source_org = 'cep'
        self.raw_dir = Path("data/dr_opa_agent/raw/cep")

        # Set up Chroma
        if chroma_path is None:
            chroma_path = "data/dr_opa_agent/chroma"
        Path(chroma_path).mkdir(parents=True, exist_ok=True)

        # Use consistent settings to avoid conflicts
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False,
                is_persistent=True
            )
        )

        # Create or get collection for OPA corpus
        collection_name = "opa_cep_corpus"
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Using existing Chroma collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"source": "dr_opa", "organization": "cep"}
            )
            logger.info(f"Created new Chroma collection: {collection_name}")

        # Set up OpenAI client for embeddings
        self.openai_client = openai_module.OpenAI(api_key=openai_api_key)
        self.EMBEDDING_MODEL = "text-embedding-3-small"
        self.EMBEDDING_BATCH_SIZE = 100

    def fetch_document(self, url: str) -> tuple[str, str]:
        """Fetch document from URL (required by base class).

        Not used in V2 - we work directly with HTML files.
        """
        return "", "html"

    def ingest_tool_from_html(self, tool_slug: str) -> Dict[str, Any]:
        """Ingest a CEP tool directly from HTML with improved chunking.

        Args:
            tool_slug: Tool slug (e.g., 'dementia-diagnosis')

        Returns:
            Ingestion statistics
        """
        try:
            logger.info(f"Ingesting CEP tool: {tool_slug}")

            # Load HTML and metadata
            html_file = self.raw_dir / f"{tool_slug}.html"
            meta_file = self.raw_dir / f"{tool_slug}_meta.json"

            if not html_file.exists():
                raise FileNotFoundError(f"HTML file not found: {html_file}")

            with open(html_file) as f:
                html = f.read()

            with open(meta_file) as f:
                tool_info = json.load(f)

            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')

            # Extract metadata
            metadata = self._extract_tool_metadata(soup, tool_info, html_file)

            # Generate document ID (no SQL storage)
            doc_id = hashlib.sha256(metadata['source_url'].encode()).hexdigest()[:16]

            # Extract full content organized by sections
            sections = self._extract_full_sections(soup, tool_info)

            # Create parent/child chunks from sections
            chunks = self._create_chunks_from_sections(sections, metadata, tool_info)

            # Store chunks with embeddings (ChromaDB only)
            stored_count = self._store_chunks_chroma_only(chunks)

            stats = {
                'tool_slug': tool_slug,
                'document_id': doc_id,
                'title': metadata['title'],
                'chunks_created': len(chunks),
                'chunks_stored': stored_count,
                'sections_extracted': len(sections),
                'ingested_at': datetime.now().isoformat()
            }

            logger.info(f"✓ Ingested {tool_slug}: {stored_count} chunks stored")

            return stats

        except Exception as e:
            logger.error(f"Error ingesting tool {tool_slug}: {e}")
            raise

    def _extract_tool_metadata(
        self,
        soup: BeautifulSoup,
        tool_info: Dict[str, str],
        html_file: Path
    ) -> Dict[str, Any]:
        """Extract tool metadata from HTML."""
        # Get tool slug from filename
        tool_slug = html_file.stem

        # Find title
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else tool_info.get('name', 'Unknown Tool')

        # Find last updated date
        last_updated = None
        date_patterns = [
            r'Last [Uu]pdated?:?\s*([^<\n]+)',
            r'Updated:?\s*([^<\n]+)',
            r'Version date:?\s*([^<\n]+)'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, str(soup), re.IGNORECASE)
            if match:
                last_updated = match.group(1).strip()
                break

        # Extract keywords from content
        text_content = soup.get_text().lower()
        topics = []

        # Common medical topics
        topic_keywords = {
            'mental_health': ['mental health', 'depression', 'anxiety', 'dementia', 'adhd'],
            'cardiovascular': ['cardio', 'heart', 'hypertension', 'blood pressure'],
            'respiratory': ['copd', 'asthma', 'respiratory'],
            'pain_management': ['pain', 'chronic pain', 'fibromyalgia'],
            'substance_use': ['alcohol', 'substance', 'addiction', 'opioid'],
            'infectious_disease': ['covid', 'hiv', 'infection'],
            'screening': ['screening', 'prevention', 'early detection'],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text_content for kw in keywords):
                topics.append(topic)

        # Add tool category from metadata
        if tool_info.get('category'):
            topics.insert(0, tool_info['category'])

        metadata = {
            'source_url': f"https://tools.cep.health/tool/{tool_slug}/",
            'source_org': 'cep',
            'title': title or 'Unknown',
            'document_type': 'clinical_tool',
            'effective_date': last_updated or 'Unknown',
            'topics': ','.join(topics) if topics else 'general',
            'content_hash': hashlib.sha256(str(soup).encode()).hexdigest(),
            'ingested_at': datetime.now().isoformat()
        }

        return metadata

    def _should_skip_section(self, heading: str) -> bool:
        """Check if section is boilerplate and should be skipped.

        Args:
            heading: Section heading text

        Returns:
            True if section should be skipped
        """
        heading_lower = heading.lower()
        is_boilerplate = any(kw in heading_lower for kw in self.BOILERPLATE_SECTIONS)

        if is_boilerplate:
            logger.debug(f"Skipping boilerplate section: {heading}")

        return is_boilerplate

    def _extract_full_sections(
        self,
        soup: BeautifulSoup,
        tool_info: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Extract full section content from HTML.

        Returns sections with FULL content, not just summaries.
        CEP tools use Gravity Forms with gfield divs, so we need special handling.
        """
        sections = []

        # Find main content area
        main_content = soup.find('main') or soup.find('div', {'class': 'content'}) or soup.find('body')

        if not main_content:
            logger.warning("No main content found, using full body")
            main_content = soup

        # Track current section and subsection context
        current_section = None
        current_subsection = None

        # Process all elements to build section structure
        for element in main_content.descendants:
            if not hasattr(element, 'name') or not element.name:
                continue

            # H2 = Main section
            if element.name == 'h2':
                # Save previous section
                if current_section and current_section.get('content_parts'):
                    current_section['content'] = '\n\n'.join(current_section['content_parts'])
                    sections.append(current_section)

                # Start new section
                heading_text = element.get_text(strip=True)

                # Skip boilerplate sections
                if self._should_skip_section(heading_text):
                    current_section = None  # Don't track this section
                    continue

                section_id = element.get('id', '')

                current_section = {
                    'heading': heading_text,
                    'level': 2,
                    'anchor': f"#{section_id}" if section_id else '',
                    'content_parts': [],
                    'subsections': []
                }
                current_subsection = None

            # H3 = Subsection (keep in same section but note hierarchy)
            elif element.name == 'h3' and current_section:
                subsection_heading = element.get_text(strip=True)
                # Add subsection marker to content
                current_section['content_parts'].append(f"## {subsection_heading}")
                current_subsection = subsection_heading
                current_section['subsections'].append(subsection_heading)

            # H4 = Sub-subsection (drug names, detailed topics)
            elif element.name == 'h4' and current_section:
                subsubsection_heading = element.get_text(strip=True)
                # Add as inline heading in content
                current_section['content_parts'].append(f"### {subsubsection_heading}")

            # Extract content from multiple sources
            elif current_section is not None:
                text = None

                # 1. Paragraphs, list items, table cells (original)
                if element.name in ['p', 'li', 'td', 'th']:
                    text = element.get_text(strip=True)

                # 2. Span tags with substantial content
                elif element.name == 'span':
                    # Only get direct text, not nested
                    direct_text = ''.join([t for t in element.stripped_strings])
                    if len(direct_text) > 20:
                        text = direct_text

                # 3. Div tags with gfield_html class (Gravity Forms HTML blocks)
                elif element.name == 'div':
                    classes = ' '.join(element.get('class', []))
                    if 'gfield_html' in classes:
                        # Get all text from this gfield block
                        text = element.get_text(strip=True)

                # 4. Blockquotes, notes, warnings
                elif element.name in ['blockquote', 'aside']:
                    text = element.get_text(strip=True)

                # Add text if substantial
                if text and len(text) > 20:
                    # Deduplicate - don't add if already added
                    if not current_section['content_parts'] or text != current_section['content_parts'][-1]:
                        current_section['content_parts'].append(text)

        # Don't forget last section
        if current_section and current_section.get('content_parts'):
            current_section['content'] = '\n\n'.join(current_section['content_parts'])
            sections.append(current_section)

        # If no sections found, fallback: extract from gfield HTML blocks directly
        if not sections or len(sections) < 2:
            logger.warning("Few/no sections found via headings, trying gfield extraction...")
            sections = self._extract_from_gfields(soup)

        logger.info(f"Extracted {len(sections)} sections")

        return sections

    def _extract_from_gfields(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Fallback: Extract content from Gravity Forms gfield blocks.

        CEP tools are built with Gravity Forms, content is in gfield divs.
        """
        sections = []

        # Find all HTML content gfields
        gfields = soup.find_all('div', class_=lambda x: x and 'gfield_html' in str(x))

        logger.info(f"Found {len(gfields)} gfield HTML blocks")

        for i, gfield in enumerate(gfields):
            text = gfield.get_text(separator='\n', strip=True)

            if len(text) > 50:  # Skip trivial content
                # Try to find a heading near this gfield
                heading = None
                prev = gfield.find_previous(['h2', 'h3', 'h4'])
                if prev:
                    heading = prev.get_text(strip=True)
                else:
                    heading = f"Section {i+1}"

                sections.append({
                    'heading': heading,
                    'level': 2,
                    'anchor': f"#gfield_{i}",
                    'content': text
                })

        # If still no content, extract all text
        if not sections:
            full_text = soup.get_text(separator='\n\n', strip=True)
            sections = [{
                'heading': 'Full Tool Content',
                'level': 1,
                'anchor': '',
                'content': full_text
            }]

        return sections

    def _create_chunks_from_sections(
        self,
        sections: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        tool_info: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Create parent/child chunks from sections.

        Parent chunks: 400-800 words (section-level)
        Child chunks: 150-300 words (subsection-level)
        """
        chunks = []
        tool_slug = tool_info.get('slug', 'unknown')

        # Create overview parent chunk
        overview_parts = [
            f"# {metadata['title']}",
            f"Clinical Tool from: Centre for Effective Practice",
            f"Category: {tool_info.get('category', 'general').replace('_', ' ').title()}",
        ]

        if metadata.get('effective_date'):
            overview_parts.append(f"Last Updated: {metadata['effective_date']}")

        # Add section overview
        if sections:
            overview_parts.append(f"\n## Tool Sections ({len(sections)}):")
            for sec in sections[:10]:
                overview_parts.append(f"- {sec['heading']}")

        overview_text = '\n'.join(overview_parts)
        overview_id = f"cep_{tool_slug}_overview"

        overview_chunk = {
            'chunk_id': overview_id,
            'text': overview_text,
            'chunk_type': 'parent',
            'section_heading': f"{metadata['title']} - Overview",
            'section_idx': 0,
            'chunk_idx': 0,
            'metadata': {
                **metadata,
                'chunk_type': 'parent',
                'section_title': 'Overview',
                'section_path': f"{metadata['title']} > Overview",
                'is_overview': True
            }
        }
        chunks.append(overview_chunk)

        # Create chunks for each section
        for sec_idx, section in enumerate(sections):
            section_content = section.get('content', '')

            if not section_content:
                continue

            # Count words in section
            word_count = len(section_content.split())

            # If section is small enough, create one parent chunk
            if word_count <= self.PARENT_MAX_WORDS:
                parent_text = f"## {section['heading']}\n\n{section_content}"
                parent_id = f"cep_{tool_slug}_sec_{sec_idx}"

                parent_chunk = {
                    'chunk_id': parent_id,
                    'text': parent_text,
                    'chunk_type': 'parent',
                    'section_heading': section['heading'],
                    'section_idx': sec_idx + 1,
                    'chunk_idx': 0,
                    'metadata': {
                        **metadata,
                        'chunk_type': 'parent',
                        'section_title': section['heading'],
                        'section_path': f"{metadata['title']} > {section['heading']}",
                        'section_level': section['level']
                    }
                }
                chunks.append(parent_chunk)

            else:
                # Section is large - create parent + children
                # Parent: first PARENT_MAX_WORDS
                words = section_content.split()
                parent_words = words[:self.PARENT_MAX_WORDS]
                parent_text = f"## {section['heading']}\n\n{' '.join(parent_words)}"
                parent_id = f"cep_{tool_slug}_sec_{sec_idx}"

                parent_chunk = {
                    'chunk_id': parent_id,
                    'text': parent_text,
                    'chunk_type': 'parent',
                    'section_heading': section['heading'],
                    'section_idx': sec_idx + 1,
                    'chunk_idx': 0,
                    'metadata': {
                        **metadata,
                        'chunk_type': 'parent',
                        'parent_id': parent_id,
                        'section_title': section['heading'],
                        'section_path': f"{metadata['title']} > {section['heading']}",
                        'section_level': section['level']
                    }
                }
                chunks.append(parent_chunk)

                # Children: subdivide remaining content
                remaining_words = words[self.PARENT_MAX_WORDS:]
                child_idx = 0

                while remaining_words:
                    child_words = remaining_words[:self.CHILD_MAX_WORDS]
                    child_text = ' '.join(child_words)
                    child_id = f"cep_{tool_slug}_sec_{sec_idx}_child_{child_idx}"

                    child_chunk = {
                        'chunk_id': child_id,
                        'parent_id': parent_id,
                        'text': child_text,
                        'chunk_type': 'child',
                        'section_heading': section['heading'],
                        'section_idx': sec_idx + 1,
                        'chunk_idx': child_idx + 1,
                        'metadata': {
                            **metadata,
                            'chunk_type': 'child',
                            'parent_id': parent_id,
                            'section_title': section['heading'],
                            'section_path': f"{metadata['title']} > {section['heading']}",
                            'section_level': section['level'],
                            'child_index': child_idx
                        }
                    }
                    chunks.append(child_chunk)

                    remaining_words = remaining_words[self.CHILD_MAX_WORDS:]
                    child_idx += 1

        logger.info(f"Created {len(chunks)} chunks ({sum(1 for c in chunks if c['chunk_type']=='parent')} parents, {sum(1 for c in chunks if c['chunk_type']=='child')} children)")

        return chunks

    def _store_chunks_chroma_only(self, chunks: List[Dict[str, Any]]) -> int:
        """Store chunks in ChromaDB only (no SQL database).

        Args:
            chunks: List of chunk dictionaries with text and metadata

        Returns:
            Number of chunks successfully stored
        """
        if not chunks:
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

        # Store in ChromaDB
        stored_count = 0
        for chunk, embedding in zip(chunks, embeddings):
            try:
                self.collection.add(
                    ids=[chunk['chunk_id']],
                    embeddings=[embedding],
                    documents=[chunk['text']],
                    metadatas=[chunk['metadata']]
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing chunk {chunk['chunk_id']}: {e}")

        logger.info(f"Successfully stored {stored_count}/{len(chunks)} chunks in ChromaDB")
        return stored_count

    def ingest_all_tools(self) -> Dict[str, Any]:
        """Ingest all CEP tools with improved chunking.

        Returns:
            Summary statistics
        """
        # Find all HTML files
        html_files = list(self.raw_dir.glob("*.html"))

        if not html_files:
            logger.warning("No HTML files found in raw directory")
            return {}

        logger.info(f"Found {len(html_files)} tools to ingest")

        results = []
        failed = []

        for html_file in html_files:
            tool_slug = html_file.stem

            try:
                stats = self.ingest_tool_from_html(tool_slug)
                results.append(stats)
                logger.info(f"✓ {tool_slug}: {stats['chunks_stored']} chunks")
            except Exception as e:
                logger.error(f"✗ {tool_slug}: {e}")
                failed.append({'tool': tool_slug, 'error': str(e)})

        # Summary
        summary = {
            'total_tools': len(html_files),
            'successfully_ingested': len(results),
            'failed': len(failed),
            'total_chunks': sum(r['chunks_stored'] for r in results),
            'failed_tools': failed,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"\n=== Ingestion Summary ===")
        logger.info(f"Total tools: {summary['total_tools']}")
        logger.info(f"Successfully ingested: {summary['successfully_ingested']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Total chunks stored: {summary['total_chunks']}")

        return summary


def main():
    """Re-ingest all CEP tools with improved chunking."""
    ingester = CEPIngesterV2()
    summary = ingester.ingest_all_tools()

    print("\nIngestion Complete!")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
