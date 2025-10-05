"""
Shared ChromaDB client singleton to avoid settings conflicts.
"""
import chromadb
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Singleton ChromaDB client to avoid settings conflicts
_chroma_client = None

def get_chroma_client():
    """Get or create shared ChromaDB client singleton."""
    global _chroma_client
    if _chroma_client is None:
        chroma_dir = Path("/app/data/chroma")
        settings = chromadb.config.Settings(
            anonymized_telemetry=False,
            allow_reset=False,
            is_persistent=True
        )
        _chroma_client = chromadb.PersistentClient(path=str(chroma_dir), settings=settings)
        logger.info(f"Initialized shared ChromaDB client: {chroma_dir}")
    return _chroma_client
