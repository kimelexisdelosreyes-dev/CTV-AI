# 07 - Workspace Architecture

## Definition

Workspace is the default employee home. It is not a generic dashboard. It answers:

- What matters today?
- What should I continue?
- What requires attention?
- What can CTV ONE help with?
- What changed since my last session?

## Recommended Priority Order

1. Personalized greeting and daily context
2. Continue Working
3. Today's Priorities
4. My AI briefing
5. Quick Actions
6. Active or recent projects
7. Recommended knowledge
8. Announcements
9. Calendar or scheduled activity
10. AI jobs or recent activity
11. System status, only when relevant

## Module Visibility

- Executive Producer: approvals, active productions, blockers.
- Writer: drafts, source documents, review requests.
- Editor: active edit tasks, files, transcripts, AI jobs.
- Multimedia or Graphic Artist: briefs, brand assets, versions, approvals.
- Marketing and Sales: campaigns, opportunities, approved messaging.
- Admin: access alerts, user tasks, audit events, system notices.

## States

| State | Behavior |
| --- | --- |
| First login | Guided setup, My AI profile, required knowledge |
| Returning user | Continue work and changes since last session |
| No active project | Suggest templates, knowledge, or assigned actions |
| AI unavailable | Keep work modules, disable AI actions with explanation |
| Knowledge unavailable | Keep projects/files, show knowledge recovery state |
| Permission-aware | Hide inaccessible modules and actions |
| Loading | Stable skeleton modules |
| Empty | Role-specific next action, not generic blank dashboard |

## Mobile Priority

Mobile Workspace shows:

1. Urgent tasks or approvals
2. Continue Working
3. AI job status
4. Recent project
5. Knowledge search
6. Notifications

