# Knowledge Engine MVP

Pipeline:

Approved file → text extraction → chunking → local Ollama embeddings → Qdrant → semantic retrieval → source-grounded answer.

Supported:
- PDF with embedded text
- DOCX
- TXT
- Markdown

Scanned PDFs are not OCR-processed in this milestone.

Security:
- JWT required
- Admins and managers can ingest
- All authenticated users can search approved knowledge
- Do not ingest confidential HR, payroll, legal, or client documents until collection-level permissions are implemented
