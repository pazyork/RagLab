"""
Text splitting utilities for RAG applications.
Provides multiple strategies for splitting text into chunks with configurable parameters.
"""

import re
from typing import List, Optional, Dict, Any, Tuple


# ── Separator presets ──────────────────────────────────────────────────────

DEFAULT_SEPARATORS = [
    "\n\n",   # paragraphs
    "\n",     # lines
    "。",     # Chinese period
    ".",      # English period
    "！",     # Chinese exclamation
    "!",      # English exclamation
    "？",     # Chinese question
    "?",      # English question
    "；",     # Chinese semicolon
    ";",      # English semicolon
    "，",     # Chinese comma
    ",",      # English comma
    " ",      # space
    "",       # character-level fallback
]

# Markdown headers from level 1 to level 6
MARKDOWN_HEADERS = ["# ", "## ", "### ", "#### ", "##### ", "###### "]


# ── Utility: deduplicate while preserving order ────────────────────────────

def _deduplicate(chunks: List[str]) -> List[str]:
    """Remove duplicate chunks, preserving first occurrence order."""
    seen = set()
    result = []
    for c in chunks:
        key = c.strip()
        if key and key not in seen:
            seen.add(key)
            result.append(c)
    return result


# ── Strategy 1: Split by lines ─────────────────────────────────────────────

def split_lines(text: str) -> List[str]:
    """
    Split text by lines and filter out empty lines.

    Args:
        text: Input text to split

    Returns:
        List of non-empty lines
    """
    if not text.strip():
        return []

    lines = text.splitlines()
    return [line.strip() for line in lines if line.strip()]


# ── Strategy 2: Fixed character size ───────────────────────────────────────

def split_by_char(text: str, chunk_size: int = 512, overlap: int = 0) -> List[str]:
    """
    Split text into chunks using fixed character size sliding window.

    Args:
        text: Input text to split
        chunk_size: Maximum number of characters per chunk
        overlap: Number of overlapping characters between consecutive chunks

    Returns:
        List of text chunks
    """
    if not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    chunks = []
    start = 0
    text_length = len(text)
    step = chunk_size - overlap

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += step

    return chunks


# ── Strategy 3: Recursive character splitting ──────────────────────────────

def split_by_recursive(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    separators: Optional[List[str]] = None,
    dedup: bool = False,
) -> List[str]:
    """
    Split text recursively using a hierarchy of separators.

    Algorithm:
      1. Try separators in order of priority (coarse → fine).
      2. If a split exceeds chunk_size, recurse with the next finer separator.
      3. When all separators are exhausted, fall back to character-level
         sliding window with overlap.

    Args:
        text: Input text to split
        chunk_size: Maximum number of characters per chunk
        chunk_overlap: Overlap characters for final char-level fallback
        separators: Ordered list of separator strings. Defaults to a
            language-agnostic set suitable for Chinese + English mixed text.
        dedup: If True, remove duplicate chunks preserving order.

    Returns:
        List of text chunks
    """
    if not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    if len(text) <= chunk_size:
        return [text]

    seps = separators if separators is not None else DEFAULT_SEPARATORS

    # Pre-filter separators: keep only those actually present in the text.
    # The last separator ("" for char-level) is always kept.
    active_seps = []
    for s in seps:
        if s == "" or s in text:
            active_seps.append(s)
    if not active_seps:
        active_seps = [""]

    def _merge_small_chunks(chunks: List[str]) -> List[str]:
        """Merge adjacent chunks while keeping each under chunk_size."""
        merged: List[str] = []
        current = ""
        for chunk in chunks:
            if len(current) + len(chunk) <= chunk_size:
                current += chunk
            else:
                if current:
                    merged.append(current)
                current = chunk
        if current:
            merged.append(current)
        return merged

    def _split(text_sub: str, sep_idx: int) -> List[str]:
        """Recursive helper."""
        if len(text_sub) <= chunk_size:
            return [text_sub]

        if sep_idx >= len(active_seps):
            # All separators exhausted → char-level with overlap
            return split_by_char(text_sub, chunk_size, chunk_overlap)

        sep = active_seps[sep_idx]
        if sep == "":
            return split_by_char(text_sub, chunk_size, chunk_overlap)

        # Split by current separator
        parts = text_sub.split(sep)

        # Process each part
        good: List[str] = []
        for i, part in enumerate(parts):
            if not part:
                continue
            # Re-attach separator except for the last split
            piece = part + sep if i < len(parts) - 1 else part
            if len(piece) <= chunk_size:
                good.append(piece)
            else:
                # Flush good buffer first so oversized pieces don't pollute merges
                if good:
                    good = _merge_small_chunks(good)
                # Recurse into oversized piece
                nested = _split(piece, sep_idx + 1)
                if good:
                    # See if last merged chunk + first nested can combine
                    last = good[-1]
                    first = nested[0] if nested else ""
                    if first and len(last) + len(first) <= chunk_size:
                        good[-1] = last + first
                        nested = nested[1:]
                    good.extend(nested)
                else:
                    good = nested

        # Final merge pass
        return _merge_small_chunks(good)

    result = _split(text, 0)
    if dedup:
        result = _deduplicate(result)
    return result


