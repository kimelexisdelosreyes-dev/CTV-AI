# 14 - Motion Guidelines

## Principle

Motion should feel calm and functional. It should clarify change, not entertain.

## Durations

| Motion | Duration |
| --- | --- |
| Hover feedback | 100-150 ms |
| Focus transition | 100-150 ms |
| Card expand/collapse | 180-220 ms |
| Drawer or sheet open | 200-260 ms |
| Module refresh fade | 150-220 ms |
| Loading shimmer, if used | 900-1200 ms cycle |

## Patterns

- Fade for content refresh.
- Subtle slide for drawers and sheets.
- Small elevation change for hover.
- No bouncy movement.
- No neon glow.
- No rapid pulsing.

## Reduced Motion

When reduced motion is enabled:

- Replace slides with instant or fade-only transitions.
- Disable shimmer.
- Avoid animated progress except textual updates.
- Preserve all state changes.

## Module Refresh

Modules should refresh in place. Avoid whole-page jumps. Preserve scroll position unless the user explicitly navigates.

