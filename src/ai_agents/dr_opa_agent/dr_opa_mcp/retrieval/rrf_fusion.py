"""
Reciprocal Rank Fusion (RRF) for merging dense + sparse retrieval results.
Based on Cormack et al. (2009) "Reciprocal Rank Fusion outperforms Condorcet and individual TREC systems"
"""
from typing import List, Dict, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RRFFusion:
    """Reciprocal Rank Fusion for merging dense + sparse retrieval results."""

    def __init__(self, c: float = 60.0):
        """
        Initialize RRF with constant c.

        Args:
            c: RRF constant (default 60). Higher = less emphasis on rank differences.
               Typical values: 30 (aggressive), 60 (balanced), 90 (conservative)
        """
        self.c = c
        logger.debug(f"RRFFusion initialized with c={c}")

    def fuse(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fuse dense (vector) and sparse (BM25) results using RRF.

        RRF Formula: score(doc) = Σ 1/(c + rank_i)
        Where rank_i is the rank of document in retriever i (1-indexed)

        Args:
            dense_results: Results from ChromaDB (with distance/similarity_score)
            sparse_results: Results from BM25 (with bm25_score)
            k: Number of final results to return

        Returns:
            Fused results sorted by RRF score (highest first)
        """
        # Build document index: doc_id -> document data
        doc_index = {}
        rrf_scores = defaultdict(float)

        # Process dense results (rank by similarity/distance)
        for rank, doc in enumerate(dense_results, start=1):
            doc_id = doc.get("document_id")
            if not doc_id:
                continue

            # RRF contribution from dense retriever
            rrf_scores[doc_id] += 1.0 / (self.c + rank)

            # Store document data (prefer first occurrence)
            if doc_id not in doc_index:
                doc_index[doc_id] = {
                    **doc,
                    "dense_rank": rank,
                    "dense_score": doc.get("similarity_score") or (1.0 - doc.get("distance", 0.0))
                }

        # Process sparse results (rank by BM25 score)
        for rank, doc in enumerate(sparse_results, start=1):
            doc_id = doc.get("document_id")
            if not doc_id:
                continue

            # RRF contribution from sparse retriever
            rrf_scores[doc_id] += 1.0 / (self.c + rank)

            # Store document data if new, or add BM25 info to existing
            if doc_id not in doc_index:
                doc_index[doc_id] = {
                    **doc,
                    "bm25_rank": rank,
                    "bm25_score": doc.get("bm25_score", 0.0)
                }
            else:
                # Merge BM25 info into existing doc (from dense)
                doc_index[doc_id]["bm25_rank"] = rank
                doc_index[doc_id]["bm25_score"] = doc.get("bm25_score", 0.0)

        # Build final result list with RRF scores
        fused = []
        for doc_id, doc in doc_index.items():
            doc["rrf_score"] = rrf_scores[doc_id]
            doc["provenance"] = self._get_provenance(doc)
            fused.append(doc)

        # Sort by RRF score (descending)
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)

        logger.info(
            f"RRF fusion (c={self.c}): {len(dense_results)} dense + {len(sparse_results)} sparse "
            f"→ {len(fused)} unique docs"
        )
        top_scores = [f"{d['rrf_score']:.4f}" for d in fused[:3]]
        logger.debug(f"Top 3 RRF scores: {top_scores}")

        # Log provenance distribution
        provenance_counts = defaultdict(int)
        for doc in fused[:k]:
            provenance_counts[doc["provenance"]] += 1
        logger.debug(f"Provenance distribution (top {k}): {dict(provenance_counts)}")

        return fused[:k]

    def _get_provenance(self, doc: Dict[str, Any]) -> str:
        """Determine retrieval provenance for a document."""
        has_dense = "dense_rank" in doc
        has_sparse = "bm25_rank" in doc

        if has_dense and has_sparse:
            return "dense+sparse"
        elif has_dense:
            return "dense"
        elif has_sparse:
            return "sparse"
        else:
            return "unknown"
