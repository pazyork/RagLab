"""
Text splitting utilities for RAG applications.
Provides multiple strategies for splitting text into chunks with configurable parameters.
"""

from typing import List


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


def split_by_recursive(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[str]:
    """
    Split text recursively using separator priority: paragraphs → sentences → characters.

    Separator priority: ["\n\n", "\n", "。", ".", "，", ",", " "]
    Overlap only applies to the final character-level split.

    Args:
        text: Input text to split
        chunk_size: Maximum number of characters per chunk
        chunk_overlap: Number of overlapping characters for final char-level split

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

    # If text is already short enough, return as single chunk
    if len(text) <= chunk_size:
        return [text]

    # Separator priority order
    separators = ["\n\n", "\n", "。", ".", "！", "!", "？", "?", "，", ",", " "]

    def _split_recursive(text: str, sep_idx: int = 0) -> List[str]:
        """Recursive helper function"""
        # If we've tried all separators, fall back to char split with overlap
        if sep_idx >= len(separators):
            return split_by_char(text, chunk_size, chunk_overlap)

        separator = separators[sep_idx]
        splits = text.split(separator)

        # Process splits: keep individual splits that are <= chunk_size,
        # recursively split those that are too big
        processed = []
        for i, split in enumerate(splits):
            if not split:
                continue

            # Add separator back except for the last split
            if i < len(splits) - 1:
                split_with_sep = split + separator
            else:
                split_with_sep = split

            if len(split_with_sep) <= chunk_size:
                processed.append(split_with_sep)
            else:
                # Too big, recurse with next separator
                nested_chunks = _split_recursive(split_with_sep, sep_idx + 1)
                processed.extend(nested_chunks)

        # For paragraph/line level separators, don't merge chunks aggressively
        # For lower level separators (punctuation, space), merge smaller chunks
        if sep_idx < 2:  # "\n\n" and "\n" are high level separators, keep as separate as possible
            return processed

        # For lower level separators, merge small adjacent chunks
        merged = []
        current = ""

        for chunk in processed:
            if len(current) + len(chunk) <= chunk_size:
                current += chunk
            else:
                if current:
                    merged.append(current)
                current = chunk

        if current:
            merged.append(current)

        return merged

    return _split_recursive(text)
