"""
Retrieval quality metrics for evaluating search performance.

Implements standard information retrieval metrics:

- **Recall@k**: "Did we find most of the relevant documents?"
  Measures what fraction of all relevant documents appear in the Top-k results.
  High recall means we're not missing important information.
  Example: If 3 relevant docs exist and we found 2 in Top-50, Recall@50 = 0.67

- **MRR (Mean Reciprocal Rank)**: "How quickly do we find a relevant result?"
  Measures how high-ranked the first relevant document is.
  High MRR means relevant results appear near the top.
  Example: First relevant at rank 3 → MRR = 1/3 = 0.33

- **nDCG@k**: "Are the most relevant results ranked highest?"
  Measures ranking quality, giving more credit for highly relevant docs at top positions.
  High nDCG means the best results are ranked before mediocre ones.
  Example: Perfect ranking = 1.0, random ranking = ~0.5

- **Hit@k**: "Did we find at least one relevant result in Top-k?"
  Binary metric - either we found something relevant (1.0) or we didn't (0.0).
  Useful for pass/fail evaluation.
  Example: If any of Top-10 results is relevant → Hit@10 = 1.0
"""

from typing import List, Dict, Set
import numpy as np


class RetrievalMetrics:
    """Compute retrieval quality metrics for search evaluation."""

    @staticmethod
    def recall_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int = 50) -> float:
        """
        Recall@k: Fraction of relevant items in Top-k results.

        Formula: |relevant ∩ top_k| / |relevant|

        Args:
            retrieved_ids: List of retrieved document IDs in ranked order
            relevant_ids: Set of ground-truth relevant document IDs
            k: Cutoff rank (default: 50)

        Returns:
            Recall score between 0.0 and 1.0

        Example:
            >>> retrieved = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
            >>> relevant = {'doc2', 'doc4', 'doc6'}
            >>> RetrievalMetrics.recall_at_k(retrieved, relevant, k=5)
            0.6666666666666666  # Found 2 out of 3 relevant docs
        """
        if not relevant_ids:
            return 0.0

        top_k = set(retrieved_ids[:k])
        return len(top_k & relevant_ids) / len(relevant_ids)

    @staticmethod
    def mrr(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
        """
        Mean Reciprocal Rank: 1/rank of first relevant item.

        Formula: 1 / (position of first relevant item)

        Args:
            retrieved_ids: List of retrieved document IDs in ranked order
            relevant_ids: Set of ground-truth relevant document IDs

        Returns:
            MRR score between 0.0 and 1.0

        Example:
            >>> retrieved = ['doc1', 'doc2', 'doc3', 'doc4']
            >>> relevant = {'doc3', 'doc5'}
            >>> RetrievalMetrics.mrr(retrieved, relevant)
            0.3333333333333333  # First relevant at rank 3 -> 1/3
        """
        for i, doc_id in enumerate(retrieved_ids, 1):
            if doc_id in relevant_ids:
                return 1.0 / i
        return 0.0

    @staticmethod
    def ndcg_at_k(retrieved_ids: List[str], relevance_scores: Dict[str, float], k: int = 10) -> float:
        """
        Normalized Discounted Cumulative Gain@k.

        DCG = Σ (2^rel_i - 1) / log2(i + 1)
        nDCG = DCG / IDCG (ideal DCG)

        Args:
            retrieved_ids: List of retrieved document IDs in ranked order
            relevance_scores: Dict mapping doc_id to relevance score (0.0-1.0 or binary)
            k: Cutoff rank (default: 10)

        Returns:
            nDCG score between 0.0 and 1.0

        Example:
            >>> retrieved = ['doc1', 'doc2', 'doc3']
            >>> relevance = {'doc1': 1.0, 'doc2': 0.5, 'doc3': 1.0}
            >>> RetrievalMetrics.ndcg_at_k(retrieved, relevance, k=3)
            0.9...  # High score - highly relevant docs ranked well
        """
        def dcg(scores: List[float]) -> float:
            """Compute Discounted Cumulative Gain."""
            return sum((2**score - 1) / np.log2(i + 2) for i, score in enumerate(scores))

        # Actual DCG (based on retrieval order)
        actual_scores = [relevance_scores.get(doc_id, 0.0) for doc_id in retrieved_ids[:k]]
        actual_dcg = dcg(actual_scores)

        # Ideal DCG (best possible ordering)
        ideal_scores = sorted(relevance_scores.values(), reverse=True)[:k]
        ideal_dcg = dcg(ideal_scores)

        if ideal_dcg == 0:
            return 0.0

        return actual_dcg / ideal_dcg

    @staticmethod
    def hit_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int = 10) -> float:
        """
        Hit@k: Binary indicator if any relevant item in Top-k.

        Args:
            retrieved_ids: List of retrieved document IDs in ranked order
            relevant_ids: Set of ground-truth relevant document IDs
            k: Cutoff rank (default: 10)

        Returns:
            1.0 if at least one relevant item in Top-k, else 0.0

        Example:
            >>> retrieved = ['doc1', 'doc2', 'doc3']
            >>> relevant = {'doc2', 'doc5'}
            >>> RetrievalMetrics.hit_at_k(retrieved, relevant, k=3)
            1.0  # doc2 is in Top-3
        """
        top_k = set(retrieved_ids[:k])
        return 1.0 if (top_k & relevant_ids) else 0.0

    @staticmethod
    def precision_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int = 10) -> float:
        """
        Precision@k: Fraction of Top-k results that are relevant.

        Formula: |relevant ∩ top_k| / k

        Args:
            retrieved_ids: List of retrieved document IDs in ranked order
            relevant_ids: Set of ground-truth relevant document IDs
            k: Cutoff rank (default: 10)

        Returns:
            Precision score between 0.0 and 1.0

        Example:
            >>> retrieved = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
            >>> relevant = {'doc2', 'doc4'}
            >>> RetrievalMetrics.precision_at_k(retrieved, relevant, k=5)
            0.4  # 2 out of 5 are relevant
        """
        top_k = set(retrieved_ids[:k])
        return len(top_k & relevant_ids) / k if k > 0 else 0.0

    @staticmethod
    def compute_all_metrics(
        retrieved_ids: List[str],
        relevant_ids: Set[str],
        relevance_scores: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Compute all retrieval metrics at once.

        Args:
            retrieved_ids: List of retrieved document IDs in ranked order
            relevant_ids: Set of ground-truth relevant document IDs
            relevance_scores: Optional dict of doc_id -> relevance score for nDCG
                             If not provided, binary relevance is assumed (1.0 for relevant, 0.0 otherwise)

        Returns:
            Dict with all metric scores

        Example:
            >>> retrieved = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
            >>> relevant = {'doc2', 'doc4', 'doc6'}
            >>> metrics = RetrievalMetrics.compute_all_metrics(retrieved, relevant)
            >>> print(metrics)
            {
                'recall@50': 0.667,
                'recall@10': 0.667,
                'mrr': 0.5,
                'ndcg@10': 0.85,
                'hit@10': 1.0,
                'precision@10': 0.2
            }
        """
        # If no relevance scores provided, use binary relevance
        if relevance_scores is None:
            relevance_scores = {doc_id: 1.0 for doc_id in relevant_ids}

        return {
            'recall@50': RetrievalMetrics.recall_at_k(retrieved_ids, relevant_ids, k=50),
            'recall@10': RetrievalMetrics.recall_at_k(retrieved_ids, relevant_ids, k=10),
            'mrr': RetrievalMetrics.mrr(retrieved_ids, relevant_ids),
            'ndcg@10': RetrievalMetrics.ndcg_at_k(retrieved_ids, relevance_scores, k=10),
            'hit@10': RetrievalMetrics.hit_at_k(retrieved_ids, relevant_ids, k=10),
            'precision@10': RetrievalMetrics.precision_at_k(retrieved_ids, relevant_ids, k=10),
        }
