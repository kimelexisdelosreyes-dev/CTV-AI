# CTV ONE Global Search UX

Sprint: Phase 2.0.3A Master Application Frame  
Scope: Universal search across permitted CTV ONE product areas.

## Search Decision

Universal search should be a top-bar command overlay available from every authenticated page. It must search product-facing objects and workflows without revealing restricted objects or internal implementation names.

## Search Entry Points

- Top bar search button or input.
- Keyboard shortcut.
- Empty-state search affordance on list pages.
- Mobile search action in navigation menu.

## Searchable Categories

| Category | Examples |
| --- | --- |
| Pages | Workspace, Knowledge, AI Studio, Projects, Files, Settings |
| People | Users discoverable by policy |
| Projects | Assigned or visible projects |
| Files | Files visible to the user |
| Knowledge | Approved collections and documents visible to the user |
| Tasks | Assigned or visible actions |
| AI jobs | User-owned or admin-visible jobs |
| Administration | Admin pages and objects, only when permitted |

## Non-Disclosure Rules

Search must not leak restricted:

- Titles
- Filenames
- Snippets
- Owners
- Paths
- Tags
- Counts
- Timestamps
- Collection names
- Relationship metadata

If a user cannot discover an object, it must not appear in results.

## Search Overlay Behavior

```text
+--------------------------------------------------------------+
| Search CTV ONE                                               |
| [ Find people, projects, files, knowledge, or pages ______ ]  |
|                                                              |
| Quick actions                                                |
| > Open Workspace                                             |
| > Create project                                             |
|                                                              |
| Results                                                      |
| Files                                                        |
|  Campaign brief.pdf                 Updated yesterday        |
| Knowledge                                                     |
|  Brand voice guidelines             Approved company knowledge|
| People                                                       |
|  Ada Cruz                           Operations               |
+--------------------------------------------------------------+
```

## Accessibility

Requirements:

- Dialog role with accessible title.
- Focus moves to search field on open.
- Escape closes and restores focus.
- Arrow keys move through results.
- Enter opens selected result.
- Category headings are announced.
- Result count is announced after debounce.
- Loading state is announced politely.
- No result state is descriptive.

## Ranking

Suggested ranking factors:

- Exact title or name match.
- Recently opened by user.
- Assigned work.
- Current product area.
- Organizational relevance.
- Permission confidence.

Search should not rank restricted or hidden results.

## Mobile Search

Mobile behavior:

- Full-screen overlay.
- Large input target.
- Results grouped as cards.
- Filters available after search, not before.
- Keyboard focus stays in overlay until closed.

## Search States

| State | Behavior |
| --- | --- |
| Empty query | Show recent pages and quick actions |
| Loading | Show skeleton grouped results |
| Results | Show category groups |
| No results | Show safe alternatives and page suggestions |
| Permission changed | Refresh permissions and remove stale results |
| Offline | Search local recent pages only if supported |
| Degraded | Show available categories and unavailable notice |

