"""
pipeline/generator.py
---------------------
Offline answer generation using Ollama (llama3.2, temperature=0.0).
Combines veracity guardrails, confidence scoring, and citation building.
"""
import os
from typing import List, Dict, Any, Tuple

import ollama
from dotenv import load_dotenv

from modules.veracity_guard import (
    get_system_prompt,
    build_grounded_prompt,
    compute_confidence,
    confidence_label,
    is_no_information_response,
)
from modules.citation_engine import build_citations, format_citation_footer

load_dotenv()

LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def generate_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate a grounded answer using Ollama.

    Args:
        query: User's question.
        retrieved_chunks: Top-k results from retriever.py.

    Returns:
        Dict with keys:
            - answer: str (the LLM response)
            - confidence: int (0-100)
            - confidence_label: str
            - confidence_color: str
            - citations: list of citation dicts
            - citation_footer: str
            - no_information: bool
    """
    if not retrieved_chunks:
        return {
            "answer": "I don't have enough information in the provided notes to answer this question.",
            "confidence": 0,
            "confidence_label": "Low Confidence",
            "confidence_color": "#ef4444",
            "citations": [],
            "citation_footer": "",
            "no_information": True,
        }

    client = ollama.Client(host=OLLAMA_BASE_URL)

    system_prompt = get_system_prompt()
    user_prompt = build_grounded_prompt(query, retrieved_chunks)

    try:
        response = client.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={
                "temperature": 0.0,
                "num_predict": 512,
                "top_k": 1,
            },
            keep_alive=0,   # unload llama3.2 immediately after generation
        )
        answer = response["message"]["content"].strip()
    except Exception as e:
        answer = f"Error generating answer: Local LLM ({LLM_MODEL}) encountered an issue (likely out of memory). Details: {e}"
        return {
            "answer": answer,
            "confidence": 0,
            "confidence_label": "Error",
            "confidence_color": "#ef4444",
            "citations": [],
            "citation_footer": "",
            "no_information": True,
        }

    # Confidence
    confidence_score = compute_confidence(retrieved_chunks)
    label, color = confidence_label(confidence_score)

    # If the LLM still hallucinated (confidence < 15%), override
    if confidence_score < 15 and not is_no_information_response(answer):
        answer = "I don't have enough information in the provided notes to answer this question."
        confidence_score = 0
        label, color = confidence_label(0)

    # Citations
    citations = build_citations(retrieved_chunks)
    citation_footer = format_citation_footer(citations)
    no_info = is_no_information_response(answer)

    return {
        "answer": answer,
        "confidence": confidence_score,
        "confidence_label": label,
        "confidence_color": color,
        "citations": citations,
        "citation_footer": citation_footer,
        "no_information": no_info,
    }


def stream_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
):
    """
    Generator that streams the LLM answer token by token.
    Yields string tokens. Does NOT include citations (use generate_answer for those).
    """
    if not retrieved_chunks:
        yield "I don't have enough information in the provided notes to answer this question."
        return

    client = ollama.Client(host=OLLAMA_BASE_URL)
    system_prompt = get_system_prompt()
    user_prompt = build_grounded_prompt(query, retrieved_chunks)

    stream = client.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": 0.0, "top_k": 1},
        keep_alive=0,   # unload after streaming
        stream=True,
    )

    for chunk in stream:
        token = chunk["message"]["content"]
        if token:
            yield token
