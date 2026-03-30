"""
modules/veracity_guard.py
--------------------------
MODULE 2: Veracity & Confidence Guardrails (40% hackathon weight)

- Provides the strict grounding system prompt for the LLM
- Computes a confidence score (0-100%) from retrieval signals
"""
from typing import List, Dict, Any
import math


# ── System Prompt ──────────────────────────────────────────────────────────────

GROUNDING_SYSTEM_PROMPT = """You are a precise document assistant for "Ironclad Scholar."

STRICT RULES:
1. You ONLY answer based on the CONTEXT provided below. 
2. NEVER use your own training knowledge or make assumptions beyond the provided context.
3. If the answer is NOT present in the context, you MUST respond with exactly:
   "I don't have enough information in the provided notes to answer this question."
4. Do NOT speculate, infer, or extrapolate beyond what is explicitly stated.
5. Quote relevant phrases from the context when supporting your answer.
6. Respond in clear, concise language. Use bullet points if listing multiple items.

Remember: Accuracy over completeness. A short, correct answer beats a long, uncertain one."""


def get_system_prompt() -> str:
    """Return the grounding system prompt."""
    return GROUNDING_SYSTEM_PROMPT


def build_grounded_prompt(query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Build the full prompt for the LLM:
    - Context (from retrieved chunks, ordered by relevance)
    - User question

    Args:
        query: User's natural language question.
        retrieved_chunks: List of chunk dicts from retriever.py.

    Returns:
        A formatted string prompt.
    """
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks):
        meta = chunk.get("metadata", {})
        page = meta.get("page_start", "?")
        section = meta.get("section_title", "Unknown Section")
        is_table = str(meta.get("is_table", "False")).lower() == "true"
        content_type = "[TABLE]" if is_table else "[TEXT]"

        context_parts.append(
            f"--- SOURCE {i+1} {content_type} (Page {page}, Section: {section}) ---\n"
            f"{chunk['text']}\n"
        )

    context_block = "\n".join(context_parts)

    return f"""CONTEXT:
{context_block}

QUESTION: {query}

ANSWER:"""


def compute_confidence(retrieved_chunks: List[Dict[str, Any]]) -> int:
    """
    Compute a confidence score (0-100) based on retrieval quality signals:

    Factors:
        - Average cosine similarity of top chunks (primary signal)
        - BM25 score normalization (keyword overlap signal)
        - Number of chunks retrieved (coverage signal)

    Returns:
        Integer confidence score between 0 and 100.
    """
    if not retrieved_chunks:
        return 0

    # ── 1. Similarity Score (0-1 range, weight: 60%) ──────────────────────────
    sim_scores = [c.get("similarity_score", 0.0) for c in retrieved_chunks]
    avg_sim = sum(sim_scores) / len(sim_scores) if sim_scores else 0.0
    # Cosine similarity from nomic-embed-text: ~0.3 = poor, ~0.7+ = excellent
    # Normalize to 0-1: clamp and rescale from [0.2, 0.85] range
    sim_normalized = max(0.0, min(1.0, (avg_sim - 0.2) / 0.65))

    # ── 2. BM25 Score (weight: 25%) ───────────────────────────────────────────
    bm25_scores = [c.get("bm25_score", 0.0) for c in retrieved_chunks]
    max_bm25 = max(bm25_scores) if bm25_scores else 0.0
    # BM25 scores vary widely; use log-normalization
    bm25_normalized = min(1.0, math.log1p(max_bm25) / 5.0) if max_bm25 > 0 else 0.0

    # ── 3. Coverage (weight: 15%) ─────────────────────────────────────────────
    coverage = min(1.0, len(retrieved_chunks) / 3.0)  # 3+ chunks = full coverage

    # ── Weighted Composite ────────────────────────────────────────────────────
    raw_confidence = (
        0.60 * sim_normalized +
        0.25 * bm25_normalized +
        0.15 * coverage
    )

    return round(raw_confidence * 100)


def confidence_label(score: int) -> tuple:
    """
    Return (label, color) for a confidence score.

    Returns:
        (label: str, color: str) where color is a CSS hex color.
    """
    if score >= 70:
        return ("High Confidence", "#22c55e")   # green
    elif score >= 40:
        return ("Moderate Confidence", "#f59e0b")  # amber
    else:
        return ("Low Confidence", "#ef4444")    # red


def is_no_information_response(answer: str) -> bool:
    """Check if the LLM responded with the 'no information' signal."""
    return "i don't have enough information" in answer.lower()
