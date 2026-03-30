"""
modules/citation_engine.py
--------------------------
MODULE 1: Spatial Citation Engine (20% hackathon weight)
Builds precise "Found on Page X, Section Y" footers from chunk metadata.
"""
from typing import List, Dict, Any


def build_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build citation objects for each retrieved chunk.

    Args:
        retrieved_chunks: List of chunk dicts from retriever.py (each has 'metadata' key).

    Returns:
        List of citation dicts: {label, page_start, page_end, section_title, is_table}
    """
    citations = []
    seen = set()

    for i, chunk in enumerate(retrieved_chunks):
        meta = chunk.get("metadata", {})
        page_start = meta.get("page_start", "?")
        page_end = meta.get("page_end", "?")
        section = meta.get("section_title", "Untitled Section")
        is_table = str(meta.get("is_table", "False")).lower() == "true"

        # De-duplicate identical citations
        key = (page_start, section)
        if key in seen:
            continue
        seen.add(key)

        # Build human-readable label
        if page_start == page_end:
            page_label = f"Page {page_start}"
        else:
            page_label = f"Pages {page_start}–{page_end}"

        content_type = "📊 Table" if is_table else "📄 Text"

        label = f"{content_type} · {page_label} · Section: \"{section}\""

        citations.append({
            "label": label,
            "page_start": page_start,
            "page_end": page_end,
            "section_title": section,
            "is_table": is_table,
            "citation_index": i + 1,
        })

    return citations


def format_citation_footer(citations: List[Dict[str, Any]]) -> str:
    """
    Format citations as a human-readable footer for the answer.

    Returns:
        A multi-line string like:
        ---
        📍 Sources:
        [1] 📄 Text · Page 3 · Section: "Thermodynamics"
        [2] 📊 Table · Pages 5–6 · Section: "Data Summary"
    """
    if not citations:
        return ""

    lines = ["\n---\n📍 **Sources:**"]
    for c in citations:
        lines.append(f"  [{c['citation_index']}] {c['label']}")

    return "\n".join(lines)


def get_primary_citation(citations: List[Dict[str, Any]]) -> str:
    """Get the most specific primary citation string (used in answer header)."""
    if not citations:
        return ""
    c = citations[0]
    if c["page_start"] == c["page_end"]:
        return f"Page {c['page_start']}, Section \"{c['section_title']}\""
    return f"Pages {c['page_start']}–{c['page_end']}, Section \"{c['section_title']}\""
