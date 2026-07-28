# CTV ONE Admin User Flows

Sprint: 2.0.1 UX Foundation and Information Architecture  
Scope: Super Admin IAM journeys and wireframes.

## Primary User Journeys

### Journey 1: Create A New Employee

1. Super Admin opens Administration.
2. Selects Create user.
3. Enters identity details.
4. Assigns department and manager.
5. Assigns role.
6. Assigns AI modules.
7. Sets quota policy.
8. Sets knowledge access.
9. Reviews Professional AI Identity readiness.
10. Confirms invite or creates active account.
11. Audit event is recorded.

Success criteria:

- New user has safe baseline access.
- Access changes are previewed before save.
- Invitation or activation status is visible.
- Audit history links to the created user.

### Journey 2: Manage A User

1. Super Admin searches User List.
2. Opens User Detail.
3. Reviews identity, status, role, modules, quota, knowledge access, and AI identity.
4. Makes a scoped change.
5. Reviews change impact.
6. Provides reason when required.
7. Saves change.
8. Audit timeline updates.

### Journey 3: Suspend A User

1. Super Admin opens User Detail.
2. Selects Suspend access.
3. Confirmation dialog lists affected modules, active sessions, scheduled tasks, and AI identity behavior.
4. Super Admin confirms with reason.
5. User is suspended, sessions are revoked, AI access disabled, and audit event logged.

### Journey 4: Adjust Quota

1. Super Admin opens Quotas or User Detail.
2. Reviews current usage, trend, inherited policy, and exceptions.
3. Adjusts quota with numeric stepper or policy selector.
4. Sees projected reset date and affected modules.
5. Saves with optional reason.

### Journey 5: Grant Knowledge Access

1. Super Admin opens Knowledge Access.
2. Selects user, role, or department.
3. Selects collections or documents.
4. Previews reachable knowledge.
5. Saves grant.
6. Audit event records scope and target.

## User Creation Flow

```text
Start
  |
  v
Identity details
  |
  v
Department and manager
  |
  v
Role assignment
  |
  v
Module assignment
  |
  v
Quota policy
  |
  v
Knowledge access
  |
  v
Professional AI Identity preview
  |
  v
Review and create
  |
  v
Invite sent or account activated
```

Required wizard steps:

| Step | Required Fields | Validation |
| --- | --- | --- |
| Identity | Name, email, employment status | Email unique, domain allowed |
| Department | Department, manager optional | Department active |
| Role | Primary role | Role assignable by actor |
| Modules | Enabled AI modules | Dependencies satisfied |
| Quota | Policy or explicit limits | Limit within actor authority |
| Knowledge | Scope source | Sensitive scopes require confirmation |
| AI Identity | Display name, title, voice defaults | Identity does not imply unauthorized authority |
| Review | Summary and reason if required | All required controls complete |

## User Management Flow

The User Detail page is the canonical place to inspect and modify a user's access state.

Tabs:

- Profile
- Access
- Modules
- Quotas
- Knowledge
- Professional AI Identity
- Audit

High-risk actions:

- Suspend access
- Reset MFA
- Revoke sessions
- Remove all modules
- Grant privileged role
- Grant sensitive knowledge collection
- Override quota above policy

Each high-risk action requires:

- Confirmation
- Reason
- Affected system preview
- Audit event

## Wireframes

### User List

```text
+--------------------------------------------------------------------------------+
| Administration / Users                                      [Create user]       |
| Search users... [__________] Role [All] Dept [All] Status [All]                 |
|                                                                                |
| Name             Role            Department      Modules       Status   Actions |
| Ada Cruz         Admin           Operations      5 enabled     Active   ...     |
| Ben Santos       Employee        Sales           2 enabled     Invited  ...     |
| Mina Lee         Knowledge Mgr   Legal           3 enabled     Active   ...     |
|                                                                                |
| [Bulk actions]                                      1-25 of 212                 |
+--------------------------------------------------------------------------------+
```

