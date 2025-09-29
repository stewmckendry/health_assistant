"""
Admin endpoints for Railway database migration
These endpoints receive exported data and load it into Railway databases
"""

import sqlite3
import json
import os
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