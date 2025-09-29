"""
Admin endpoints for Railway database migration
These endpoints receive exported data and load it into Railway databases
"""

import sqlite3
import json
import os
import sys
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class DatabaseLoadRequest(BaseModel):
    target_db: str
    tables: Dict[str, List[Dict[str, Any]]]
    metadata: Dict[str, Any]

class ChromaLoadRequest(BaseModel):
    collection_name: str
    documents: List[str]
    metadatas: List[Dict[str, Any]]
    embeddings: List[List[float]]
    ids: List[str]
    metadata: Dict[str, Any]

def register_admin_endpoints(app):
    """Register admin endpoints for database migration"""
    
    # Import and register simple ChromaDB endpoints
    try:
        from src.web.api.simple_chroma_endpoint import create_simple_chroma_endpoint
        create_simple_chroma_endpoint(app)
        logger.info("Simple ChromaDB endpoints registered")
    except Exception as e:
        logger.warning(f"Could not register simple ChromaDB endpoints: {e}")
    
    @app.post("/admin/load-database")
    async def load_database(request: DatabaseLoadRequest, background_tasks: BackgroundTasks):
        """Load exported SQLite data into Railway database"""
        try:
            # Ensure data directory exists
            data_dir = Path("/app/data")
            target_path = data_dir / request.target_db
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Loading database to: {target_path}")
            
            # Create/connect to database
            conn = sqlite3.connect(str(target_path))
            
            tables_loaded = 0
            total_rows = 0
            
            for table_name, rows in request.tables.items():
                if not rows:
                    logger.info(f"Skipping empty table: {table_name}")
                    continue
                
                logger.info(f"Loading table {table_name} with {len(rows)} rows")
                
                # Create table from first row structure
                if rows:
                    columns = list(rows[0].keys())
                    
                    # Create table (drop if exists)
                    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                    
                    # Build CREATE TABLE statement
                    column_defs = []
                    for col in columns:
                        # Simple type inference
                        sample_val = rows[0].get(col)
                        if isinstance(sample_val, int):
                            col_type = "INTEGER"
                        elif isinstance(sample_val, float):
                            col_type = "REAL"
                        else:
                            col_type = "TEXT"
                        column_defs.append(f"{col} {col_type}")
                    
                    create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
                    conn.execute(create_sql)
                    
                    # Insert data
                    placeholders = ", ".join(["?" for _ in columns])
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    for row in rows:
                        values = [row.get(col) for col in columns]
                        conn.execute(insert_sql, values)
                    
                    tables_loaded += 1
                    total_rows += len(rows)
                    logger.info(f"  ✓ Loaded {len(rows)} rows into {table_name}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database load completed: {tables_loaded} tables, {total_rows} rows")
            
            return {
                "success": True,
                "target_db": request.target_db,
                "tables_loaded": tables_loaded,
                "total_rows": total_rows,
                "message": f"Successfully loaded {tables_loaded} tables with {total_rows} total rows"
            }
            
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            raise HTTPException(status_code=500, detail=f"Database load failed: {str(e)}")
    
    @app.post("/admin/load-chroma")
    async def load_chroma(request: ChromaLoadRequest, background_tasks: BackgroundTasks):
        """Load exported ChromaDB data into Railway ChromaDB"""
        try:
            # Ensure chroma directory exists
            chroma_dir = Path("/app/data/chroma")
            chroma_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Loading ChromaDB collection: {request.collection_name}")
            logger.info(f"Documents to load: {len(request.documents)}")
            
            # Initialize ChromaDB client
            client = chromadb.PersistentClient(path=str(chroma_dir))
            
            # Try to get existing collection or create new one
            try:
                collection = client.get_collection(request.collection_name)
                logger.info(f"Found existing collection: {request.collection_name}")
                # Delete existing collection to replace with new data
                client.delete_collection(request.collection_name)
                logger.info(f"Deleted existing collection for fresh load")
            except:
                logger.info(f"Collection {request.collection_name} doesn't exist, will create new")
            
            # Create collection with OpenAI embeddings
            embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-ada-002"
            )
            
            collection = client.create_collection(
                name=request.collection_name,
                embedding_function=embedding_function
            )
            
            # Add documents in batches (ChromaDB has batch size limits)
            batch_size = 100
            documents_loaded = 0
            
            for i in range(0, len(request.documents), batch_size):
                batch_end = min(i + batch_size, len(request.documents))
                
                batch_ids = request.ids[i:batch_end]
                batch_documents = request.documents[i:batch_end]
                batch_metadatas = request.metadatas[i:batch_end]
                batch_embeddings = request.embeddings[i:batch_end] if request.embeddings else None
                
                if batch_embeddings:
                    # Use provided embeddings
                    collection.add(
                        ids=batch_ids,
                        documents=batch_documents,
                        metadatas=batch_metadatas,
                        embeddings=batch_embeddings
                    )
                else:
                    # Let ChromaDB generate embeddings
                    collection.add(
                        ids=batch_ids,
                        documents=batch_documents,
                        metadatas=batch_metadatas
                    )
                
                documents_loaded += len(batch_documents)
                logger.info(f"  ✓ Loaded batch {i//batch_size + 1}: {documents_loaded}/{len(request.documents)} documents")
            
            logger.info(f"ChromaDB load completed: {documents_loaded} documents in {request.collection_name}")
            
            return {
                "success": True,
                "collection_name": request.collection_name,
                "documents_loaded": documents_loaded,
                "message": f"Successfully loaded {documents_loaded} documents into {request.collection_name}"
            }
            
        except Exception as e:
            logger.error(f"Error loading ChromaDB: {e}")
            raise HTTPException(status_code=500, detail=f"ChromaDB load failed: {str(e)}")
    
    @app.get("/admin/database-status")
    async def database_status():
        """Check status of databases on Railway"""
        try:
            data_dir = Path("/app/data")
            chroma_dir = Path("/app/data/chroma")
            
            status = {
                "data_directory": str(data_dir),
                "data_exists": data_dir.exists(),
                "databases": {},
                "chroma_collections": {}
            }
            
            # Check SQLite databases
            if data_dir.exists():
                for db_file in data_dir.rglob("*.db"):
                    rel_path = str(db_file.relative_to(data_dir))
                    try:
                        conn = sqlite3.connect(str(db_file))
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = [row[0] for row in cursor.fetchall()]
                        
                        table_counts = {}
                        for table in tables:
                            count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                            table_counts[table] = count_cursor.fetchone()[0]
                        
                        conn.close()
                        
                        status["databases"][rel_path] = {
                            "exists": True,
                            "size_mb": round(db_file.stat().st_size / 1024 / 1024, 2),
                            "tables": table_counts
                        }
                    except Exception as e:
                        status["databases"][rel_path] = {
                            "exists": True,
                            "error": str(e)
                        }
            
            # Check ChromaDB collections
            if chroma_dir.exists():
                try:
                    client = chromadb.PersistentClient(path=str(chroma_dir))
                    collections = client.list_collections()
                    
                    for collection_info in collections:
                        collection = client.get_collection(collection_info.name)
                        count = collection.count()
                        status["chroma_collections"][collection_info.name] = {
                            "document_count": count,
                            "id": collection_info.id
                        }
                except Exception as e:
                    status["chroma_collections"]["error"] = str(e)
            
            return status
            
        except Exception as e:
            logger.error(f"Error checking database status: {e}")
            raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
    
    @app.post("/admin/ingest-json")
    async def ingest_json_data(request: Dict[str, Any], background_tasks: BackgroundTasks):
        """Ingest processed JSON data using existing ingestion pipelines"""
        try:
            agent_type = request.get("agent_type")  # "dr_off" or "dr_opa"
            json_data = request.get("json_data")
            collection_name = request.get("collection_name", "default_collection")
            
            logger.info(f"Starting JSON ingestion for {agent_type}, collection: {collection_name}")
            
            if agent_type == "dr_off":
                # Use ADP ingestion pipeline for dr_off agent
                from pathlib import Path
                import tempfile
                import json
                
                # Create temporary file for the JSON data
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(json_data, temp_file, indent=2)
                    temp_file_path = temp_file.name
                
                try:
                    # Import and use the ADP ingester with absolute import
                    sys.path.insert(0, '/app')
                    from src.ai_agents.dr_off_agent.ingestion.ingesters.adp_ingester import EnhancedADPIngester
                    
                    # Initialize ingester with Railway paths
                    db_path = "/app/data/ohip.db"
                    chroma_path = "/app/data/chroma"
                    
                    ingester = EnhancedADPIngester(
                        db_path=db_path,
                        chroma_path=chroma_path,
                        collection_name=collection_name
                    )
                    
                    # Ingest the JSON file
                    count = ingester.ingest_json(temp_file_path)
                    stats = ingester.get_stats()
                    
                    ingester.close()
                    
                    return {
                        "success": True,
                        "agent_type": agent_type,
                        "collection_name": collection_name,
                        "sections_ingested": count,
                        "stats": stats,
                        "message": f"Successfully ingested {count} sections for {agent_type}"
                    }
                    
                finally:
                    # Clean up temp file
                    import os
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                        
            elif agent_type == "dr_opa":
                # Use OPA ingestion pipeline for dr_opa agent  
                sys.path.insert(0, '/app')
                from src.ai_agents.dr_opa_agent.ingestion.base_ingester import BaseOPAIngester
                
                # Initialize ingester with Railway paths
                db_path = "/app/data/dr_opa_agent/opa.db"
                chroma_path = "/app/data/chroma"
                
                ingester = BaseOPAIngester(
                    source_org=request.get("source_org", "generic"),
                    db_path=db_path,
                    chroma_path=chroma_path,
                    collection_name=collection_name
                )
                
                # Process JSON data based on structure
                if isinstance(json_data, list):
                    # Handle array of documents
                    count = 0
                    for doc in json_data:
                        ingester.ingest_document(doc)
                        count += 1
                elif isinstance(json_data, dict):
                    # Handle single document
                    ingester.ingest_document(json_data)
                    count = 1
                else:
                    raise ValueError("Invalid JSON data format")
                
                ingester.close()
                
                return {
                    "success": True,
                    "agent_type": agent_type,
                    "collection_name": collection_name,
                    "documents_ingested": count,
                    "message": f"Successfully ingested {count} documents for {agent_type}"
                }
            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")
                
        except Exception as e:
            logger.error(f"Error during JSON ingestion: {e}")
            raise HTTPException(status_code=500, detail=f"JSON ingestion failed: {str(e)}")
    
    @app.post("/admin/bulk-ingest-files")
    async def bulk_ingest_files(request: Dict[str, Any], background_tasks: BackgroundTasks):
        """Bulk ingest multiple JSON files sent as file data"""
        try:
            files_data = request.get("files", [])
            agent_type = request.get("agent_type")
            
            logger.info(f"Starting bulk ingestion: {len(files_data)} files for {agent_type}")
            
            results = []
            total_processed = 0
            
            for file_info in files_data:
                filename = file_info.get("filename")
                content = file_info.get("content")
                
                try:
                    # Determine collection name from filename
                    if "adp" in filename.lower():
                        collection_name = "adp_documents"
                    elif "odb" in filename.lower():
                        collection_name = "odb_documents"
                    elif "ohip" in filename.lower():
                        collection_name = "ohip_documents"
                    elif "cpso" in filename.lower():
                        collection_name = "opa_cpso_corpus"
                    elif "cep" in filename.lower():
                        collection_name = "opa_cep_corpus"
                    elif "pho" in filename.lower():
                        collection_name = "opa_pho_corpus"
                    else:
                        collection_name = "default_collection"
                    
                    # Ingest this file
                    ingest_result = await ingest_json_data({
                        "agent_type": agent_type,
                        "json_data": content,
                        "collection_name": collection_name,
                        "source_org": file_info.get("source_org", "generic")
                    }, background_tasks)
                    
                    results.append({
                        "filename": filename,
                        "collection": collection_name,
                        "success": True,
                        "count": ingest_result.get("sections_ingested") or ingest_result.get("documents_ingested", 0)
                    })
                    
                    total_processed += results[-1]["count"]
                    
                except Exception as e:
                    logger.error(f"Error ingesting {filename}: {e}")
                    results.append({
                        "filename": filename,
                        "success": False,
                        "error": str(e)
                    })
            
            successful = sum(1 for r in results if r.get("success"))
            failed = len(results) - successful
            
            return {
                "success": True,
                "agent_type": agent_type,
                "files_processed": len(files_data),
                "successful": successful,
                "failed": failed,
                "total_items_processed": total_processed,
                "results": results,
                "message": f"Bulk ingestion complete: {successful}/{len(files_data)} files successful"
            }
            
        except Exception as e:
            logger.error(f"Error during bulk ingestion: {e}")
            raise HTTPException(status_code=500, detail=f"Bulk ingestion failed: {str(e)}")