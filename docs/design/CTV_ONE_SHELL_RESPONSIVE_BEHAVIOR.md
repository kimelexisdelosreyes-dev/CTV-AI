# CTV ONE Shell Responsive Behavior

Sprint: Phase 2.0.3A Master Application Frame  
Scope: Responsive behavior for the permanent application shell.

## Breakpoints

| Range | Width | Frame Behavior |
| --- | --- | --- |
| Wide desktop | 1440 px and above | Expanded sidebar, full top bar, optional right drawers |
| Desktop | 1024-1439 px | Expanded or user-collapsed sidebar, full administration |
| Tablet | 768-1023 px | Collapsed sidebar or rail, top bar keeps search and profile |
| Mobile | 390-767 px | Menu sheet navigation, full-screen search, limited admin tasks |

## Wide Desktop

- Expanded primary sidebar.
- Top bar with organization, search, jobs, notifications, profile.
- Main content uses max readable widths for forms and wide layouts for tables.
- Contextual drawers can open on the right without covering the sidebar.
- Administration supports full Permission Matrix and side-by-side previews.

## Desktop

- Full administration supported.
- Sidebar can be expanded or collapsed.
- Breadcrumbs and page actions stay in page header.
- Drawers may overlay content or dock depending on available width.
- Sticky action areas are allowed.

## Tablet

- Sidebar collapses to rail or menu.
- Administration child navigation becomes sticky tabs.
- Data-heavy screens prioritize search, filters, and focused detail views.
- Permission Matrix defaults to fewer compared roles.

## Mobile

Mobile administration prioritizes:

- Account lookup
- Status review
- Urgent suspension
- Approvals
- Quota review
- Alerts

Mobile administration does not force the complete Permission Matrix into a small viewport. Instead, it provides:

- Role lookup
- User permission summary
- High-risk action flows
- Request/approval actions
- Links to desktop-required comparison tasks

## Tablet Shell Wireframe

```text
+----------------------------------------------------+
| CTV ONE  [Search]                 Jobs  Alerts  Me |
|----------------------------------------------------|
| Rail | Breadcrumbs                                 |
| W    | Page Title                     [Primary]    |
| K    |---------------------------------------------|
| A    | Main content                                |
| P    |                                             |
| F    |                                             |
| I    |                                             |
+----------------------------------------------------+
```

## Mobile Shell Wireframe

```text
+--------------------------------------+
| [Menu] Workspace      Search Jobs Me |
|--------------------------------------|
| Page title                           |
| [Primary action]                     |
|--------------------------------------|
| Main content cards                   |
|                                      |
|                                      |
+--------------------------------------+
```

## Mobile Navigation Open

```text
+--------------------------------------+
| CTV ONE                         [X]  |
|                                      |
| Workspace                            |
| Knowledge                            |
| AI Studio                            |
| Projects                             |
| Files                                |
| Professional AI Identity             |
| Administration, if permitted         |
| Settings                             |
+--------------------------------------+
```

## Responsive Rules

- Primary action must remain reachable on every viewport.
- Search must remain available globally.
- Jobs and notifications must remain reachable but can move behind labeled icons.
- Profile and sign-out must remain reachable.
- Reduced navigation must preserve current location context.
- Avoid horizontal scrolling except for designed comparison tools.
- Mobile tap targets are at least 44 by 44 px.

