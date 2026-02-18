"""Text chunking utilities for RAG pipelines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    """A text chunk with metadata for indexing."""

    id: str
    content: str
    document_id: str
    chunk_index: int
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict | None = None


def chunk_text(
    text: str,
    document_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separator: str = "\n\n",
) -> list[Chunk]:
    """Split text into overlapping chunks.

    Uses paragraph boundaries when possible, falling back to
    character-level splitting for long paragraphs.
    """
    if not text.strip():
        return []

    # Ensure overlap is less than chunk_size to guarantee progress
    chunk_overlap = min(chunk_overlap, chunk_size - 1)

    paragraphs = [p.strip() for p in text.split(separator) if p.strip()]
    chunks: list[Chunk] = []
    current = ""
    chunk_idx = 0

    for para in paragraphs:
        # If adding this paragraph exceeds chunk_size, finalize current chunk
        if current and len(current) + len(para) + len(separator) > chunk_size:
            chunks.append(
                Chunk(
                    id=f"{document_id}-{chunk_idx:04d}",
                    content=current.strip(),
                    document_id=document_id,
                    chunk_index=chunk_idx,
                )
            )
            chunk_idx += 1
            # Keep overlap from the end of the current chunk
            if chunk_overlap > 0 and len(current) > chunk_overlap:
                current = current[-chunk_overlap:]
            else:
                current = ""

        if len(para) > chunk_size:
            # Split oversized paragraphs at character level
            if current:
                chunks.append(
                    Chunk(
                        id=f"{document_id}-{chunk_idx:04d}",
                        content=current.strip(),
                        document_id=document_id,
                        chunk_index=chunk_idx,
                    )
                )
                chunk_idx += 1
                current = ""

            for i in range(0, len(para), chunk_size - chunk_overlap):
                segment = para[i : i + chunk_size]
                chunks.append(
                    Chunk(
                        id=f"{document_id}-{chunk_idx:04d}",
                        content=segment.strip(),
                        document_id=document_id,
                        chunk_index=chunk_idx,
                    )
                )
                chunk_idx += 1
        else:
            current = f"{current}{separator}{para}" if current else para

    # Don't forget the last chunk
    if current.strip():
        chunks.append(
            Chunk(
                id=f"{document_id}-{chunk_idx:04d}",
                content=current.strip(),
                document_id=document_id,
                chunk_index=chunk_idx,
            )
        )

    return chunks
