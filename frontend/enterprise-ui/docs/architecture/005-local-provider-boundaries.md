# Local Provider Boundaries

Phase 4.1C introduces local-demo providers around existing source records:

- `LocalFilesSearchProvider` owns file and asset records from `demoFileResults`.
- `LocalKnowledgeSearchProvider` owns Knowledge-category records.
- `LocalProjectsSearchProvider` owns Projects-category records.

Source adapters and normalizers remain independent of React and presentation components. The composition root is the only place that registers providers. NAS, Google Drive, Alibaba OSS, Monday.com, authentication, APIs, and database schemas remain outside this phase.

The generic `DemoSearchProvider` remains registered during migration. Normalized provider attribution is retained so duplicate strategy can be improved with stronger stable identifiers when authoritative IDs become available.
