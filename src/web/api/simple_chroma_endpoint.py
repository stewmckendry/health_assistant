"""
Simple ChromaDB ingestion endpoint for Railway
Bypasses complex ingester classes with import issues
"""

import chromadb
from chromadb.utils import embedding_functions
import os
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Import shared client getter
from src.web.api.chroma_client import get_chroma_client

def create_simple_chroma_endpoint(app):
    """Register simple ChromaDB ingestion endpoint"""

    @app.post("/admin/direct-chroma-upload")
    async def direct_chroma_upload(request: Dict[str, Any]):
        """Direct ChromaDB upload without complex imports"""
        try:
            collection_name = request.get("collection_name")
            documents = request.get("documents", [])
            metadatas = request.get("metadatas", [])
            ids = request.get("ids", [])

            logger.info(f"Direct ChromaDB upload to collection: {collection_name}")
            logger.info(f"Documents to upload: {len(documents)}")

            # Use shared ChromaDB client
            client = get_chroma_client()
            
            # Delete existing collection if it exists
            try:
                client.delete_collection(collection_name)
                logger.info(f"Deleted existing collection: {collection_name}")
            except:
                pass
            
            # Create collection with OpenAI embeddings
            embedding_function = None
            if os.getenv("OPENAI_API_KEY"):
                embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    model_name="text-embedding-ada-002"
                )
            
            collection = client.create_collection(
                name=collection_name,
                embedding_function=embedding_function
            )
            
            # Add documents in batches
            batch_size = 100
            total_added = 0
            
            for i in range(0, len(documents), batch_size):
                batch_end = min(i + batch_size, len(documents))
                
                batch_docs = documents[i:batch_end]
                batch_metas = metadatas[i:batch_end] if metadatas else None
                batch_ids = ids[i:batch_end] if ids else [f"{collection_name}_{j}" for j in range(i, batch_end)]
                
                # Clean metadata - convert lists to strings
                if batch_metas:
                    cleaned_metas = []
                    for meta in batch_metas:
                        cleaned_meta = {}
                        for key, value in meta.items():
                            if isinstance(value, list):
                                cleaned_meta[key] = ", ".join(str(v) for v in value)
                            elif value is None:
                                cleaned_meta[key] = ""
                            else:
                                cleaned_meta[key] = str(value)
                        cleaned_metas.append(cleaned_meta)
                    batch_metas = cleaned_metas
                
                collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
                
                total_added += len(batch_docs)
                logger.info(f"Added batch {i//batch_size + 1}: {total_added}/{len(documents)} documents")
            
            # Get collection stats
            count = collection.count()
            
            return {
                "success": True,
                "collection_name": collection_name,
                "documents_added": total_added,
                "collection_count": count,
                "message": f"Successfully created collection {collection_name} with {count} documents"
            }
            
        except Exception as e:
            logger.error(f"Error in direct ChromaDB upload: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to upload to ChromaDB: {str(e)}"
            }
    
    @app.get("/admin/chroma-collections")
    async def list_chroma_collections():
        """List all ChromaDB collections"""
        try:
            chroma_path = "/app/data/chroma"
            
            if not os.path.exists(chroma_path):
                return {
                    "success": True,
                    "collections": [],
                    "message": "No ChromaDB directory found"
                }

            # Use shared ChromaDB client
            client = get_chroma_client()
            collections = client.list_collections()
            
            collection_info = []
            for col in collections:
                try:
                    count = client.get_collection(col.name).count()
                    collection_info.append({
                        "name": col.name,
                        "count": count
                    })
                except:
                    collection_info.append({
                        "name": col.name,
                        "count": 0
                    })
            
            return {
                "success": True,
                "collections": collection_info,
                "total_collections": len(collection_info),
                "message": f"Found {len(collection_info)} ChromaDB collections"
            }
            
        except Exception as e:
            logger.error(f"Error listing ChromaDB collections: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to list collections: {str(e)}"
            }