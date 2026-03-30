"""
pipeline/retriever.py
---------------------
Hybrid search: BM25 (keyword) + ChromaDB cosine similarity (semantic).
Results are merged using Reciprocal Rank Fusion (RRF) for best recall.
"""
import os
from typing import List, Dict, Any, Tuple

from rank_bm25 import BM25Okapi
import ollama
from dotenv import load_dotenv

from pipeline.embedder import get_collection, embed_text  # noqa: E402

load_dotenv()

TOP_K = int(os.getenv("TOP_K_CHUNKS", "5"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# RRF constant (standard: 60)
RRF_K = 60


def _tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer for BM25."""
    return text.lower().split()


def _rrf_score(rank: int) -> float:
    """Reciprocal Rank Fusion score for a given rank (1-indexed)."""
    return 1.0 / (RRF_K + rank)


def hybrid_search(query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Perform hybrid retrieval:
    1. Semantic search using ChromaDB + nomic-embed-text embedding
    2. BM25 keyword search over all stored documents
    3. Merge scores with Reciprocal Rank Fusion

    Args:
        query: User's natural language question.
        top_k: Number of top chunks to return.

    Returns:
        List of chunk dicts with keys: text, metadata, score, similarity_score
    """
    collection = get_collection()

    # ── Fetch all documents for BM25 ─────────────────────────────────────────
    all_results = collection.get(include=["documents", "metadatas"])
    all_docs = all_results.get("documents", [])
    all_meta = all_results.get("metadatas", [])
    all_ids = all_results.get("ids", [])

    if not all_docs:
        return []

    # ── Semantic Search ───────────────────────────────────────────────────────
    query_embedding = embed_text(query)
    n_results = min(top_k * 2, len(all_docs))  # over-fetch for RRF

    semantic_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    semantic_ids = semantic_results["ids"][0]
    semantic_distances = semantic_results["distances"][0]

    # Convert cosine distance → similarity (ChromaDB returns cosine distance: 0=identical)
    semantic_scores: Dict[str, float] = {
        chunk_id: 1.0 - dist
        for chunk_id, dist in zip(semantic_ids, semantic_distances)
    }

    # ── BM25 Search ───────────────────────────────────────────────────────────
    tokenized_corpus = [_tokenize(doc) for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores_raw = bm25.get_scores(_tokenize(query))

    # Rank all documents by BM25 score
    bm25_ranked: List[Tuple[str, float]] = sorted(
        zip(all_ids, bm25_scores_raw), key=lambda x: x[1], reverse=True
    )
    bm25_ranks: Dict[str, int] = {
        chunk_id: rank + 1 for rank, (chunk_id, _) in enumerate(bm25_ranked)
    }
    bm25_score_map: Dict[str, float] = {
        chunk_id: score for chunk_id, score in bm25_ranked
    }

    # ── Reciprocal Rank Fusion ────────────────────────────────────────────────
    semantic_ranked = sorted(semantic_scores.keys(), key=lambda cid: semantic_scores[cid], reverse=True)
    semantic_ranks: Dict[str, int] = {cid: rank + 1 for rank, cid in enumerate(semantic_ranked)}

    all_candidate_ids = set(semantic_ids) | set(all_ids[:n_results])

    rrf_scores: Dict[str, float] = {}
    for cid in all_candidate_ids:
        s_rank = semantic_ranks.get(cid, n_results + 1)
        b_rank = bm25_ranks.get(cid, len(all_ids) + 1)
        rrf_scores[cid] = _rrf_score(s_rank) + _rrf_score(b_rank)

    top_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

    # ── Assemble Results ──────────────────────────────────────────────────────
    id_to_doc = dict(zip(all_ids, all_docs))
    id_to_meta = dict(zip(all_ids, all_meta))

    results = []
    for cid in top_ids:
        if cid not in id_to_doc:
            continue
        sim_score = semantic_scores.get(cid, 0.0)
        bm25_raw = bm25_score_map.get(cid, 0.0)
        results.append({
            "chunk_id": cid,
            "text": id_to_doc[cid],
            "metadata": id_to_meta[cid],
            "rrf_score": rrf_scores[cid],
            "similarity_score": sim_score,
            "bm25_score": bm25_raw,
        })

    return results