### Create User Wizard

```text
+--------------------------------------------------------------------------------+
| Create User                                                                    |
| Identity > Department > Role > Modules > Quota > Knowledge > AI Identity > Review|
|                                                                                |
| Step: Role                                                                     |
| Primary role                                                                   |
| ( ) Employee       Baseline AI access                                           |
| ( ) Manager        Team administration                                          |
| ( ) Admin          Scoped administration                                        |
|                                                                                |
| Access preview                                                                 |
| + Knowledge: enabled                                                           |
| + AI Studio: read assigned capabilities                                        |
| - System Settings: denied                                                      |
|                                                                                |
| [Back]                                                   [Continue]             |
+--------------------------------------------------------------------------------+
```

### User Detail

```text
+--------------------------------------------------------------------------------+
| Users / Ada Cruz                                           [Suspend access]     |
| Active | Operations | Admin | Last login 12 min ago                             |
|                                                                                |
| Profile | Access | Modules | Quotas | Knowledge | AI Identity | Audit           |
|                                                                                |
| Current access                                                                 |
| Role: Admin                         Department: Operations                      |
| Modules: Knowledge, AI Studio drafting, AI analysis, Files                      |
| Quota: Operations Admin Policy, 82 percent remaining                            |
| Knowledge: Operations, Shared Policies, Runbooks                                |
|                                                                                |
| Access changes pending                                                         |
| No unsaved changes                                                             |
+--------------------------------------------------------------------------------+
```

### Department Management

```text
+--------------------------------------------------------------------------------+
| Administration / Departments                              [Create department]   |
|                                                                                |
| Departments                    Members                                          |
| Operations                     Ada Cruz       Admin       Manager: L. Reyes      |
|   Dispatch                     Jun Park       Employee    Manager: Ada Cruz      |
|   Field Support                Pia Lim        Employee    Manager: Ada Cruz      |
| Sales                                                                          |
| Legal                                                                          |
|                                                                                |
| Department defaults                                                            |
| Role template [Employee]  Quota policy [Department default]                     |
+--------------------------------------------------------------------------------+
```

### Role Builder

```text
+--------------------------------------------------------------------------------+
| Administration / Roles                                      [Create role]       |
| Roles                         Role: Department Manager                          |
| Employee                      Description [________________________]            |
| Department Manager            Assignable by [Admin, Super Admin]                |
| Admin                                                                          |
|                                                                                |
| Permissions                                                                    |
| [x] View team users          [x] Edit team membership                           |
| [x] View team quota          [ ] Change tenant settings                         |
| [ ] Grant Super Admin        [x] Approve quota override                         |
|                                                                                |
| Impact preview: 18 users currently hold this role                               |
| [Discard]                                                  [Save changes]       |
+--------------------------------------------------------------------------------+
```

### Permission Matrix

```text
+--------------------------------------------------------------------------------+
| Administration / Permission Matrix                                             |
| Filter [All modules] Search permission [____________] [Export]                  |
|                                                                                |
| Permission                     Employee  Manager  Admin  Super Admin            |
| View own profile               yes       yes      yes    yes                    |
| Manage department users        no        scoped   yes    yes                    |
| Assign AI modules              no        request  scoped yes                    |
| Manage system settings         no        no       no     yes                    |
| Export audit logs              no        no       scoped yes                    |
+--------------------------------------------------------------------------------+
```

### AI Module Management

```text
+--------------------------------------------------------------------------------+
| Administration / AI Modules                                                    |
| Module          Status      Eligible roles       Dependencies       Actions     |
| Knowledge Q&A    Enabled     All active users     Knowledge access   Configure  |
| AI drafting      Enabled     Writers, Marketing   Files access       Configure  |
| AI analysis      Enabled     Admin, Analysts      Knowledge access   Configure  |
| File generation  Enabled     Creative roles       File policy        Configure  |
|                                                                                |
| Assignment preview                                                             |
| Selected module affects 34 users and 6 roles                                    |
+--------------------------------------------------------------------------------+
```

