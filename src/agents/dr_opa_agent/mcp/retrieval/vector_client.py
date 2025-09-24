"""
Chroma vector client with timeout support for OPA MCP tools.
Shared utility for semantic search across OPA practice guidance documents.
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

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class VectorClient:
    """
    Async Chroma client for vector similarity search with timeout.
    Used by all OPA MCP tools for semantic document retrieval.
    """
    
    def __init__(
        self,
        persist_directory: str = "data/dr_opa_agent/chroma",
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
        
        # Initialize OpenAI embedding function to match the collections
        # Collections were created with text-embedding-3-small
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-small"
            )
            logger.info("Using OpenAI embedding function (text-embedding-3-small)")
        else:
            logger.warning("OPENAI_API_KEY not found - using default embedding function")
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
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
        """Load all available collections."""
        try:
            # List all collections
            collections = self.client.list_collections()
            
            for collection in collections:
                collection_name = collection.name
                # Get collection with embedding function
                # For OPA collections, always use OpenAI embedding
                if 'opa' in collection_name.lower():
                    try:
                        self._collections[collection_name] = self.client.get_collection(
                            name=collection_name,
                            embedding_function=self.embedding_function
                        )
                        logger.info(f"Loaded collection: {collection_name} with OpenAI embedding")
                    except Exception as e:
                        # If that fails, try to get or create with correct embedding
                        logger.warning(f"Recreating collection {collection_name} with correct embedding")
                        try:
                            self.client.delete_collection(collection_name)
                        except:
                            pass
                        self._collections[collection_name] = self.client.get_or_create_collection(
                            name=collection_name,
                            embedding_function=self.embedding_function
                        )
                        logger.info(f"Recreated collection: {collection_name}")
                else:
                    # Non-OPA collections
                    self._collections[collection_name] = self.client.get_collection(
                        name=collection_name
                    )
                    logger.info(f"Loaded collection: {collection_name}")
            
            logger.info(f"Loaded {len(self._collections)} collections")
            
        except Exception as e:
            logger.error(f"Error loading collections: {e}")
    
    def _search_collection(
        self,
        collection_name: str,
        query: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search a specific collection (runs in thread).
        
        Args:
            collection_name: Name of collection to search
            query: Query text
            n_results: Number of results
            where: Metadata filters
            
        Returns:
            Search results from collection
        """
        if collection_name not in self._collections:
            logger.warning(f"Collection {collection_name} not found")
            return {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        collection = self._collections[collection_name]
        
        try:
            # Query with timeout
            start_time = time.time()
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                logger.warning(f"Query exceeded timeout: {elapsed:.2f}s > {self.timeout_seconds}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying collection {collection_name}: {e}")
            return {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    async def search_sections(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        doc_types: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        n_results: int = 10,
        include_superseded: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search document sections using vector similarity.
        
        Args:
            query: Search query
            sources: Filter by source organizations
            doc_types: Filter by document types
            topics: Filter by topics
            n_results: Number of results to return
            include_superseded: Include superseded documents
            
        Returns:
            List of matching sections with similarity scores
        """
        # Build metadata filter
        where = {}
        where_conditions = []
        
        if not include_superseded:
            where_conditions.append({"is_superseded": {"$eq": "False"}})
        
        if sources:
            where_conditions.append({"source_org": {"$in": sources}})
        
        if doc_types:
            where_conditions.append({"document_type": {"$in": doc_types}})
        
        if topics:
            # Topics are stored as comma-separated string in metadata
            topic_conditions = []
            for topic in topics:
                topic_conditions.append({"topics": {"$contains": topic}})
            if topic_conditions:
                where_conditions.append({"$or": topic_conditions})
        
        if where_conditions:
            if len(where_conditions) == 1:
                where = where_conditions[0]
            else:
                where = {"$and": where_conditions}
        
        # Search across all relevant collections
        results = []
        loop = asyncio.get_event_loop()
        
        # Search main corpus collection
        for collection_name in self._collections.keys():
            if 'opa' in collection_name.lower():
                search_results = await loop.run_in_executor(
                    self.executor,
                    self._search_collection,
                    collection_name,
                    query,
                    n_results,
                    where if where else None
                )
                
                # Process results
                if search_results and search_results['ids'] and search_results['ids'][0]:
                    for i, chunk_id in enumerate(search_results['ids'][0]):
                        metadata = search_results['metadatas'][0][i] if search_results['metadatas'] else {}
                        document = search_results['documents'][0][i] if search_results['documents'] else ""
                        distance = search_results['distances'][0][i] if 'distances' in search_results else 1.0
                        
                        # Convert distance to similarity score (1 - normalized_distance)
                        similarity = max(0, 1 - (distance / 2))  # Assuming L2 distance
                        
                        results.append({
                            'chunk_id': chunk_id,
                            'text': document,
                            'similarity_score': similarity,
                            'metadata': metadata,
                            'collection': collection_name
                        })
        
        # Sort by similarity score and limit results
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:n_results]
    
    async def get_passages_by_ids(
        self,
        chunk_ids: List[str],
        collection: str = "opa_cpso_corpus"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve specific passages by their chunk IDs.
        
        Args:
            chunk_ids: List of chunk IDs to retrieve
            collection: Collection name
            
        Returns:
            List of passages with metadata
        """
        if collection not in self._collections:
            logger.warning(f"Collection {collection} not found")
            return []
        
        coll = self._collections[collection]
        
        try:
            # Get specific documents by ID
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                lambda: coll.get(ids=chunk_ids)
            )
            
            passages = []
            if results and results.get('ids'):
                for i, chunk_id in enumerate(results['ids']):
                    passages.append({
                        'id': chunk_id,
                        'text': results['documents'][i] if results.get('documents') else "",
                        'metadata': results['metadatas'][i] if results.get('metadatas') else {}
                    })
            
            return passages
            
        except Exception as e:
            logger.error(f"Error retrieving passages: {e}")
            return []
    
    async def find_similar(
        self,
        text: str,
        collection: str = "opa_cpso_corpus",
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar documents to a given text.
        
        Args:
            text: Reference text
            collection: Collection to search
            n_results: Number of similar documents
            
        Returns:
            Similar documents with scores
        """
        if collection not in self._collections:
            logger.warning(f"Collection {collection} not found")
            return []
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self._search_collection,
            collection,
            text,
            n_results,
            None
        )
        
        similar = []
        if results and results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][i] if 'distances' in results else 1.0
                similarity = max(0, 1 - (distance / 2))
                
                similar.append({
                    'chunk_id': chunk_id,
                    'text': results['documents'][0][i] if results['documents'] else "",
                    'similarity_score': similarity,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                })
        
        return similar
    
    async def close(self):
        """Close the thread pool executor."""
        self.executor.shutdown(wait=True)