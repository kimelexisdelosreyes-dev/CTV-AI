# CTV ONE Navigation Specification

Sprint: Phase 2.0.3A Master Application Frame  
Scope: Product-facing, permission-aware navigation model.

## Navigation Principle

Navigation is derived from effective permissions, not hardcoded job titles. Job titles in this document are examples of likely permission bundles.

All employees retain access to approved general Company Knowledge unless account state or platform policy explicitly removes it.

## Product-Facing Primary Navigation

| Item | Purpose | Ordinary User Label |
| --- | --- | --- |
| Workspace | Daily work, assigned actions, operational overview | Workspace |
| Knowledge | Approved company knowledge, collections, answers, sources | Knowledge |
| AI Studio | AI-assisted creation, drafting, analysis, and specialist workflows | AI Studio |
| Projects | Project planning, assignments, milestones, outputs | Projects |
| Files | Documents, uploads, shared assets, exports | Files |
| Professional AI Identity | Business identity and AI representation controls | Professional AI Identity |
| Administration | IAM, governance, modules, quotas, audit | Administration |
| Settings | Preferences and permitted tenant settings | Settings |

## Administration Navigation

Administration route model:

| Route | Label |
| --- | --- |
| `/admin` | Overview |
| `/admin/users` | Users |
| `/admin/users/new` | Create User |
| `/admin/users/:id` | User Detail |
| `/admin/departments` | Departments |
| `/admin/roles` | Roles |
| `/admin/permissions` | Permission Matrix |
| `/admin/modules` | AI Modules |
| `/admin/quotas` | Quotas and Limits |
| `/admin/knowledge-access` | Knowledge Access |
| `/admin/professional-identities` | Professional AI Identities |
| `/admin/audit` | Audit Activity |
| `/admin/settings` | System Settings |

Recommended decision:

- Administration should use routes, not only in-memory tabs.
- Routes allow deep links, audit references, object details, approval workflows, and permission-specific redirects.
- The global frame remains stable across admin routes.

## Role-Aware Navigation Examples

These examples show effective-permission outcomes. They are not hardcoded title rules.

| Example Role | Navigation |
| --- | --- |
| Super Admin | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Administration, Settings |
| Admin | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Administration subset, Settings |
| Executive Producer | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| Writer | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| Editor | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| Multimedia Artist | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| Graphic Artist | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| Marketing | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| Sales | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| HR | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings |
| Standard Employee | Workspace, Knowledge, AI Studio if entitled, Projects if assigned, Files, Professional AI Identity, Settings |
| Future Custom Role | Any combination allowed by effective permissions and tenant policy |

## Sidebar Specification

Desktop expanded:

- Logo and organization identity at top.
- Product navigation below.
- Administration appears only if permitted.
- Settings appears at bottom or lower group.
- Current route has `aria-current="page"` and visual active state.

Desktop collapsed:

- Icons remain.
- Tooltips reveal labels.
- Active item remains visually and semantically clear.
- Search, jobs, notifications, and profile stay in top bar.

Mobile:

- Primary navigation opens as a menu sheet.
- Keep most-used items first.
- Administration entry opens an admin task list optimized for urgent actions.

## Permission-Aware Navigation States

| State | UX Behavior |
| --- | --- |
| Hidden capability | Omit from navigation and search |
| Disabled capability | Show only when discoverable and explanatory, with reason |
| Coming-soon module | Show only to allowed preview audiences |
| Temporarily unavailable module | Show with status and keep unrelated modules active |
| Quota exhausted | Keep page reachable, disable generation actions, show quota path |
| Approval required | Show locked action with request flow |
| Restricted knowledge | Omit restricted objects and metadata |
| Platform-enforced restriction | Show policy reason if user is allowed to know |
| Role-inherited permission | Show inherited source in detail pages, not sidebar |
| Department-inherited permission | Show inherited source in detail pages, not sidebar |
| Direct override | Show override badge in access detail and audit |

## Standard Employee Shell

```text
+--------------------------------------------------------------------------------+
| Sidebar                  | Top bar: Search  Jobs  Notifications  Profile        |
| > Workspace              |------------------------------------------------------|
|   Knowledge              | Workspace                                            |
|   AI Studio              | Assigned work, recent files, approved knowledge       |
|   Projects               |                                                      |
|   Files                  |                                                      |
|   Professional AI Identity|                                                     |
|   Settings               |                                                      |
+--------------------------------------------------------------------------------+
```

## Editor Shell

```text
+--------------------------------------------------------------------------------+
| Sidebar                  | Top bar: Search projects, files, knowledge           |
| > Workspace              |------------------------------------------------------|
|   Knowledge              | Editing Workspace                                    |
|   AI Studio              | Draft review, source checks, project assignments      |
|   Projects               |                                                      |
|   Files                  |                                                      |
|   Professional AI Identity|                                                     |
|   Settings               |                                                      |
+--------------------------------------------------------------------------------+
```

## Marketing Shell

```text
+--------------------------------------------------------------------------------+
| Sidebar                  | Top bar: Search campaigns, files, approved knowledge |
| > Workspace              |------------------------------------------------------|
|   Knowledge              | Marketing Workspace                                  |
|   AI Studio              | Campaign tasks, content drafts, approvals            |
|   Projects               |                                                      |
|   Files                  |                                                      |
|   Professional AI Identity|                                                     |
|   Settings               |                                                      |
+--------------------------------------------------------------------------------+
```

## Future Modules

Future modules should enter navigation only when:

- The module has a stable product-facing name.
- A permission exists for visibility.
- Empty, disabled, loading, and unavailable states are designed.
- Universal search indexing rules are defined.
- Audit and notification behaviors are defined.

