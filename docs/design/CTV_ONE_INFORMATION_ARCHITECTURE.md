# CTV ONE Information Architecture

Sprint: 2.0.1 UX Foundation and Information Architecture  
Scope: Portal IA with Super Admin IAM as the first fully specified administration module.

## Architecture Summary

CTV ONE should use a stable enterprise shell with role-filtered navigation. The primary hierarchy separates daily work, knowledge, AI-assisted creation, projects, files, professional identity, administration, and settings.

The current frontend already supports a left navigation pattern and single-page section switching. Sprint 2.0.1 defines the target IA so implementation can later choose route-based pages, nested section state, or a hybrid without changing the product model.

## Global Navigation

Top-level navigation for a full-access Super Admin:

1. Workspace
2. Knowledge
3. AI Studio
4. Projects
5. Files
6. Professional AI Identity
7. Administration
8. Settings

Recommended sidebar grouping:

| Group | Items | Notes |
| --- | --- | --- |
| Work | Workspace, Projects, Files | Daily work, project execution, and assets |
| Intelligence | Knowledge, AI Studio, Professional AI Identity | Approved knowledge and AI-assisted work |
| Admin | Administration, Settings | Access and governance |

## Administration Navigation

Administration contains these subsections:

1. Overview
2. Users
3. Departments
4. Roles
5. Permission Matrix
6. AI Modules
7. Quotas and Limits
8. Knowledge Access
9. Professional AI Identity
10. Audit Activity
11. Settings

Recommended nested sidebar behavior:

- Desktop: expanded Administration item reveals nested child navigation.
- Tablet: Administration opens as a secondary rail or sticky tab row.
- Mobile: Administration opens to an index page with searchable admin tasks.

## Role-Specific Navigation

| Role | Visible Top-Level Navigation | Notes |
| --- | --- | --- |
| Super Admin | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Administration, Settings | Can manage users, roles, modules, quotas, knowledge access, AI identities, audit, and system settings |
| Admin | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Administration subset, Settings | Cannot grant Super Admin or change platform-wide controls |
| Department Manager | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, team administration when permitted, Settings | Sees only assigned departments and scoped quotas |
| Knowledge Manager | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Knowledge Access when permitted, Settings | Manages collections and access scopes, not IAM roles |
| Developer | Workspace, Knowledge, AI Studio, Projects, Files, Professional AI Identity, Settings | Technical diagnostics are permissioned admin or settings views, not ordinary navigation |
| Standard Employee | Workspace, Knowledge, AI Studio if entitled, Projects if assigned, Files, Professional AI Identity, Settings | No admin shell |
| Auditor | Workspace read-only, Administration audit and permission views read-only, Settings read-only | Cannot mutate portal state |

## Page Inventory

### Authentication

| Page | Purpose | Primary Actions |
| --- | --- | --- |
| Login | Authenticate user and route to authorized shell | Sign in |
| Session expired | Recover from expired credentials | Sign in again |
| Access denied | Explain missing access | Return to overview |

### Portal

| Page | Purpose | Primary Actions |
| --- | --- | --- |
| Workspace | Executive and operational work summary | Review status, enter workspaces |
| Knowledge | Approved company knowledge and knowledge-grounded answers | Ask, browse, inspect permitted sources |
| AI Studio | AI-assisted creation, drafting, analysis, and specialist workflows | Start AI work, review capabilities |
| Projects | Project planning, assignments, milestones, and outputs | Review, assign, prioritize |
| Files | Documents, uploads, shared assets, and exports | Upload, organize, share, inspect |
| Professional AI Identity | Business identity and AI representation controls | Review profile, request or approve changes |

### Administration

