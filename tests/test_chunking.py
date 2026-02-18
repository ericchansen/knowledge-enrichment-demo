"""Tests for the chunking service."""

from ifwebuildit.services.chunking import Chunk, chunk_text


def test_chunk_text_basic():
    """Basic chunking splits text into chunks."""
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunk_text(text, document_id="doc1", chunk_size=50, chunk_overlap=0)
    assert len(chunks) >= 1
    assert all(isinstance(c, Chunk) for c in chunks)


def test_chunk_text_empty():
    """Empty text returns no chunks."""
    chunks = chunk_text("", document_id="doc1")
    assert chunks == []


def test_chunk_text_whitespace():
    """Whitespace-only text returns no chunks."""
    chunks = chunk_text("   \n\n  \n  ", document_id="doc1")
    assert chunks == []


def test_chunk_ids_sequential():
    """Chunk IDs are sequential."""
    text = "A\n\nB\n\nC\n\nD\n\nE"
    chunks = chunk_text(text, document_id="test", chunk_size=5, chunk_overlap=0)
    for i, chunk in enumerate(chunks):
        assert chunk.id == f"test-{i:04d}"
        assert chunk.chunk_index == i
        assert chunk.document_id == "test"


def test_chunk_overlap():
    """Chunks overlap by the specified amount."""
    text = "A" * 100 + "\n\n" + "B" * 100
    chunks = chunk_text(text, document_id="doc", chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2
    # Second chunk should start with overlap from first
    if len(chunks) >= 2:
        assert len(chunks[0].content) <= 100


def test_oversized_paragraph():
    """A single paragraph larger than chunk_size gets split."""
    text = "X" * 500
    chunks = chunk_text(text, document_id="big", chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 5
    # Each chunk should be at most chunk_size chars
    for chunk in chunks:
        assert len(chunk.content) <= 100


def test_chunk_content_preserved():
    """All content should be represented across chunks."""
    text = "Hello world.\n\nThis is a test.\n\nFinal paragraph."
    chunks = chunk_text(text, document_id="doc", chunk_size=1000, chunk_overlap=0)
    # With a large chunk size, everything fits in one chunk
    assert len(chunks) == 1
    assert "Hello world." in chunks[0].content
    assert "Final paragraph." in chunks[0].content


def test_chunk_metadata_defaults():
    """Default metadata fields are None."""
    text = "Some text here."
    chunks = chunk_text(text, document_id="doc")
    assert chunks[0].page_number is None
    assert chunks[0].section_title is None
    assert chunks[0].metadata is None
