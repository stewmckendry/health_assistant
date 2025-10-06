"""
BM25 sparse retrieval client using Whoosh for exact term matching.
Complements dense vector search for hybrid retrieval.
"""
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser, OrGroup
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
import asyncio
import os

logger = logging.getLogger(__name__)


class BM25Client:
    """BM25 sparse retrieval using Whoosh for exact term matching."""

    def __init__(self, index_dir: str = None):
        """
        Initialize BM25 client with Whoosh index.

        Args:
            index_dir: Path to Whoosh index directory (default: data/dr_opa_agent/bm25_index)
        """
        if index_dir is None:
            # Default path based on environment (matches VectorClient structure)
            railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "").lower()
            if railway_env in ["true", "1", "yes", "on"]:
                index_dir = "/app/data/bm25_index"
            else:
                index_dir = "data/dr_opa_agent/bm25_index"

        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Define schema: what fields to index for BM25
        self.schema = Schema(
            doc_id=ID(stored=True, unique=True),
            text=TEXT(stored=True),  # Main content for BM25
            document_title=TEXT(stored=True),
            section_heading=TEXT(stored=True),
            source_org=STORED,
            document_type=STORED,
            chunk_type=STORED,
            effective_date=STORED,
            source_url=STORED,
            collection=STORED  # Which ChromaDB collection this came from
        )

        self.index = None
        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing index or create new one."""
        if exists_in(str(self.index_dir)):
            # Index exists, open it
            self.index = open_dir(str(self.index_dir))
            doc_count = self.index.doc_count_all()
            logger.info(f"Loaded BM25 index from {self.index_dir} ({doc_count} docs)")
        else:
            # Create new index
            self.index = create_in(str(self.index_dir), self.schema)
            logger.info(f"Created new BM25 index at {self.index_dir}")

    async def build_index_from_chroma(self, vector_client):
        """
        Build BM25 index from existing ChromaDB collections.

        Args:
            vector_client: VectorClient instance with loaded collections
        """
        writer = self.index.writer()

        # Get all collections from the vector client
        if not vector_client._collections:
            logger.warning("No collections loaded in vector client")
            writer.commit()
            return

        total_docs = 0
        for collection_name, collection in vector_client._collections.items():
            logger.info(f"Indexing {collection_name} for BM25...")

            # Retrieve all documents from ChromaDB (including their actual IDs)
            try:
                # Use a proper function to avoid lambda closure issues
                # Note: IDs are returned by default, don't include in 'include' parameter
                def get_collection_docs(coll=collection):
                    return coll.get(include=["documents", "metadatas"])

                results = await asyncio.get_event_loop().run_in_executor(
                    vector_client.executor,
                    get_collection_docs
                )
            except Exception as e:
                logger.error(f"Error retrieving documents from {collection_name}: {e}")
                continue

            if not results or not results.get("documents"):
                logger.warning(f"No documents found in {collection_name}")
                continue

            # Index each document using ChromaDB's actual document IDs
            document_ids = results.get("ids", [])
            documents = results["documents"]
            metadatas = results.get("metadatas", [])

            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}

                # Use ChromaDB's actual document ID (CRITICAL for RRF matching)
                doc_id = document_ids[i] if i < len(document_ids) else f"{collection_name}:{i}"

                writer.add_document(
                    doc_id=doc_id,
                    text=doc or "",
                    document_title=metadata.get("document_title", ""),
                    section_heading=metadata.get("section_heading", ""),
                    source_org=metadata.get("source_org", ""),
                    document_type=metadata.get("document_type", ""),
                    chunk_type=metadata.get("chunk_type", ""),
                    effective_date=metadata.get("effective_date", ""),
                    source_url=metadata.get("source_url", ""),
                    collection=collection_name
                )
                total_docs += 1

            logger.info(f"  Indexed {len(documents)} documents from {collection_name}")

        writer.commit()
        logger.info(f"✅ BM25 index built: {total_docs} documents indexed")

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        n_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search BM25 index for exact term matches.

        Args:
            query: Search query
            sources: Filter by source organizations (cpso, pho, cep, quality_standards, choosing_wisely)
            n_results: Number of results to return

        Returns:
            List of matching documents with BM25 scores
        """
        if not self.index:
            logger.error("BM25 index not initialized")
            return []

        # Map sources to collections
        collection_map = {
            'cpso': 'opa_cpso_corpus',
            'pho': 'opa_pho_corpus',
            'cep': 'opa_cep_corpus',
            'quality_standards': 'opa_quality_standards_corpus',
            'ontario_health_quality_standards': 'opa_quality_standards_corpus',
            'choosing_wisely': 'opa_choosing_wisely_corpus',
            'choosing_wisely_canada': 'opa_choosing_wisely_corpus'
        }

        target_collections = None
        if sources:
            target_collections = [collection_map.get(s) for s in sources if s in collection_map]

        # Search in thread executor (Whoosh is not async)
        def _search():
            with self.index.searcher() as searcher:
                # Parse query for text field (BM25 on main content)
                # Use OrGroup to combine terms with OR (default is AND)
                parser = QueryParser("text", self.index.schema, group=OrGroup)

                try:
                    parsed_query = parser.parse(query)
                except Exception as e:
                    logger.error(f"Error parsing BM25 query '{query}': {e}")
                    return []

                # Execute search
                results = searcher.search(parsed_query, limit=n_results * 2)  # Get more for filtering

                # Convert to standard format
                matches = []
                for result in results:
                    # Filter by collection if sources specified
                    if target_collections and result["collection"] not in target_collections:
                        continue

                    matches.append({
                        "document_id": result["doc_id"],
                        "text": result["text"],
                        "bm25_score": result.score,  # Whoosh BM25 score
                        "metadata": {
                            "document_title": result.get("document_title", ""),
                            "section_heading": result.get("section_heading", ""),
                            "source_org": result.get("source_org", ""),
                            "document_type": result.get("document_type", ""),
                            "chunk_type": result.get("chunk_type", ""),
                            "effective_date": result.get("effective_date", ""),
                            "source_url": result.get("source_url", "")
                        },
                        "collection": result["collection"]
                    })

                    # Stop once we have enough results
                    if len(matches) >= n_results:
                        break

                return matches

        results = await asyncio.get_event_loop().run_in_executor(None, _search)
        logger.debug(f"BM25 search for '{query[:50]}...': {len(results)} results")

        return results

    def close(self):
        """Close the index (cleanup)."""
        if self.index:
            self.index.close()
            logger.debug("BM25 index closed")