| Page | Purpose | Primary Actions |
| --- | --- | --- |
| Super Admin Overview | Summarize identity, access, module, quota, and risk posture | Create user, review alerts, open audit |
| User List | Find and manage portal users | Create, filter, bulk edit, export |
| Create User Wizard | Create identity and assign safe baseline access | Invite, create, assign role, set quota |
| User Detail | Inspect and manage one user | Edit, suspend, assign modules, review audit |
| Department Management | Manage departments, memberships, and managers | Create department, move users, assign manager |
| Role Builder | Create and edit roles | Clone, edit permissions, preview impact |
| Permission Matrix | Compare permissions across roles and modules | Filter, inspect, export |
| AI Module Management | Assign product modules and AI agents | Enable, disable, review dependencies |
| Quota Editor | Allocate and adjust AI usage limits | Set limits, approve overrides |
| Knowledge Access | Manage collection and document access scopes | Grant, revoke, preview coverage |
| Professional AI Identity | Configure how users appear and act through AI | Review profile, approve identity state |
| Audit Activity | Search administrative and AI governance events | Filter, inspect, export |
| System Settings | Configure tenant-level controls | Edit policies, connectors, defaults |

## Route Model

Suggested route model for future implementation:

| Route | Page |
| --- | --- |
| `/login` | Login |
| `/` | Workspace |
| `/knowledge` | Knowledge |
| `/ai-studio` | AI Studio |
| `/projects` | Projects |
| `/files` | Files |
| `/professional-ai-identity` | Professional AI Identity |
| `/admin` | Super Admin Overview |
| `/admin/users` | User List |
| `/admin/users/new` | Create User Wizard |
| `/admin/users/:id` | User Detail |
| `/admin/departments` | Department Management |
| `/admin/roles` | Role Builder |
| `/admin/permissions` | Permission Matrix |
| `/admin/modules` | AI Module Management |
| `/admin/quotas` | Quotas and Limits |
| `/admin/knowledge-access` | Knowledge Access |
| `/admin/professional-identities` | Professional AI Identity |
| `/audit` | Audit Activity |
| `/settings` | System Settings |

## Object Relationships

User:

- Belongs to zero or more departments.
- Has one primary role and optional additive scoped roles.
- Receives AI module entitlements.
- Receives quota policies.
- Receives knowledge access through role, department, explicit grant, or exception.
- Has a Professional AI Identity state.
- Produces audit activity.

Role:

- Defines permissions.
- Can imply baseline module visibility.
- Can imply default quota tier.
- Can imply baseline knowledge scope.
- Cannot override explicit denial policies.

Department:

- Groups users.
- Assigns managers.
- Can scope knowledge and quotas.
- Can provide default role templates.

AI Module:

- Requires entitlement.
- May require knowledge access.
- May consume quota.
- May require Professional AI Identity readiness.

## Login Wireframe

```text
+------------------------------------------------------------+
|                                                            |
|                         CTV ONE                            |
|                   Enterprise AI Portal                     |
|                                                            |
|             Email                                          |
|             [________________________________]             |
|                                                            |
|             Password                                       |
|             [________________________________]             |
|                                                            |
|             [ Sign in ]                                    |
|                                                            |
|             SSO option, if enabled                         |
|                                                            |
+------------------------------------------------------------+
```

Validation notes:

- Login should be visually quiet and centered.
- Error copy should not disclose whether email or password failed.
- After authentication, route by highest-priority permitted home page.

## Super Admin Overview Wireframe

```text
+--------------------------------------------------------------------------------+
| Sidebar                  | Super Admin Overview                  [Create user]   |
| Overview                 | Identity, access, and AI governance posture           |
| Intelligence             |                                                        |
| Administration >         | [Users] [Roles] [AI modules] [Quota use] [Risks]       |
|  Overview                |                                                        |
|  Users                   | Access alerts                         Recent activity  |
|  Departments             | - 3 users pending invite              - Role changed    |
|  Roles                   | - 2 quota overrides pending           - Module enabled  |
|  Permissions             | - 1 stale Professional AI Identity     - User suspended |
| Platform                 |                                                        |
|                          | Department coverage                  System policy      |
|                          | Sales       42 users                  MFA required      |
|                          | Ops         18 users                  Audit export on   |
+--------------------------------------------------------------------------------+
```

## Navigation Decision

Sprint 2.0.1 recommends adding Administration as a primary sidebar item when implementation begins. Employees and Settings placeholders should be absorbed into Administration and System Settings rather than remaining as passive future-nav text.
