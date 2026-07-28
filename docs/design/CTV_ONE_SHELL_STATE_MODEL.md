# CTV ONE Shell State Model

Sprint: Phase 2.0.3A Master Application Frame  
Scope: Application frame behavior across normal, exceptional, and permission-changing states.

## Principle

The shell should isolate failures. A single service failure must not disable unrelated product areas.

## Shell States

| State | Behavior |
| --- | --- |
| Normal | Full permitted navigation and top-bar controls available |
| Loading | Frame skeleton loads first, then page content |
| Offline | Keep frame, show offline notice, disable network actions |
| Degraded service | Show scoped banner and keep unaffected areas available |
| Permission changed | Refresh effective navigation and explain changes |
| Session expiring | Modal warning with stay signed in and sign out |
| Maintenance | Show affected area and expected recovery if available |
| No organization assigned | Show limited profile/settings recovery state |
| Account suspended | Remove app access and show suspension message |
| Mobile navigation open | Trap focus in nav sheet and restore on close |
| Universal search open | Trap focus in search overlay and restore on close |
| Notification drawer open | Trap focus in drawer and restore on close |
| AI job drawer open | Trap focus in drawer and restore on close |

## Loading State

```text
+--------------------------------------------------------------------------------+
| Sidebar skeleton        | Top bar skeleton                                      |
|-------------------------|------------------------------------------------------|
|                         | Page header skeleton                                 |
|                         | Content skeleton                                     |
+--------------------------------------------------------------------------------+
```

Rules:

- Load shell before content when authentication is valid.
- Keep navigation placeholders stable.
- Do not show unauthorized nav while permissions are loading.

## Offline State

Behavior:

- Show offline banner.
- Keep visible recent page context if already loaded.
- Disable submit, save, generation, upload, and approval actions.
- Allow sign out and local preferences.

## Degraded Service

Behavior:

- Show service-neutral product message.
- Identify affected product area, not internal service name.
- Keep unrelated navigation active.
- Provide retry or details only when useful.

Example:

```text
Knowledge search is delayed. Workspace, Projects, Files, and Settings remain available.
```

## Permission Changed

Behavior:

- Refresh effective permissions.
- Remove hidden navigation items.
- If current page is no longer allowed, redirect to Workspace with an explanation.
- Close unauthorized drawers and modals.
- Keep safe notification: "Your access changed. Some pages may no longer be available."

## Session Expiring

Behavior:

- Warn before expiration.
- Preserve unsaved page state where possible.
- Provide Stay signed in and Sign out actions.
- Restore route after successful re-auth when allowed.

## Maintenance

Behavior:

- Product-facing label: "Scheduled maintenance".
- Show affected areas.
- Do not expose deployment, server, or infrastructure labels to ordinary users.
- Admins may see a link to technical status if permitted.

## No Organization Assigned

Behavior:

- Show a limited shell with profile menu and sign out.
- Explain that access requires organization assignment.
- Provide contact admin path if configured.

## Account Suspended

Behavior:

- Block application shell.
- Show account suspended message.
- Provide sign out.
- Do not expose prior navigation, notifications, jobs, or search results.

## Drawer And Overlay State Rules

- Only one global overlay can be primary at a time.
- Opening search closes notification and job drawers.
- Opening notification drawer closes job drawer.
- Dirty contextual drawers prompt before close.
- Focus restoration always targets the invoking control or nearest valid replacement.

## State Validation Checklist

- Single product-area failure does not break shell.
- Permission updates do not leak removed navigation.
- Search results clear when permissions change.
- Notifications and jobs refresh after scope changes.
- Session modal is keyboard accessible.
- Offline state prevents mutation.
- Account suspended state hides app content.

