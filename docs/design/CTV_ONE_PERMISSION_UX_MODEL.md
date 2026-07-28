# CTV ONE Permission UX Model

Sprint: 2.0.1 UX Foundation and Information Architecture  
Scope: User-facing model for permissions, roles, modules, quotas, and knowledge access.

## Permission Hierarchy

Access is evaluated and displayed in this order:

1. Tenant policy
2. User status
3. Role permissions
4. Department scope
5. AI module entitlement
6. Quota policy
7. Knowledge access
8. Explicit grants or denials
9. Temporary overrides

The UX must show inherited access separately from explicit access. Super Admins should never need to infer why a user can or cannot perform an action.

## Permission Types

| Type | Example | UX Treatment |
| --- | --- | --- |
| Platform permission | Manage system settings | Role Builder and Permission Matrix |
| Object permission | Edit department users | User Detail and Department Management |
| Module entitlement | Enable AI drafting capability | AI Module Management |
| Quota allowance | 5,000 requests per month | Quota Editor |
| Knowledge scope | Access Operations Runbooks | Knowledge Access |
| Identity capability | Use external AI signature | Professional AI Identity |
| Override | Temporary extra quota | Time-bound override drawer |

## Access Labels

Use these labels consistently:

- Granted
- Denied
- Inherited
- Explicit grant
- Explicit denial
- Scoped
- Pending approval
- Expired
- Suspended
- Disabled by policy

## Role And Permission Flow

```text
Select role
  |
  v
Edit permission groups
  |
  v
Preview affected users and modules
  |
  v
Resolve conflicts
  |
  v
Confirm high-risk permissions
  |
  v
Save role
  |
  v
Audit event recorded
```

High-risk permissions:

- Assign Super Admin
- Manage system settings
- Export audit logs
- Grant confidential knowledge access
- Disable audit capture
- Change AI identity external signature behavior
- Raise quota above tenant default

## Module Assignment Flow

```text
Select user, role, or department
  |
  v
Choose AI module
  |
  v
Check dependencies
  |
  v
Check quota policy
  |
  v
Check knowledge requirements
  |
  v
Preview affected users
  |
  v
Save assignment
```

Module assignment screen requirements:

- Show module status, dependency status, quota impact, and Professional AI Identity requirements.
- Prevent enabling modules when prerequisites are unsatisfied unless an override workflow exists.
- Distinguish "module visible" from "module usable".
- Show usage and audit history per module.

## Quota Flow

```text
Open quota policy
  |
  v
Review usage trend
  |
  v
Adjust limit or policy
  |
  v
Preview affected users and reset behavior
  |
  v
Confirm if limit increases risk or spend
  |
  v
Save quota
```

Quota display model:

- Remaining
- Used
- Reset date
- Burst status
- Module breakdown
- Inherited policy
- Temporary override
- Approval state

## Knowledge Access Flow

```text
Select target
  |
  v
Inspect inherited knowledge
  |
  v
Grant or revoke collections
  |
  v
Preview reachable documents
  |
  v
Review sensitivity warnings
  |
  v
Save access
```

Knowledge access must disclose:

- Collection name
- Source of access
- Sensitivity level
- Document count
- Chunk count
- Last indexed time
- Whether access applies to AI retrieval, human browsing, or both

## Conflict UX

Conflict examples:

- Role grants access, explicit denial blocks it.
- Department grants collection access, tenant policy blocks sensitivity level.
- Module entitlement exists, quota is zero.
- User can access Knowledge, but Professional AI Identity is not ready.

Conflict presentation:

```text
Access conflict
Role grants an advanced AI analysis capability, but the user lacks the required knowledge retrieval entitlement.

Current result: AI analysis unavailable
Resolution: Enable the required knowledge entitlement, remove the analysis capability, or assign a role with the required bundle.
```

## Permission Matrix Rules

- Matrix columns represent roles or selected users.
- Matrix rows represent permissions grouped by product area.
- Cells use text labels, not color alone.
- Clicking a cell opens its source, dependencies, and affected users.
- Export preserves filters and includes timestamp and actor.
- Read-only auditors can inspect but cannot mutate matrix values.

## Change Impact Summary

Every permission-changing action should include:

- Actor
- Target
- Change type
- Before value
- After value
- Affected users
- Affected modules
- Affected knowledge scopes
- Quota or cost impact
- Required confirmation reason

## Privacy Boundaries

Super Admins can manage access but should not receive unnecessary content exposure.

Rules:

- Permission previews may show collection names, sensitivity, counts, and policy metadata.
- Permission previews should not reveal restricted document content to admins who lack content-view permission.
- Audit logs should show action metadata and object identifiers, but sensitive payload values should be redacted when policy requires.
- Professional AI Identity profiles expose business identity controls, not private personal data.
- Quota screens show usage metrics, not private prompt contents.
