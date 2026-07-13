from app.services.document_parser import ParsedSection
from app.services.text_chunker import chunk_sections

def test_chunker_creates_overlap() -> None:
    chunks = chunk_sections(
        [ParsedSection(text="A" * 1200, page_number=1)],
        chunk_size=500,
        overlap=100,
    )
    assert len(chunks) >= 3
    assert chunks[0].page_number == 1
    assert chunks[1].chunk_index == 1

def test_chunker_rejects_invalid_overlap() -> None:
    try:
        chunk_sections([ParsedSection(text="test")], chunk_size=100, overlap=100)
    except ValueError as exc:
        assert "overlap" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
