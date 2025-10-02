"""
Railway endpoint for ingesting pre-chunked structured data.
Handles quality standards, Choosing Wisely recommendations, and other pre-processed data.

Add this to your existing admin_endpoints.py or deploy as a separate endpoint.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Any, Optional
import logging
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from pathlib import Path
import os
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/admin/ingest-prechunked")
async def ingest_prechunked_data(request: Dict[str, Any]):
    """
    Ingest pre-chunked structured data directly into Chroma.
    
    This endpoint is designed for data that has already been:
    - Structured into chunks with text and metadata
    - Organized with proper IDs
    - Ready for embedding generation
    
    Expected payload format:
    {
        "collection_name": "opa_quality_standards_corpus",
        "source_org": "ontario_health",
        "embedding_model": "text-embedding-3-small",  # Optional, defaults to text-embedding-3-small
        "chunks": [
            {
                "id": "unique_chunk_id",
                "text": "chunk text content",
                "metadata": {
                    "source": "ontario_health_quality_standards",
                    "title": "Document Title",
                    "chunk_type": "document|statement|section",
                    ... any other metadata ...
                }
            },
            ...
        ]
    }
    
    OR for convenience, also accepts structured documents that it will chunk:
    {
        "collection_name": "opa_quality_standards_corpus",
        "source_org": "ontario_health", 
        "document_type": "quality_standard|choosing_wisely|clinical_guideline",
        "documents": [
            {
                "title": "Document Title",
                "sections": [...],  # Will be converted to chunks
                "metadata": {...}
            }
        ]
    }
    """
    try:
        # Extract parameters
        collection_name = request.get("collection_name")
        source_org = request.get("source_org", "generic")
        embedding_model = request.get("embedding_model", "text-embedding-3-small")
        
        if not collection_name:
            raise ValueError("collection_name is required")
        
        # Initialize Chroma client
        chroma_path = "/app/data/chroma" if os.path.exists("/app/data") else "data/dr_opa_agent/chroma"
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Set up embedding function
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name=embedding_model
        )
        
        # Get or create collection with explicit embedding function
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=embedding_function
            )
            logger.info(f"Using existing collection: {collection_name}")
        except:
            collection = client.create_collection(
                name=collection_name,
                embedding_function=embedding_function,
                metadata={
                    "source_org": source_org,
                    "embedding_model": embedding_model,
                    "created_at": datetime.now().isoformat()
                }
            )
            logger.info(f"Created new collection: {collection_name}")
        
        # Process chunks or documents
        if "chunks" in request:
            # Direct chunks provided
            chunks = request["chunks"]
            logger.info(f"Processing {len(chunks)} pre-chunked items")
            
        elif "documents" in request:
            # Convert structured documents to chunks
            chunks = convert_documents_to_chunks(
                request["documents"],
                request.get("document_type", "generic"),
                source_org
            )
            logger.info(f"Converted {len(request['documents'])} documents to {len(chunks)} chunks")
            
        else:
            raise ValueError("Either 'chunks' or 'documents' must be provided")
        
        # Validate and clean chunks
        validated_chunks = validate_chunks(chunks)
        
        # Batch process chunks
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(validated_chunks), batch_size):
            batch = validated_chunks[i:i + batch_size]
            
            # Extract components
            ids = [chunk["id"] for chunk in batch]
            texts = [chunk["text"] for chunk in batch]
            metadatas = [chunk["metadata"] for chunk in batch]
            
            # Add to Chroma (embeddings generated automatically via embedding_function)
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            total_added += len(batch)
            logger.info(f"Added batch {i//batch_size + 1}: {len(batch)} chunks")
        
        return {
            "success": True,
            "collection_name": collection_name,
            "source_org": source_org,
            "chunks_ingested": total_added,
            "embedding_model": embedding_model,
            "message": f"Successfully ingested {total_added} chunks into {collection_name}"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting pre-chunked data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


def validate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and clean chunks for Chroma compatibility.
    
    - Ensures unique IDs
    - Validates metadata types (no None, no lists in metadata)
    - Ensures text content exists
    """
    seen_ids = set()
    validated = []
    
    for chunk in chunks:
        # Validate ID
        chunk_id = chunk.get("id")
        if not chunk_id:
            logger.warning("Skipping chunk without ID")
            continue
        
        if chunk_id in seen_ids:
            logger.warning(f"Duplicate ID found: {chunk_id}, skipping")
            continue
        
        seen_ids.add(chunk_id)
        
        # Validate text
        text = chunk.get("text", "").strip()
        if not text:
            logger.warning(f"Skipping chunk {chunk_id} with empty text")
            continue
        
        # Clean metadata - Chroma doesn't accept None or lists
        metadata = chunk.get("metadata", {})
        cleaned_metadata = {}
        
        for key, value in metadata.items():
            if value is None:
                continue  # Skip None values
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                cleaned_metadata[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, (str, int, float, bool)):
                cleaned_metadata[key] = value
            else:
                # Convert other types to string
                cleaned_metadata[key] = str(value)
        
        validated.append({
            "id": chunk_id,
            "text": text,
            "metadata": cleaned_metadata
        })
    
    return validated


