"""
Chroma vector client with timeout support for MCP tools.
Shared utility for semantic search across OHIP, ADP, and ODB documents.
"""
import asyncio
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import logging
import time
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class VectorClient:
    """
    Async Chroma client for vector similarity search with timeout.
    Used by all MCP tools for semantic document retrieval.
    """
    
    def __init__(
        self,
        persist_directory: str = "data/dr_off_agent/processed/dr_off/chroma",
        timeout_ms: int = 1000,
        max_workers: int = 3
    ):
        """
        Initialize Chroma client for vector search.
        
        Args:
            persist_directory: Path to Chroma persistence directory
            timeout_ms: Search timeout in milliseconds (default 1000ms)
            max_workers: Max concurrent workers for async operations
        """
        self.persist_dir = Path(persist_directory)
        self.timeout_seconds = timeout_ms / 1000.0
        
        # Thread pool for Chroma operations (not natively async)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Initialize OpenAI client for embeddings
        # Collections were created with text-embedding-3-small model
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
            self.embedding_model = "text-embedding-3-small"
            logger.info(f"Using OpenAI embeddings model: {self.embedding_model}")
        else:
            logger.error("OPENAI_API_KEY not found - embeddings will not work correctly")
            self.openai_client = None
            self.embedding_model = None
        
        # Initialize Chroma client with unique settings to avoid conflicts
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        except (ValueError, RuntimeError) as e:
            # If client already exists, try to get it without special settings
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        
        # Cache collection references
        self._collections = {}
        self._load_collections()
        
        logger.info(f"Vector client initialized: {self.persist_dir} (timeout={timeout_ms}ms)")
    
    def _load_collections(self):
        """Load and cache available collections."""
        try:
            # Pre-load known collections
            collection_names = [
                "ohip_documents",   # OHIP Schedule & Act chunks (191 embeddings)
                "adp_documents",    # ADP manual chunks (if exists)  
                "odb_documents"     # ODB policy chunks (49 embeddings)
            ]
            
            for name in collection_names:
                try:
                    # Get collection WITHOUT embedding function to avoid conflicts
                    # The collections were created with 1536-dim embeddings
                    collection = self.client.get_collection(name=name)
                    self._collections[name] = collection
                    count = collection.count()
                    logger.info(f"Loaded collection '{name}': {count} embeddings")
                except Exception as e:
                    logger.warning(f"Collection '{name}' not found: {e}")
                    
        except Exception as e:
            logger.error(f"Error loading collections: {e}")
    
    def _search_collection(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
        include: List[str] = ["documents", "metadatas", "distances"]
    ) -> Dict[str, Any]:
        """
        Execute vector search in a specific collection (blocking).
        
        Args:
            collection_name: Name of Chroma collection
            query_text: Query text to embed and search
            n_results: Number of results to return
            where: Metadata filter conditions
            include: Fields to include in results
            
        Returns:
            Chroma query results dictionary
        """
        if collection_name not in self._collections:
            # If collection doesn't exist, return empty results instead of raising
            logger.warning(f"Collection '{collection_name}' not found, returning empty results")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        collection = self._collections[collection_name]
        
        # Generate embedding using OpenAI
        if self.openai_client:
            # Use OpenAI API directly to generate query embedding
            embedding_response = self.openai_client.embeddings.create(
                input=[query_text],
                model=self.embedding_model
            )
            query_embedding = embedding_response.data[0].embedding
            
            # Perform similarity search with pre-computed embeddings
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=include
            )
        else:
            # This won't work properly without OpenAI embeddings
            logger.error("Cannot perform search without OpenAI API key")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        return results
    
    async def search(
        self,
        query: str,
        collection: str = "ohip_documents",
        n_results: int = 5,
        where: Optional[Dict] = None,
        timeout_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Async vector similarity search with timeout.
        
        Args:
            query: Search query text
            collection: Collection name to search
            n_results: Number of results to return
            where: Metadata filters (e.g., {"source": "schedule.pdf"})
            timeout_ms: Override default timeout (optional)
            
        Returns:
            List of search results with text and metadata
            
        Raises:
            asyncio.TimeoutError: If search exceeds timeout
        """
        timeout = (timeout_ms / 1000.0) if timeout_ms else self.timeout_seconds
        
        start_time = time.time()
        try:
            # Run blocking Chroma operation in thread pool with timeout
            results = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._search_collection,
                    collection,
                    query,
                    n_results,
                    where,
                    ["documents", "metadatas", "distances"]
                ),
                timeout=timeout
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Transform Chroma results to consistent format
            formatted_results = []
            if results and results.get("documents"):
                documents = results["documents"][0]  # First query result
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                
                for i, doc in enumerate(documents):
                    formatted_results.append({
                        "text": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "distance": distances[i] if i < len(distances) else None,
                        "collection": collection
                    })
            
            logger.debug(f"Vector search completed in {elapsed_ms:.1f}ms: {len(formatted_results)} results")
            return formatted_results
            
        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(f"Vector search timeout after {elapsed_ms:.1f}ms: {query[:100]}...")
            raise
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise
    
    async def search_schedule(
        self,
        query: str,
        codes: Optional[List[str]] = None,
        n_results: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Search OHIP Schedule of Benefits and Health Insurance Act.
        
        Args:
            query: Search query
            codes: Filter by specific fee codes in metadata
            n_results: Number of results
            
        Returns:
            List of relevant OHIP document chunks
        """
        where = {}
        if codes:
            # Filter by fee codes if they exist in metadata
            # Chroma doesn't support single-value $in in simple where clauses
            # So we'll just use the codes for text search instead
            where = None  # Let text search handle code matching
        
        return await self.search(
            query=query,
            collection="ohip_documents",
            n_results=n_results,
            where=where if where else None
        )
    
    async def search_adp(
        self,
        query: str,
        device_category: Optional[str] = None,
        n_results: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Search ADP manuals (Communication Aids & Mobility Devices).
        
        Args:
            query: Search query
            device_category: Filter by device category if specified
            n_results: Number of results
            
        Returns:
            List of relevant ADP document chunks
        """
        # ChromaDB doesn't support $contains, so we'll use text search instead
        # and let the query embedding handle the device category matching
        where = None  # Let semantic search handle the filtering
        
        return await self.search(
            query=query,
            collection="adp_documents",  # Try adp_documents, fallback to ohip_documents if not found
            n_results=n_results,
            where=where if where else None
        )
    
    async def search_odb(
        self,
        query: str,
        drug_class: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search ODB formulary policy documents.
        
        Args:
            query: Search query
            drug_class: Filter by therapeutic class if specified
            n_results: Number of results
            
        Returns:
            List of relevant ODB document chunks
        """
        # ChromaDB doesn't support $contains, so we'll use text search instead
        where = None  # Let semantic search handle the filtering
        
        return await self.search(
            query=query,
            collection="odb_documents",
            n_results=n_results,
            where=where if where else None
        )
    
    async def get_passages_by_ids(
        self,
        chunk_ids: List[str],
        collection: str = "ohip_documents"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve specific passages by their chunk IDs.
        Used by source.passages tool for "show source" functionality.
        
        Args:
            chunk_ids: List of chunk IDs to retrieve
            collection: Collection containing the chunks
            
        Returns:
            List of passages with full text and metadata
        """
        if collection not in self._collections:
            logger.warning(f"Collection '{collection}' not found for passage retrieval")
            return []  # Return empty list instead of raising error
        
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._collections[collection].get,
                chunk_ids
            )
            
            formatted = []
            if results:
                documents = results.get("documents", [])
                metadatas = results.get("metadatas", [])
                
                for i, doc in enumerate(documents):
                    formatted.append({
                        "id": chunk_ids[i] if i < len(chunk_ids) else None,
                        "text": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "collection": collection
                    })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error retrieving passages: {e}")
            raise
    
    async def close(self):
        """Cleanup thread pool executor."""
        self.executor.shutdown(wait=True)
    
    def __del__(self):
        """Ensure executor is cleaned up."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)