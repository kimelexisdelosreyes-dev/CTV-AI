# 15 - Accessibility

## Standard

Target WCAG 2.2 AA. This document defines requirements and does not claim existing implementation compliance.

## Requirements

- Every module is keyboard reachable.
- Focus order follows reading priority: hero, resume, priorities, quick actions, projects, knowledge, timeline.
- Visible focus state is clear on dark and light themes.
- Screen readers can identify module headings and counts.
- Status chips include text and accessible names.
- My AI briefing changes use polite announcements.
- Urgent priority changes use appropriate live-region behavior.
- Reduced motion is honored.
- Touch targets are at least 44 by 44 px.
- Contrast meets AA for body text and controls.
- Empty states and errors are announced.

## Keyboard

- Tab moves through modules and actions.
- Enter activates primary action.
- Escape closes expanded cards, drawers, and overlays.
- Arrow keys may move within horizontal quick actions where implemented.

## Screen Reader Structure

Recommended landmarks:

- Header for shell top bar.
- Navigation for primary nav.
- Main for Workspace.
- Region labels for modules.

