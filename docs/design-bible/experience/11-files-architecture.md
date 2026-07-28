# 11 - Files Architecture

## Definition

Files is an enterprise media and document access layer. It may reference NAS storage, cloud storage, project files, generated assets, and company archives without assuming physical copy into CTV ONE.

## File Types

| Type | Meaning |
| --- | --- |
| Indexed file | Searchable metadata or text exists in CTV ONE |
| Linked file | CTV ONE references an external location |
| Uploaded file | File was uploaded into CTV ONE-controlled storage |
| Generated file | File was created by an AI capability or export |
| Archived file | Retained but removed from active work |
| Unavailable file | Known file whose storage source cannot currently be reached |

## Files IA

- Recent files
- Shared files
- Project files
- Archive files
- Generated files
- Favorites
- Search
- Filters
- File preview
- Metadata
- Version history
- Permissions
- File location
- Project relationships
- Knowledge relationships
- AI usage history

## Actions

- Download
- Share
- Move
- Rename
- Archive
- Delete with safeguards
- Link to project
- Use in AI Studio

## Storage States

- Available
- Offline
- Permission denied
- File moved
- File deleted
- Preview unavailable
- Indexing delayed

Design language should distinguish "CTV ONE cannot reach this file right now" from "you do not have permission".