### Quota Editor

```text
+--------------------------------------------------------------------------------+
| Administration / Quotas                                                        |
| Policy [Operations Admin] Reset [Monthly] Applies to [Role + Department]        |
|                                                                                |
| Requests per month       [-] 5000 [+]                                           |
| Token budget             [-] 20,000,000 [+]                                     |
| Burst limit              [----------|---] 80 percent                            |
|                                                                                |
| Module limits                                                                  |
| Knowledge Q&A   45 percent used                                                 |
| AI drafting     18 percent used                                                 |
| AI analysis     12 percent used                                                 |
|                                                                                |
| [Preview affected users]                              [Save quota policy]       |
+--------------------------------------------------------------------------------+
```

### Knowledge Access

```text
+--------------------------------------------------------------------------------+
| Administration / Knowledge Access                                              |
| Target [Department: Operations] Collection [All] Sensitivity [All]              |
|                                                                                |
| Collection             Access     Source          Sensitivity       Actions     |
| Operations Runbooks    Granted    Department      Internal          Revoke      |
| HR Policies            Denied     Role policy     Restricted        Request     |
| Vendor Contracts       Exception  Explicit grant  Confidential      Review      |
|                                                                                |
| Preview: 18 users can access 142 documents and 5,830 chunks                    |
+--------------------------------------------------------------------------------+
```

### Professional AI Identity

```text
+--------------------------------------------------------------------------------+
| Users / Ada Cruz / Professional AI Identity                                    |
| Status: Ready for AI interactions                         [Request review]      |
|                                                                                |
| Display name [Ada Cruz]                                                        |
| Title        [Operations Administrator]                                        |
| Department   [Operations]                                                      |
| Authority    [May approve dispatch workflow changes]                           |
|                                                                                |
| AI behavior                                                                    |
| [x] Use professional title in generated correspondence                          |
| [x] Include department context when routing tasks                               |
| [ ] Allow external-facing AI signature                                          |
|                                                                                |
| Boundary preview                                                               |
| CTV ONE can act with assigned modules only. It cannot imply legal authority.    |
+--------------------------------------------------------------------------------+
```

### Audit Activity

```text
+--------------------------------------------------------------------------------+
| Audit Activity                                                                 |
| Actor [All] Target [All] Action [All] Date [Last 7 days] [Export]              |
|                                                                                |
| Time                 Actor       Action              Target        Result       |
| 2026-07-27 09:41     M. Lim      Role changed        Ada Cruz      Success      |
| 2026-07-27 09:12     M. Lim      Module enabled      AI analysis   Success      |
| 2026-07-26 18:22     System      Quota reset         Ops Admin     Success      |
|                                                                                |
| Details panel opens on row selection                                           |
+--------------------------------------------------------------------------------+
```

### System Settings

```text
+--------------------------------------------------------------------------------+
| System Settings                                                                |
| Security | AI Policy | Knowledge | Connectors | Notifications                  |
|                                                                                |
| Security                                                                       |
| [x] Require MFA for administrators                                             |
| [x] Revoke sessions when user is suspended                                     |
| [ ] Allow external collaborators                                               |
|                                                                                |
| Default role for invited users [Employee]                                      |
| Audit retention [365 days]                                                     |
|                                                                                |
| [Save settings]                                                                |
+--------------------------------------------------------------------------------+
```

## Edge Cases

- User exists but invite has expired.
- User belongs to multiple departments with conflicting inherited access.
- Role edit would remove the current admin's own permission.
- Module enablement requires quota policy that is not configured.
- Knowledge collection is archived after access was granted.
- Professional AI Identity is incomplete but the user has AI module access.
- Audit export is requested by a role that can view but not export audit events.
