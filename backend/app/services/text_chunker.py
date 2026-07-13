from dataclasses import dataclass
from app.services.document_parser import ParsedSection

@dataclass(frozen=True)
class TextChunk:
    text: str
    chunk_index: int
    page_number: int | None

def chunk_sections(sections: list[ParsedSection], chunk_size: int, overlap: int) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be zero or less than chunk_size")

    chunks = []
    chunk_index = 0
    for section in sections:
        normalized = " ".join(section.text.split())
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + chunk_size)
            candidate = normalized[start:end]
            if end < len(normalized):
                boundary = max(candidate.rfind(". "), candidate.rfind("? "), candidate.rfind("! "))
                if boundary >= chunk_size // 2:
                    end = start + boundary + 1
                    candidate = normalized[start:end]
            text = candidate.strip()
            if text:
                chunks.append(TextChunk(text=text, chunk_index=chunk_index, page_number=section.page_number))
                chunk_index += 1
            if end >= len(normalized):
                break
            start = max(start + 1, end - overlap)
    return chunks
