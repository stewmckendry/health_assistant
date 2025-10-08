"""
Cross-encoder reranker for improving ranking quality.

Uses bge-reranker-v2-m3 to rerank top-K candidates from dense/hybrid retrieval.
This improves MRR and nDCG@10 by scoring query-document pairs directly.
"""

import logging
import os
from typing import List, Dict, Any

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None

logger = logging.getLogger(__name__)

# Configure HuggingFace cache to use Railway persistent volume
if TORCH_AVAILABLE and os.environ.get("RAILWAY_ENVIRONMENT"):
    os.environ["HF_HOME"] = "/app/data/huggingface_cache"
    os.environ["TRANSFORMERS_CACHE"] = "/app/data/huggingface_cache"
    logger.info("Railway environment detected - using persistent volume for HuggingFace cache")


class CrossEncoderReranker:
    """
    Cross-encoder reranker using bge-reranker-v2-m3.

    Cross-encoders score query-document pairs jointly, providing better
    ranking quality than bi-encoders (which encode query and document separately).

    Use this for reranking top-50 candidates → top-10 results.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = None):
        """
        Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace model name (default: bge-reranker-v2-m3)
            device: Device to run model on ('cpu', 'cuda', 'mps', or None for auto)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("torch and transformers are required for CrossEncoderReranker. Install with: pip install torch transformers")

        logger.info(f"Initializing CrossEncoderReranker with model: {model_name}")

        # Auto-detect device if not specified
        if device is None:
            if torch.cuda.is_available():
                device = 'cuda'
            elif torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'

        self.device = device
        logger.info(f"Using device: {self.device}")

        # Load tokenizer and model
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
        text_field: str = 'text'
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using cross-encoder.

        Args:
            query: Search query
            documents: List of documents to rerank (each must have text_field)
            top_k: Number of top results to return
            text_field: Field name containing document text (default: 'text')

        Returns:
            Reranked documents (top_k) with 'ce_score' field added
        """
        if not documents:
            logger.warning("No documents to rerank")
            return []

        logger.info(f"Reranking {len(documents)} documents with cross-encoder...")
        logger.debug(f"Query: {query[:100]}...")

        # Extract text from documents
        doc_texts = []
        for i, doc in enumerate(documents):
            text = doc.get(text_field, '')
            if not text:
                logger.warning(f"Document {i} missing '{text_field}' field, using empty string")
            doc_texts.append(text)

        # Create query-document pairs
        pairs = [(query, text) for text in doc_texts]

        # Batch encode and score
        try:
            with torch.no_grad():
                inputs = self.tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    return_tensors='pt',
                    max_length=512
                ).to(self.device)

                # Get logits (raw scores)
                logits = self.model(**inputs, return_dict=True).logits
                scores = logits.view(-1).float().cpu().tolist()

            logger.info(f"Cross-encoder scoring complete: {len(scores)} scores generated")

        except Exception as e:
            logger.error(f"Error during cross-encoder scoring: {e}")
            # Fallback: use existing scores or distance
            scores = [
                doc.get('relevance_score', 1.0 / (1.0 + doc.get('distance', 1.0)))
                for doc in documents
            ]
            logger.warning("Falling back to existing scores due to error")

        # Attach scores to documents
        for doc, score in zip(documents, scores):
            doc['ce_score'] = score

        # Sort by cross-encoder score (descending)
        documents.sort(key=lambda x: x.get('ce_score', 0.0), reverse=True)

        # Log top results
        if documents:
            top_scores = [f"{doc.get('document_id', doc.get('id', 'unknown'))}: {doc['ce_score']:.3f}"
                         for doc in documents[:5]]
            logger.info(f"Top 5 reranked results: {top_scores}")

        # Return top_k results
        reranked = documents[:top_k]
        logger.info(f"Reranking complete: returning top {len(reranked)} documents")

        return reranked
