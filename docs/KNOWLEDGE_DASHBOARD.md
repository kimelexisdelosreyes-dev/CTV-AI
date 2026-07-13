# Knowledge Admin Dashboard

Open:

```text
http://127.0.0.1:8000/admin/knowledge
```

The dashboard uses the existing JWT login system and provides:

- Document upload
- Category assignment
- Indexing status
- Document deletion
- Semantic search testing
- Grounded-answer testing
- Knowledge statistics

Deletion removes:

1. Qdrant vectors belonging to the document
2. The stored source file
3. PostgreSQL metadata

Use this dashboard only on the trusted local network until HTTPS and stricter administrative access controls are added.
