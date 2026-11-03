"""
RHD Vector Storage Module (ChromaDB Integration)
Loads final_chunks.json, generates embeddings, and indexes into a persistent ChromaDB database.
Supports both English and Hindi vector similarity search.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils import embedding_functions

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rhd_chroma")


def get_chroma_collection(
    db_path: str = "rhd_ingestion/chroma_db",
    collection_name: str = "railway_passenger_rules"
):
    """
    Initializes a persistent ChromaDB collection.
    Uses Chroma's bundled all-MiniLM-L6-v2 ONNX embedding function (fast, local, free, zero-config).
    """
    client = chromadb.PersistentClient(path=db_path)

    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def push_chunks_to_chroma(
    chunks_path: str = "rhd_ingestion/output/final_chunks.json",
    db_path: str = "rhd_ingestion/chroma_db",
    collection_name: str = "railway_passenger_rules",
    batch_size: int = 50
) -> int:
    """
    Reads chunks and upserts them into ChromaDB in batches.
    """
    chunks_file = Path(chunks_path)
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found at: {chunks_file}. Run run_pipeline.py first.")

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks: List[Dict[str, Any]] = json.load(f)

    logger.info(f"Loaded {len(chunks)} chunks from {chunks_file}")
    collection = get_chroma_collection(db_path=db_path, collection_name=collection_name)

    ids = []
    documents = []
    metadatas = []

    for c in chunks:
        ids.append(c["id"])
        documents.append(c["text"])
        meta = c["metadata"].copy()
        
        if meta.get("page") is None:
            meta["page"] = -1  
        metadatas.append(meta)

    # Upsert in batches to avoid memory/IPC spikes
    total_added = 0
    for i in range(0, len(chunks), batch_size):
        b_ids = ids[i:i + batch_size]
        b_docs = documents[i:i + batch_size]
        b_metas = metadatas[i:i + batch_size]

        collection.upsert(
            ids=b_ids,
            documents=b_docs,
            metadatas=b_metas
        )
        total_added += len(b_ids)
        logger.info(f"  Upserted {total_added}/{len(chunks)} chunks into ChromaDB...")

    logger.info(f"SUCCESS: {total_added} vectors indexed in ChromaDB at {db_path} (Collection: '{collection_name}')")
    return total_added


def search_chroma(
    query: str,
    k: int = 3,
    language_filter: Optional[str] = None,
    db_path: str = "rhd_ingestion/chroma_db",
    collection_name: str = "railway_passenger_rules"
):
    """
    Performs cosine similarity search on the ChromaDB collection.
    """
    collection = get_chroma_collection(db_path=db_path, collection_name=collection_name)
    where_clause = {"language": language_filter} if language_filter else None

    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where_clause
    )
    return results


if __name__ == "__main__":
    push_chunks_to_chroma()
