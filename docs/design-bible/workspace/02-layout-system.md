# 02 - Layout System

## Visual Hierarchy

1. Hero: first five-second answer and primary resume action.
2. Primary modules: Continue Working, Today's Priorities, My AI Briefing.
3. Secondary modules: Projects, Knowledge, Activity Timeline, Calendar.
4. Utilities: system status, announcements, low-priority notifications.
5. Footer: rarely needed; avoid using footer for primary work.

## Desktop Grid

Recommended desktop canvas:

- Content max width: 1280-1440 px inside the application frame.
- Outer content margin: 32-48 px.
- Grid: 12 columns.
- Gutter: 20-24 px.
- Hero height: about 25-30 percent of viewport.
- Primary module row: 3-column composition after hero.
- Secondary area: 8-column main plus 4-column utility rail when useful.

```mermaid
flowchart TB
    Hero[Hero: full width, 25-30 percent viewport]
    Hero --> Row1[Primary row]
    Row1 --> Continue[Continue Working: 5-6 cols]
    Row1 --> Priorities[Today's Priorities: 3-4 cols]
    Row1 --> MyAI[My AI Briefing: 3-4 cols]
    Row1 --> Row2[Secondary row]
    Row2 --> Projects[Projects: 8 cols]
    Row2 --> Side[Knowledge, Timeline, Calendar: 4 cols]
```

## Tablet Layout

- Content margin: 24 px.
- Grid: 8 columns.
- Hero remains full width but shorter.
- Continue Working becomes full width.
- Priorities and My AI become two columns.
- Projects become full width.
- Knowledge and timeline stack below.

## Mobile Layout

- Content margin: 16 px.
- Single-column priority stack.
- Hero becomes compact.
- Continue Working appears immediately after hero.
- Today's Priorities follows.
- Quick Actions use horizontal scroll or compact grid.
- Projects show top three only with View all.
- Knowledge shows one recommendation group at a time.
- Calendar becomes "Next scheduled item".
- Activity Timeline shows latest three entries.

## Reading Flow

```mermaid
flowchart LR
    A[Where am I?] --> B[What should I resume?]
    B --> C[What needs attention?]
    C --> D[What changed?]
    D --> E[What can AI help with?]
    E --> F[Where do I go next?]
```

## Whitespace Philosophy

Workspace should use fewer, stronger modules. The screen should breathe. Avoid equal-weight dashboards where every card competes. Use whitespace to show priority, not emptiness.

