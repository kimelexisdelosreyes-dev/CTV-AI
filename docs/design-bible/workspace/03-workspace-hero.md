# 03 - Workspace Hero

## Purpose

The hero is the daily cockpit. It answers the five-second questions before the user scrolls.

## Anatomy

- Greeting.
- Daily context.
- Resume button.
- Project summary.
- AI summary.
- Pending approvals.
- Relevant knowledge.
- Suggested next action.

## Visual Hierarchy

1. Greeting and location label.
2. Suggested next action.
3. Resume button.
4. Project and approval summary.
5. AI and knowledge supporting context.

## Card Anatomy

```text
+--------------------------------------------------------------------------------+
| Good morning, Mina.                                      Workspace              |
| You have 2 approvals, 1 completed AI job, and a script review due today.         |
|                                                                                |
| Suggested next action                                                           |
| Review subtitles for Fire Documentary                                           |
| [Resume review]                                      Project: Fire Documentary  |
|                                                                                |
| AI completed subtitle generation. 3 archive photos still need selection.         |
+--------------------------------------------------------------------------------+
```

## Priority Rules

Hero chooses one primary suggested action by evaluating:

1. Urgent approval.
2. Deadline today.
3. Blocked teammate.
4. Recently paused work.
5. Completed AI job needing review.
6. Required reading.
7. Recommended project continuation.

## Spacing

- Desktop hero height: 25-30 percent viewport.
- Internal padding: 28-40 px.
- Primary action gap: 16-20 px from suggested action text.
- Metadata row: 12 px vertical rhythm.

## Behavior

- Hero never shows more than one primary CTA.
- Secondary items are compact links or chips.
- Dismissed suggestions move to Continue Working or Timeline if still relevant.
- Hero updates after completed actions without page reload.

## States

| State | Hero Behavior |
| --- | --- |
| Empty | "You're set for now" plus useful exploration action |
| Returning user | Resume-oriented, shows changes since last session |
| First login | Orientation, professional setup, required knowledge |
| Busy day | Approval/deadline-first |
| Quiet day | Learning, cleanup, and recommended knowledge |

