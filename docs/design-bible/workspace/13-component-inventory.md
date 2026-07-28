# 13 - Component Inventory

## Workspace Components

| Component | Purpose | Required States |
| --- | --- | --- |
| Hero Panel | Daily context and primary suggested action | first login, returning, busy, quiet, offline |
| Greeting | Personal orientation | normal, first login, returning |
| Continue Button | Resume exact work context | ready, disabled, loading |
| Continue Working Card | Workspace Memory item | active, paused, completed, dismissed |
| Project Card | Active project summary | active, pinned, blocked, completed, archived |
| Knowledge Card | Recommended or required knowledge | recommended, required, updated, unavailable |
| Announcement Card | Organization message | unread, required, dismissed |
| Quick Action | Role-aware shortcut | enabled, disabled, quota reached |
| Priority Card | Actionable attention item | due, blocked, approval, AI review |
| Timeline Item | Work activity event | normal, important, filtered |
| Status Chip | Compact state label | success, warning, danger, info, neutral |
| AI Brief Card | My AI briefing item | collapsed, expanded, dismissed |
| Module Header | Section identity and secondary action | default, loading, empty |
| Section Divider | Rhythm between modules | desktop, mobile |
| Loading Skeleton | Loading state | module, card, row |
| Empty State | Role-aware absence of content | first-use, no work, no permission |
| Calendar Item | Scheduled event summary | upcoming, live, past |
| System Status Strip | Relevant platform state | degraded, offline, maintenance |

## Component Rules

- Cards have one clear primary action.
- Secondary actions belong in overflow or lower emphasis areas.
- Status chips include text, not color alone.
- Loading skeletons preserve final layout dimensions.
- Empty states should guide action rather than explain features generically.

