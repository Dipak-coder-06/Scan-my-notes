"""
pipeline/embedder.py
--------------------
Embeds chunks using Ollama nomic-embed-text and stores them in ChromaDB (local, persistent).
"""
import os
import time
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
import ollama
from dotenv import load_dotenv

load_dotenv()

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
COLLECTION_NAME = "ironclad_scholar"


def _get_chroma_client() -> chromadb.PersistentClient:
    """Get or create a persistent ChromaDB client."""
    return chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


def _get_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """Get or create the ChromaDB collection."""
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_text(text: str) -> List[float]:
    """
    Embed a single text string using Ollama nomic-embed-text.
    Uses keep_alive=0 so the model is unloaded immediately after use,
    freeing RAM for the LLM generation step.
    Retries up to 3 times with backoff on transient failures.
    """
    client = ollama.Client(host=OLLAMA_BASE_URL)
    last_err = None
    for attempt in range(3):
        try:
            response = client.embeddings(
                model=EMBED_MODEL,
                prompt=text,
                keep_alive=0,   # unload immediately after embedding
            )
            return response["embedding"]
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1s, 2s backoff
    raise RuntimeError(
        f"Embedding failed after 3 attempts: {last_err}\n"
        "Tip: Ollama may be out of memory. Try restarting Ollama."
    )


def store_chunks(chunks: List[Dict[str, Any]], progress_callback=None) -> int:
    """
    Embed all chunks and upsert them into ChromaDB.

    Args:
        chunks: List of chunk dicts from chunker.py.
        progress_callback: Optional callable(current, total).

    Returns:
        Number of chunks stored.
    """
    chroma_client = _get_chroma_client()
    collection = _get_collection(chroma_client)

    total = len(chunks)
    stored = 0

    for i, chunk in enumerate(chunks):
        text = chunk["text"]
        if not text.strip():
            continue

        embedding = embed_text(text)

        # Metadata stored alongside vector (must be strings/ints/floats for ChromaDB)
        metadata = {
            "chunk_id": chunk["chunk_id"],
            "section_title": chunk["section_title"],
            "page_start": chunk["page_start"],
            "page_end": chunk["page_end"],
            "is_table": str(chunk.get("is_table", False)),
            "word_count": chunk.get("word_count", 0),
        }

        collection.upsert(
            ids=[chunk["chunk_id"]],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        stored += 1

        if progress_callback:
            progress_callback(i + 1, total)

    return stored


def get_collection():
    """Return the ChromaDB collection for querying."""
    client = _get_chroma_client()
    return _get_collection(client)


def clear_collection():
    """Delete and recreate the collection (for re-ingesting a new document)."""
    client = _get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return _get_collection(client)
