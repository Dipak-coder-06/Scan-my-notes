"""
pipeline/chunker.py
--------------------
Smart Section chunking: groups OCR words into context-preserving chunks
based on headers, tables, page breaks, and visual whitespace gaps.
"""
from typing import List, Dict, Any, Optional
import re
from modules.visual_parser import is_table_region, words_to_markdown_table, extract_diagram_labels  # noqa: E402


# ── Constants ──────────────────────────────────────────────────────────────────

# Height threshold (pixels) above which a word is considered a "header"
HEADER_HEIGHT_THRESHOLD = 28

# Vertical gap (pixels) between word groups that triggers a new chunk
VERTICAL_GAP_THRESHOLD = 45

# Minimum characters for a chunk to be stored
MIN_CHUNK_CHARS = 20

# Maximum characters per chunk (soft limit)
MAX_CHUNK_CHARS = 1500


# ── Utilities ──────────────────────────────────────────────────────────────────

def _is_header_word(word: Dict[str, Any]) -> bool:
    """Heuristic: tall bounding box → larger font → likely a section header."""
    return word["bbox"]["h"] >= HEADER_HEIGHT_THRESHOLD


def _words_to_text(words: List[Dict[str, Any]]) -> str:
    """Concatenate word texts into a single string with spaces."""
    return " ".join(w["text"] for w in words)


def _get_page_range(words: List[Dict[str, Any]]) -> tuple:
    """Return (min_page, max_page) for a list of words."""
    pages = [w["page"] for w in words]
    return min(pages), max(pages)


def _get_bboxes(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return bounding boxes for all words in the chunk."""
    return [w["bbox"] for w in words]


# ── Core Chunking Logic ────────────────────────────────────────────────────────

def _split_into_groups(words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Step 1: Split word stream into groups based on:
      - Page breaks (different page number)
      - Large vertical gaps (whitespace between sections)
    """
    if not words:
        return []

    groups: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = [words[0]]

    for prev, curr in zip(words, words[1:]):
        page_break = curr["page"] != prev["page"]
        vertical_gap = (
            curr["bbox"]["y"] - (prev["bbox"]["y"] + prev["bbox"]["h"])
            > VERTICAL_GAP_THRESHOLD
        )
        if page_break or vertical_gap:
            groups.append(current_group)
            current_group = [curr]
        else:
            current_group.append(curr)

    if current_group:
        groups.append(current_group)

    return groups


def _detect_section_title(group: List[Dict[str, Any]]) -> Optional[str]:
    """
    Look for header words at the start of a group.
    Returns the concatenated header text, or None.
    """
    header_words = []
    for word in group:
        if _is_header_word(word):
            header_words.append(word)
        else:
            break  # headers are at the top

    if header_words:
        return _words_to_text(header_words)
    return None


def _build_chunk(
    words: List[Dict[str, Any]],
    section_title: Optional[str],
    chunk_index: int,
    content_override: Optional[str] = None,
    is_table: bool = False,
) -> Dict[str, Any]:
    """Assemble a single chunk dict with all metadata."""
    page_start, page_end = _get_page_range(words)
    text = content_override if content_override else _words_to_text(words)

    return {
        "chunk_id": f"chunk_{chunk_index:04d}",
        "text": text,
        "section_title": section_title or "Untitled Section",
        "page_start": page_start,
        "page_end": page_end,
        "bboxes": _get_bboxes(words),
        "is_table": is_table,
        "word_count": len(words),
    }


def chunk_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Main chunking entry point.

    Args:
        words: List of word objects from ingest.py (with text, page, bbox).

    Returns:
        List of chunk dicts ready for embedding.
    """
    # Sort words: page → y → x (reading order)
    sorted_words = sorted(words, key=lambda w: (w["page"], w["bbox"]["y"], w["bbox"]["x"]))

    groups = _split_into_groups(sorted_words)

    chunks: List[Dict[str, Any]] = []
    chunk_idx = 0
    current_section = "Introduction"

    for group in groups:
        if not group:
            continue

        # Detect section title from this group's header words
        detected_title = _detect_section_title(group)
        if detected_title:
            current_section = detected_title

        # Check if this group looks like a table
        if is_table_region(group):
            md_table = words_to_markdown_table(group)
            chunk = _build_chunk(
                group,
                section_title=current_section,
                chunk_index=chunk_idx,
                content_override=md_table,
                is_table=True,
            )
            if len(chunk["text"]) >= MIN_CHUNK_CHARS:
                chunks.append(chunk)
                chunk_idx += 1
            continue

        # Check for diagram labels
        diagram_text = extract_diagram_labels(group)
        if diagram_text and len(group) < 15:
            chunk = _build_chunk(
                group,
                section_title=current_section,
                chunk_index=chunk_idx,
                content_override=diagram_text,
            )
            if len(chunk["text"]) >= MIN_CHUNK_CHARS:
                chunks.append(chunk)
                chunk_idx += 1
            continue

        # Regular text: sub-chunk if too long
        text = _words_to_text(group)
        if len(text) <= MAX_CHUNK_CHARS:
            chunk = _build_chunk(group, current_section, chunk_idx)
            if len(chunk["text"]) >= MIN_CHUNK_CHARS:
                chunks.append(chunk)
                chunk_idx += 1
        else:
            # Split large groups into smaller text chunks
            step = MAX_CHUNK_CHARS // 6  # approximate words per chunk
            for i in range(0, len(group), step):
                sub_group = group[i: i + step]
                chunk = _build_chunk(sub_group, current_section, chunk_idx)
                if len(chunk["text"]) >= MIN_CHUNK_CHARS:
                    chunks.append(chunk)
                    chunk_idx += 1

    return chunks
