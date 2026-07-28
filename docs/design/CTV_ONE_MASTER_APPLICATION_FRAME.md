# CTV ONE Master Application Frame

Sprint: Phase 2.0.3A Master Application Frame  
Scope: Design-only shell specification for every CTV ONE product area.

## Master Frame Decision

CTV ONE should use one permanent application frame across all product areas. The frame exposes user-facing workflows and hides internal implementation names from ordinary navigation.

Approved product-facing navigation:

- Workspace
- Knowledge
- AI Studio
- Projects
- Files
- Professional AI Identity
- Administration
- Settings

Do not expose internal engine names, model names, provider names, graph retrieval names, infrastructure terms, or backend service names in ordinary employee navigation. Administration may expose "AI Modules" as a governance concept, but it should describe capabilities, assignments, quotas, and policy rather than internal implementation.

## Existing Shell Review

The current frontend has a compact dark shell with a persistent left sidebar and section-based content. It already establishes:

- Strong CTV ONE brand lockup.
- Dark enterprise visual tone.
- Sidebar navigation.
- Main content region.
- Login and authenticated app states.
- Responsive collapse behavior.

The master frame should evolve this shell into a route-aware enterprise frame with global search, alerts, job monitoring, profile controls, role-aware navigation, and clear system state behavior.

## Application Regions

1. Primary sidebar
2. Top application bar
3. Universal search
4. AI job center
5. Notification center
6. Profile menu
7. Page header
8. Breadcrumbs
9. Main content container
10. Contextual drawers
11. Modal layer
12. Sticky action areas
13. System-status area

## Primary Sidebar

Purpose:

- Provide stable product-area navigation.
- Reflect effective permissions.
- Avoid leaking restricted capabilities.
- Support future modules without redesign.

Desktop behavior:

- Expanded width: 252-280 px.
- Collapsed width: 72-88 px.
- Active item has icon, label, active semantic state, and orange accent.
- Disabled items appear only when visibility is allowed and the user needs explanation.

Sidebar order:

1. Workspace
2. Knowledge
3. AI Studio
4. Projects
5. Files
6. Professional AI Identity
7. Administration
8. Settings

Administration should appear only for users with at least one effective admin permission.

## Top Application Bar

Purpose:

- Hold universal actions and current organizational context.
- Keep workflow pages focused.

Required controls:

- Skip link target after initial focus.
- Organization or workspace selector, when applicable.
- Universal search trigger.
- AI job center trigger.
- Notification center trigger.
- Profile menu trigger.
- Optional compact system-status indicator.

Rules:

- Search is global, not page-only.
- Job center and notifications are separate because jobs are operational progress while notifications are attention events.
- Profile menu never contains product navigation that belongs in the sidebar.

## Universal Search

The search trigger opens an accessible command-style overlay. It searches only objects the user is permitted to discover.

Searchable product-facing categories:

- Pages
- People
- Projects
- Files
- Knowledge
- Tasks
- AI jobs
- Settings

Restricted content rules:

- Do not leak restricted titles, filenames, snippets, owners, paths, tags, counts, or metadata.
- If a result is not discoverable, it is absent rather than masked.
- Search can show "request access" only for approved discoverable collections or objects.

## AI Job Center

The AI job center shows long-running and background AI work in product language:

- Preparing answer
- Indexing knowledge
- Generating file
- Processing project update
- Waiting for approval
- Completed
- Failed

It must not expose model, provider, queue, worker, or service names to ordinary employees.

## Notification Center

Notifications are attention events:

- Approval requested
- Quota limit approaching
- File shared
- Knowledge access changed
- Session expiring
- Account policy updated
- Administration change completed

Notifications are permission-aware and never include restricted content metadata.

## Profile Menu

Profile menu contents:

- User identity summary
- Role and organization context
- Professional AI Identity shortcut
- Preferences
- Theme selector
- Keyboard shortcuts
- Session controls
- Sign out

Do not place admin mutation controls in the profile menu.

Profile menu wireframe:

