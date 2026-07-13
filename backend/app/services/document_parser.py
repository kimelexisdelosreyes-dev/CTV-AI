from dataclasses import dataclass
from pathlib import Path
import pymupdf
from docx import Document

@dataclass(frozen=True)
class ParsedSection:
    text: str
    page_number: int | None = None

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

def parse_document(path: Path) -> list[ParsedSection]:
    extension = path.suffix.lower()
    if extension == ".pdf":
        return _parse_pdf(path)
    if extension == ".docx":
        return _parse_docx(path)
    if extension in {".txt", ".md"}:
        return _parse_text(path)
    raise ValueError(f"Unsupported file extension: {extension}")

def _parse_pdf(path: Path) -> list[ParsedSection]:
    sections = []
    with pymupdf.open(path) as document:
        for page_index, page in enumerate(document):
            text = page.get_text("text", sort=True).strip()
            if text:
                sections.append(ParsedSection(text=text, page_number=page_index + 1))
    return sections

def _parse_docx(path: Path) -> list[ParsedSection]:
    document = Document(path)
    blocks = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                blocks.append(" | ".join(cells))
    text = "\n".join(blocks).strip()
    return [ParsedSection(text=text)] if text else []

def _parse_text(path: Path) -> list[ParsedSection]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return [ParsedSection(text=text)] if text else []
