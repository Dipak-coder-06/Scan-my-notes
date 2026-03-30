"""
modules/visual_parser.py
------------------------
Detects handwritten tables and diagrams from OCR word objects.
Converts table data into Markdown before embedding so the LLM
can properly understand data relationships.
"""
from typing import List, Dict, Any, Optional
import re


# ── Table Detection ────────────────────────────────────────────────────────────

def _cluster_words_by_row(words: List[Dict[str, Any]], row_tolerance: int = 15) -> List[List[Dict[str, Any]]]:
    """
    Group words into horizontal rows based on their Y coordinates.
    Words within `row_tolerance` pixels of each other are in the same row.
    """
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: w["bbox"]["y"])
    rows: List[List[Dict[str, Any]]] = []
    current_row: List[Dict[str, Any]] = [sorted_words[0]]
    current_y = sorted_words[0]["bbox"]["y"]

    for word in sorted_words[1:]:
        if abs(word["bbox"]["y"] - current_y) <= row_tolerance:
            current_row.append(word)
        else:
            rows.append(sorted(current_row, key=lambda w: w["bbox"]["x"]))
            current_row = [word]
            current_y = word["bbox"]["y"]

    if current_row:
        rows.append(sorted(current_row, key=lambda w: w["bbox"]["x"]))

    return rows


def _detect_column_boundaries(rows: List[List[Dict[str, Any]]], x_gap_threshold: int = 40) -> List[int]:
    """
    Find column X boundaries by looking for consistent gaps between words across rows.
    Returns a list of X-break positions.
    """
    all_x_gaps = []
    for row in rows:
        for i in range(len(row) - 1):
            gap_start = row[i]["bbox"]["x"] + row[i]["bbox"]["w"]
            gap_end = row[i + 1]["bbox"]["x"]
            gap = gap_end - gap_start
            if gap >= x_gap_threshold:
                all_x_gaps.append((gap_start + gap_end) // 2)

    # Cluster gap positions
    if not all_x_gaps:
        return []

    all_x_gaps.sort()
    boundaries = [all_x_gaps[0]]
    for x in all_x_gaps[1:]:
        if x - boundaries[-1] > x_gap_threshold:
            boundaries.append(x)
        else:
            boundaries[-1] = (boundaries[-1] + x) // 2  # merge close boundaries

    return boundaries


def _words_in_rows_to_cells(rows: List[List[Dict[str, Any]]], col_boundaries: List[int]) -> List[List[str]]:
    """
    Assign words to columns based on X position relative to column boundaries.
    Returns a 2D list of cell strings.
    """
    num_cols = len(col_boundaries) + 1
    table: List[List[str]] = []

    for row in rows:
        cells = [""] * num_cols
        for word in row:
            word_x = word["bbox"]["x"]
            col_idx = 0
            for boundary in col_boundaries:
                if word_x > boundary:
                    col_idx += 1
            cells[col_idx] = (cells[col_idx] + " " + word["text"]).strip()
        table.append(cells)

    return table


def is_table_region(words: List[Dict[str, Any]], min_rows: int = 2, min_cols: int = 2) -> bool:
    """
    Heuristic: a block of words is a table if it has >= min_rows distinct Y-rows
    AND consistent column boundaries across multiple rows.
    """
    if len(words) < min_rows * min_cols:
        return False

    rows = _cluster_words_by_row(words)
    if len(rows) < min_rows:
        return False

    col_boundaries = _detect_column_boundaries(rows)
    return len(col_boundaries) >= (min_cols - 1)


def words_to_markdown_table(words: List[Dict[str, Any]]) -> str:
    """
    Convert a block of OCR words (from a table region) into a Markdown table string.

    Returns:
        A Markdown table string, e.g.:
        | Name | Score |
        | ---- | ----- |
        | Alice | 95   |
    """
    rows = _cluster_words_by_row(words)
    col_boundaries = _detect_column_boundaries(rows)
    table_data = _words_in_rows_to_cells(rows, col_boundaries)

    if not table_data:
        return " ".join(w["text"] for w in words)

    # Build Markdown
    md_lines = []
    header = table_data[0]
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in table_data[1:]:
        # Pad row to match header column count
        padded = row + [""] * (len(header) - len(row))
        md_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

    return "\n".join(md_lines)


# ── Diagram / Label Detection ──────────────────────────────────────────────────

def extract_diagram_labels(words: List[Dict[str, Any]]) -> Optional[str]:
    """
    For regions that look like diagrams (isolated text labels spread around),
    collect them as a structured text block with spatial hints.
    Returns None if not enough labels detected.
    """
    if len(words) < 3:
        return None

    # Sort labels: top-to-bottom, left-to-right
    sorted_labels = sorted(words, key=lambda w: (w["bbox"]["y"], w["bbox"]["x"]))
    label_texts = [w["text"] for w in sorted_labels]

    # Only treat as diagram labels if words are spread out (low word density)
    if len(words) < 15:
        return "[Diagram Labels]: " + ", ".join(label_texts)
    return None
