# CTV ONE Responsive Strategy

Sprint: 2.0.1 UX Foundation and Information Architecture  
Scope: Responsive behavior for portal shell and Super Admin IAM.

## Breakpoints

| Breakpoint | Width | Strategy |
| --- | --- | --- |
| Mobile | 390-767 px | Single-column pages, task index navigation, stacked forms |
| Tablet | 768-1023 px | Collapsed sidebar, tabbed admin subsections, horizontal tables |
| Desktop | 1024-1439 px | Persistent sidebar, constrained content, dense admin tables |
| Wide desktop | 1440 px and above | Persistent sidebar, larger table viewport, optional detail side panel |

## Shell Behavior

Desktop:

- Sidebar remains visible.
- Administration can expand inline.
- Page header and primary action stay on the same row when space allows.
- Detail pages may use two-column layouts with a sticky summary or audit panel.

Tablet:

- Sidebar can collapse to icon rail.
- Administration subsection navigation becomes sticky horizontal tabs.
- Tables preserve key columns and move lower-priority metadata into row expansion.

Mobile:

- Login remains centered.
- Global navigation becomes a compact rail or bottom command region.
- Administration starts with a searchable task index.
- Data tables become card rows with visible primary metadata and action menu.
- Wizards use one step per screen.

## Data Table Responsiveness

Priority columns for User List:

1. Name
2. Status
3. Role
4. Department
5. Modules
6. Last active
7. Actions

Mobile card row:

```text
+--------------------------------------+
| Ada Cruz                      Active |
| Admin | Operations                   |
| 5 modules | Last login 12 min ago    |
| [Open]                         [...] |
+--------------------------------------+
```

Rules:

- Preserve action access on every viewport.
- Avoid horizontal scrolling for primary workflows on mobile.
- Allow horizontal scrolling only for comparative tools like Permission Matrix.
- Keep sticky headers for long tables on desktop.
- Use row expansion for secondary details.

## Wizard Responsiveness

Desktop:

- Stepper at top.
- Form on left, access preview on right.
- Footer actions fixed to wizard container.

Mobile:

- Current step label plus progress count.
- One form group at a time.
- Preview appears before final review, not beside every step.
- Footer actions remain reachable at bottom.

## Permission Matrix Responsiveness

Permission Matrix is inherently comparative.

Desktop:

- Sticky permission name column.
- Sticky role header row.
- Horizontal scroll when many roles are selected.

Tablet and mobile:

- Default to one selected role versus baseline.
- Provide role picker.
- Allow export for full comparison.
- Avoid compressing permission labels below readability.

## Touch Targets

- Minimum target: 44 x 44 px for touch.
- Dense desktop controls may be 36 px high if keyboard and pointer targets remain clear.
- Icon-only controls require tooltip and accessible label.
- Destructive overflow actions require confirmation.

## Layout Stability

Fixed-format admin elements need stable dimensions:

- Sidebars
- Table rows
- Status badges
- Quota meters
- Permission matrix cells
- Wizard footer
- Module cards
- Audit timeline rows

Dynamic content should wrap or truncate without resizing critical controls.

## Responsive Validation Checklist

Validate at:

- 1440 x 900
- 1280 x 800
- 1024 x 768
- 768 x 1024
- 390 x 844

Checks:

- No text overlaps.
- Primary action remains visible.
- Navigation remains understandable.
- Tables expose critical columns.
- Dialogs fit viewport.
- Wizard can be completed.
- Permission Matrix remains usable.
- Audit row details are reachable.

