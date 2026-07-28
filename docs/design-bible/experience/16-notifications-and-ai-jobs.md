# 16 - Notifications And AI Jobs

## Notifications

Notifications are grouped by meaning:

- AI Jobs
- Projects
- Approvals
- Knowledge
- Announcements
- Security
- System

Notification behavior:

- Priority levels: critical, high, normal, low.
- Read/unread state is per user.
- Toasts are for immediate feedback only.
- Required announcements may need acknowledgement.
- Deep links open authorized detail pages.
- Deduplication prevents noisy repeated alerts.
- Quiet hours suppress non-critical notifications.
- Role-aware relevance prevents unnecessary noise.

## AI Job Center

AI jobs track long-running AI work.

States:

- Draft
- Queued
- Preparing
- Running
- Waiting for input
- Completed
- Completed with warning
- Failed
- Cancelled
- Expired

Job fields:

- Job name
- Capability
- Project
- Owner
- Start time
- Duration
- Progress
- Output
- Quota usage
- Cancel, retry, duplicate, open output, save to project, download, report issue

Technical infrastructure status appears only for authorized technical administrators.