# ── Strategy 4: Markdown-aware splitting ───────────────────────────────────

def split_by_markdown(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: int = 50,
    headers: Optional[List[Tuple[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Split Markdown text by header hierarchy.

    First pass: group content under each header path.
    Second pass (optional): if chunk_size is set, further split oversized
    groups using recursive character splitting; each resulting chunk inherits
    the header metadata.

    Args:
        text: Markdown source text
        chunk_size: If provided, split oversized sections recursively.
        chunk_overlap: Overlap for recursive fallback splits.
        headers: Ordered list of (header_marker, metadata_key).
            Defaults to standard Markdown H1–H6.
            Example: [("# ", "H1"), ("## ", "H2")]

    Returns:
        List of dicts with keys:
            - "content": str  (the chunk text)
            - "metadata": dict (header path, e.g. {"H1": "Title", "H2": "Sub"})
    """
    if not text.strip():
        return []

    hdrs = headers if headers is not None else [
        ("# ", "H1"), ("## ", "H2"), ("### ", "H3"),
        ("#### ", "H4"), ("##### ", "H5"), ("###### ", "H6"),
    ]

    lines = text.splitlines()
    result: List[Dict[str, Any]] = []
    current_meta: Dict[str, str] = {}
    current_lines: List[str] = []

    def _flush():
        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                result.append({"content": content, "metadata": dict(current_meta)})
            current_lines.clear()

    for line in lines:
        is_header = False
        for marker, key in hdrs:
            if line.startswith(marker):
                _flush()
                # Update metadata: set this level and clear deeper levels
                current_meta[key] = line[len(marker):].strip()
                # Clear any deeper headers
                clear = False
                for _, k in hdrs:
                    if clear and k in current_meta:
                        del current_meta[k]
                    if k == key:
                        clear = True
                is_header = True
                break
        if not is_header:
            current_lines.append(line)

    _flush()

    # Optional second pass: split oversized sections while preserving metadata
    if chunk_size and chunk_size > 0:
        final: List[Dict[str, Any]] = []
        for item in result:
            if len(item["content"]) <= chunk_size:
                final.append(item)
            else:
                sub_chunks = split_by_recursive(
                    item["content"],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                for sc in sub_chunks:
                    final.append({"content": sc, "metadata": dict(item["metadata"])})
        return final

    return result


# ── Unified splitter interface ─────────────────────────────────────────────

SPLITTER_MODES = ["lines", "char", "recursive", "markdown"]


def split_text(
    text: str,
    mode: str = "recursive",
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    **kwargs,
) -> List[str]:
    """
    Unified text splitting entry point.

    Args:
        text: Input text
        mode: One of "lines", "char", "recursive", "markdown"
        chunk_size: Target chunk size (characters)
        chunk_overlap: Overlap for sliding-window strategies
        **kwargs: Extra args forwarded to the underlying splitter
            (e.g. separators=..., dedup=..., headers=...)

    Returns:
        List of chunk strings. For "markdown" mode, metadata is dropped;
        use split_by_markdown() directly if you need metadata.
    """
    if mode == "lines":
        return split_lines(text)
    if mode == "char":
        return split_by_char(text, chunk_size, chunk_overlap)
    if mode == "recursive":
        return split_by_recursive(text, chunk_size, chunk_overlap, **kwargs)
    if mode == "markdown":
        chunks = split_by_markdown(text, chunk_size, chunk_overlap, **kwargs)
        return [c["content"] for c in chunks]

    raise ValueError(f"Unknown split mode: {mode}. Choose from {SPLITTER_MODES}")