def convert_documents_to_chunks(
    documents: List[Dict[str, Any]], 
    document_type: str,
    source_org: str
) -> List[Dict[str, Any]]:
    """
    Convert structured documents to chunks based on document type.
    
    Handles:
    - quality_standard: Documents with statements
    - choosing_wisely: Recommendations
    - clinical_guideline: Documents with sections
    """
    chunks = []
    
    for doc in documents:
        doc_id = generate_doc_id(doc.get("title", "unknown"))
        
        if document_type == "quality_standard":
            # Create document overview chunk
            chunks.append({
                "id": f"qs_{doc_id}_document",
                "text": create_quality_standard_overview(doc),
                "metadata": {
                    "source": f"{source_org}_quality_standards",
                    "source_org": source_org,
                    "title": doc.get("title", ""),
                    "doc_type": "quality_standard_overview",
                    "chunk_type": "document",
                    "num_statements": len(doc.get("statements", [])),
                    "ingested_at": datetime.now().isoformat()
                }
            })
            
            # Create statement chunks
            for stmt in doc.get("statements", []):
                stmt_num = stmt.get("number", 0)
                chunks.append({
                    "id": f"qs_{doc_id}_stmt{stmt_num}",
                    "text": create_statement_text(stmt, doc.get("title", "")),
                    "metadata": {
                        "source": f"{source_org}_quality_standards",
                        "source_org": source_org,
                        "parent_title": doc.get("title", ""),
                        "doc_type": "quality_statement",
                        "chunk_type": "statement",
                        "statement_number": stmt_num,
                        "statement_title": stmt.get("title", ""),
                        "ingested_at": datetime.now().isoformat()
                    }
                })
        
        elif document_type == "choosing_wisely":
            # Create specialty overview chunk
            chunks.append({
                "id": f"cw_{doc_id}_overview",
                "text": create_choosing_wisely_overview(doc),
                "metadata": {
                    "source": "choosing_wisely",
                    "source_org": source_org,
                    "specialty": doc.get("specialty", ""),
                    "doc_type": "choosing_wisely_overview",
                    "chunk_type": "document",
                    "num_recommendations": len(doc.get("recommendations", [])),
                    "ingested_at": datetime.now().isoformat()
                }
            })
            
            # Create recommendation chunks
            for rec in doc.get("recommendations", []):
                rec_num = rec.get("number", 0)
                chunks.append({
                    "id": f"cw_{doc_id}_rec{rec_num}",
                    "text": create_recommendation_text(rec, doc.get("specialty", "")),
                    "metadata": {
                        "source": "choosing_wisely",
                        "source_org": source_org,
                        "specialty": doc.get("specialty", ""),
                        "doc_type": "choosing_wisely_recommendation",
                        "chunk_type": "recommendation",
                        "recommendation_number": rec_num,
                        "recommendation_title": rec.get("title", ""),
                        "ingested_at": datetime.now().isoformat()
                    }
                })
        
        else:
            # Generic document with sections
            for section in doc.get("sections", []):
                chunks.append({
                    "id": f"{doc_id}_{section.get('id', 'unknown')}",
                    "text": section.get("text", ""),
                    "metadata": {
                        "source": source_org,
                        "source_org": source_org,
                        "title": doc.get("title", ""),
                        "doc_type": document_type,
                        "chunk_type": "section",
                        "section_title": section.get("title", ""),
                        "ingested_at": datetime.now().isoformat()
                    }
                })
    
    return chunks


