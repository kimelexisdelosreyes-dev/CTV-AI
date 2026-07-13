from pathlib import Path
from app.services.document_parser import parse_document

def test_parse_text(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("CTV-AI knowledge test", encoding="utf-8")
    sections = parse_document(path)
    assert len(sections) == 1
    assert sections[0].text == "CTV-AI knowledge test"
