# CTV ONE Notification And Job Center UX

Sprint: Phase 2.0.3A Master Application Frame  
Scope: Notification center and AI job center behavior in the master frame.

## Separation Decision

CTV ONE should separate notifications from AI jobs.

- Notifications are attention and decision events.
- AI jobs are progress, completion, and background work events.

This keeps the shell from becoming chat-first or alert-heavy while still making long-running AI work visible.

## Notification Center

Notification categories:

- Approvals
- Access changes
- Quota and limits
- Project updates
- File activity
- Knowledge changes
- Session and security
- System notices

Notification drawer wireframe:

```text
+----------------------------------------------+
| Notifications                         [Close] |
| [All] [Unread] [Approvals] [System]           |
|                                              |
| Approval required                             |
| Quota override requested by Ada Cruz          |
| [Review]                                      |
|                                              |
| Knowledge access changed                      |
| Your access to General Policies was updated   |
|                                              |
| Session notice                                |
| MFA settings were updated                     |
+----------------------------------------------+
```

Rules:

- Notifications only reveal content the user can discover.
- Admin notifications include target and action metadata when permitted.
- Sensitive notification payloads use generic copy and link to authorized detail views.
- Read/unread is per user.
- Critical notifications can require acknowledgement.

## AI Job Center

AI job categories:

- Answer preparation
- Knowledge indexing
- File generation
- Project processing
- Approval wait
- Export generation

AI job drawer wireframe:

```text
+----------------------------------------------+
| AI Jobs                               [Close] |
| [Running] [Completed] [Needs action]          |
|                                              |
| Preparing project summary              68%    |
| Started 2 min ago                             |
| [Open] [Cancel]                              |
|                                              |
| Indexing approved knowledge            Queued |
| Workspace remains available                   |
|                                              |
| File export completed                         |
| [Download]                                    |
+----------------------------------------------+
```

Rules:

- Use product-facing job names.
- Do not expose internal queue, model, provider, worker, or service names.
- Jobs should show owner, progress, started time, status, and allowed actions.
- Failed jobs show recovery action and reference ID when available.
- Users see their own jobs; admins see jobs permitted by scope.

## Top Bar Indicators

Notification trigger:

- Badge for unread count.
- Critical state indicator when required.

AI job trigger:

- Progress ring or count for active jobs.
- Needs-action state when a job is blocked.

Do not combine notification count and job count.

## Permission Behavior

| Situation | UX |
| --- | --- |
| User loses access to a linked object | Notification remains generic, link becomes unavailable |
| Job completes for restricted file | Show generic completion if user owns job, hide file metadata |
| Admin loses scope during session | Drawer refreshes and removes unauthorized rows |
| Approval no longer available | Show "No longer available" with safe explanation |

## Drawer Accessibility

- Drawer has accessible name.
- Focus moves to drawer heading or first actionable item.
- Escape closes drawer.
- Focus returns to trigger.
- Tab order stays inside drawer.
- Status updates use live regions when progress changes materially.
- Reduced motion disables progress animations.

## Session Expiry Warning

```text
+----------------------------------------------+
| Session expiring                              |
| Your session will expire soon.                |
| Unsaved changes remain on this page.          |
|                                              |
| [Sign out]                    [Stay signed in]|
+----------------------------------------------+
```

Session rules:

- Warn before expiration.
- Preserve unsaved local state when possible.
- Never hide sign-out.
- Re-auth returns to original route when policy allows.