def generate_doc_id(title: str) -> str:
    """Generate a clean document ID from title."""
    clean_title = title.lower()
    clean_title = ''.join(c if c.isalnum() or c.isspace() else '' for c in clean_title)
    clean_title = '_'.join(clean_title.split())[:50]
    return clean_title


def create_quality_standard_overview(doc: Dict[str, Any]) -> str:
    """Create overview text for quality standard."""
    text = f"Ontario Health Quality Standard: {doc.get('title', 'Unknown')}"
    
    if doc.get('year'):
        text += f" ({doc['year']})"
    
    # Add front matter if available
    fm = doc.get('front_matter', {})
    if fm.get('executive_summary'):
        text += f"\n\n## Executive Summary\n{fm['executive_summary']}"
    
    if fm.get('scope'):
        text += f"\n\n## Scope\n{fm['scope']}"
    
    # Add statement list
    statements = doc.get('statements', [])
    if statements:
        text += f"\n\n## Quality Statements ({len(statements)} Total)\n"
        for stmt in statements:
            text += f"\nStatement {stmt.get('number', '?')}: {stmt.get('title', 'Untitled')}"
            if stmt.get('brief_statement'):
                text += f"\n{stmt['brief_statement'][:200]}..."
    
    return text


def create_statement_text(stmt: Dict[str, Any], doc_title: str) -> str:
    """Create full text for a quality statement."""
    text = f"Ontario Health Quality Standard: {doc_title}\n"
    text += f"Quality Statement {stmt.get('number', '?')}: {stmt.get('title', 'Untitled')}\n"
    text += "=" * 60 + "\n"
    
    if stmt.get('full_statement'):
        text += f"\n## Statement\n{stmt['full_statement']}\n"
    
    if stmt.get('background'):
        text += f"\n## Background\n{stmt['background']}\n"
    
    for audience in ['for_patients', 'for_clinicians', 'for_health_services']:
        if stmt.get(audience):
            title = audience.replace('_', ' ').title()
            text += f"\n## {title}\n{stmt[audience]}\n"
    
    if stmt.get('indicators'):
        text += "\n## Quality Indicators\n"
        for indicator in stmt['indicators']:
            text += f"• {indicator}\n"
    
    return text


def create_choosing_wisely_overview(doc: Dict[str, Any]) -> str:
    """Create overview text for Choosing Wisely recommendations."""
    text = f"Choosing Wisely Canada: {doc.get('specialty', 'Unknown Specialty')}\n"
    
    if doc.get('organization'):
        text += f"Organization: {doc['organization']}\n"
    
    if doc.get('last_updated'):
        text += f"Last Updated: {doc['last_updated']}\n"
    
    recommendations = doc.get('recommendations', [])
    if recommendations:
        text += f"\n## Recommendations ({len(recommendations)} Total)\n"
        for rec in recommendations:
            text += f"\n{rec.get('number', '?')}. {rec.get('title', 'Untitled')}"
    
    return text


def create_recommendation_text(rec: Dict[str, Any], specialty: str) -> str:
    """Create full text for a Choosing Wisely recommendation."""
    text = f"Choosing Wisely Canada - {specialty}\n"
    text += f"Recommendation #{rec.get('number', '?')}: {rec.get('title', 'Untitled')}\n"
    text += "=" * 60 + "\n"
    
    if rec.get('description'):
        text += f"\n{rec['description']}\n"
    
    if rec.get('references'):
        text += "\n## References\n"
        for ref in rec['references']:
            text += f"• {ref}\n"
    
    return text