```text
+--------------------------------------+
| Ada Cruz                             |
| Operations Administrator              |
| Role: Admin                           |
|--------------------------------------|
| Professional AI Identity              |
| Preferences                           |
| Theme: System                         |
| Keyboard shortcuts                    |
| Session details                       |
|--------------------------------------|
| Sign out                              |
+--------------------------------------+
```

## Page Header

Page header structure:

- Breadcrumbs
- Page title
- Short operational description when helpful
- Object state badges
- Primary action
- Secondary actions menu

Header should avoid marketing copy. The title should name the current workflow or object.

## Main Content Container

Layout types:

- Overview dashboard
- Object list
- Object detail
- Wizard
- Matrix/comparison
- Split workspace
- Settings form
- Audit timeline
- Empty state

Each content type should preserve the same frame and avoid full-page custom chrome.

## Contextual Drawers

Use drawers for:

- Inspecting details while preserving list context.
- Viewing notifications.
- Viewing AI jobs.
- Previewing access impact.
- Reviewing audit event details.

Drawer rules:

- Drawer has heading, close control, focus trap, and focus restoration.
- Drawer can be dismissed without saving if no dirty state exists.
- Dirty drawers require save, discard, or cancel.

## Modal Behavior

Use modals for:

- Destructive confirmations.
- Short blocking decisions.
- Session expiration.
- Required approval reasons.

Modal rules:

- Focus starts on the safest action.
- Escape closes only dismissible modals.
- Confirmation modals name the target and consequence.
- Modals should not contain large data tables.

## Sticky Action Areas

Use sticky actions for:

- Wizards.
- Long settings forms.
- Role Builder.
- Quota Editor.
- Professional AI Identity review.

Sticky footer includes:

- Save or continue.
- Cancel or discard.
- Unsaved state text.
- Validation status when relevant.

## System-Status Area

System status appears as a compact top-bar indicator and expands to details only when needed.

States:

- All systems available.
- Degraded service.
- Offline.
- Maintenance.
- Permission changed.

A single service failure must not disable unrelated product areas.

## Wireframes

### Expanded Desktop Shell

```text
+--------------------------------------------------------------------------------+
| Sidebar                    | Top bar: Org  Search  Jobs  Notifications Profile |
| CTV ONE                    |----------------------------------------------------|
| > Workspace                | Breadcrumbs                                       |
|   Knowledge                | Page Title                         [Primary] [...]|
|   AI Studio                |----------------------------------------------------|
|   Projects                 |                                                    |
|   Files                    | Main content container                            |
|   Professional AI Identity |                                                    |
|   Administration           |                                                    |
|   Settings                 |                                                    |
+--------------------------------------------------------------------------------+
```

### Collapsed Desktop Shell

```text
+--------------------------------------------------------------------------------+
| C | Top bar: Org  Search  Jobs  Notifications Profile                          |
|---|----------------------------------------------------------------------------|
| W | Breadcrumbs                                                               |
| K | Page Title                                                [Primary]       |
| A |----------------------------------------------------------------------------|
| P | Main content container                                                    |
| F |                                                                            |
| I |                                                                            |
| S |                                                                            |
+--------------------------------------------------------------------------------+
```

### Administration Shell

```text
+--------------------------------------------------------------------------------+
| Primary sidebar           | Administration / Users                 [Create user] |
| Workspace                 |----------------------------------------------------|
| Knowledge                 | Admin nav: Overview Users Departments Roles ...    |
| AI Studio                 |----------------------------------------------------|
| Projects                  | Filter toolbar                                     |
| Files                     | User administration content                        |
| Professional AI Identity  | Sticky save/action area when editing               |
| > Administration          |                                                    |
| Settings                  |                                                    |
+--------------------------------------------------------------------------------+
```

### Degraded-Service Banner

```text
+--------------------------------------------------------------------------------+
| Service degraded: Knowledge search is delayed. Workspace and Files are available.|
| [View details]                                                        [Dismiss] |
+--------------------------------------------------------------------------------+
```

### Session-Expiry Warning

```text
+----------------------------------------------+
| Session expiring                              |
| Your session will expire in 2 minutes.        |
|                                              |
| [Sign out]                    [Stay signed in]|
+----------------------------------------------+
```
