# CTV ONE Design System v1.0 Migration Notes

## Repository Audit

Frontend stack:

- Next.js 16 App Router.
- React 19.
- TypeScript strict mode.
- Plain global CSS.
- Lucide React icons.
- Node test runner for lightweight tests.
- No Tailwind configuration.
- No Storybook.
- No theme provider.

Existing component architecture:

- `src/app/page.tsx` owns authentication state and switches between section components.
- `components/sidebar.tsx` owns current navigation items.
- Feature components own much of their own markup and class names.
- Styling is spread through `globals.css`, `knowledge-center.css`, and `operations-workspace.css`.

Issues discovered:

- Colors, radius, spacing, and shadows were hardcoded in global and feature CSS.
- Buttons, cards, badges, inputs, and panels used repeated class patterns.
- Current navigation labels are older product terms in several screens.
- The app has no dedicated shared UI component foundation.
- Responsive behavior exists but is page-specific.

## Implemented Foundation

Added:

- Token constants in `src/design-system/tokens/index.ts`.
- CSS token layer in `src/design-system/tokens/tokens.css`.
- Shared component styles in `src/design-system/design-system.css`.
- Typed reusable components in `src/design-system/components`.
- Barrel exports in `src/design-system/index.ts`.
- Showcase route at `/design-system`.

## Representative Migration

Migrated:

- Global CSS now maps legacy variables to semantic design-system tokens.
- Sidebar uses `AppSidebar`, `SidebarSection`, and `SidebarItem`.
- Overview uses `PageShell`, `PageHeader`, `MetricCard`, `HealthCard`, `StatusBadge`, `AIRecommendationCard`, and `EmptyState`.

## Sprint 2.2A Module Migration Table

| Module | Files modified | Design-system components adopted | Behavior preserved | Remaining limitation |
| --- | --- | --- | --- | --- |
| Workspace | `components/overview.tsx` | `PageShell`, `PageHeader`, `MetricCard`, `HealthCard`, `StatusBadge`, `AIRecommendationCard`, `EmptyState` | Existing knowledge and health stats loading | Still a lightweight Workspace, not the full Sprint 3.0.2 cockpit |
| AI Studio | `components/assistants.tsx` | `PageShell`, `PageHeader`, `ResponsiveGrid`, `AIRecommendationCard`, `PrimaryButton`, `StatusBadge`, `EmptyState` | Existing section remains reachable | Capability cards are static until real AI Studio workflows exist |
| Knowledge Center | `components/knowledge-center.tsx` | `PageShell`, `PageHeader`, `BaseCard`, `ResponsiveGrid`, `SearchInput`, `Select`, `PrimaryButton`, `SecondaryButton`, `StatusBadge`, `InlineAlert`, `LoadingSkeleton`, `EmptyState` | Collections, document search, upload, refresh, delete | File input remains native for browser compatibility |
| Projects | `components/operations-workspace.tsx` | `PageShell`, `PageHeader`, `PrimaryButton`, `MetricCard`, `SearchInput`, `StatusBadge`, `SyncStatus`, `InlineAlert`, `LoadingSkeleton`, `EmptyState` | Monday.com snapshot, refresh, filters, table, outbound links | Dense table and side panels retain compatibility CSS |
| Files | `components/files-workspace.tsx`, `app/page.tsx`, `components/sidebar.tsx` | `PageShell`, `PageHeader`, `SearchInput`, `FileLocationCard`, `StorageSourceBadge`, `WorkstationBadge`, `ArchiveBadge`, `EmptyState` | No existing file API behavior changed | Empty-state only until Enterprise File Discovery is implemented |
| My AI | `components/company-brain.tsx` | `PageShell`, `PageHeader`, `BaseCard`, `Select`, `TextArea`, `Checkbox`, `PrimaryButton`, `SecondaryButton`, `AIThinkingPanel`, `AIConfidenceBadge`, `AISourceReference`, `InlineAlert`, `EmptyState`, `LoadingSkeleton` | Conversation streaming, recents, rename, archive, delete, collection routing | Message bubbles retain small legacy chat classes for readability |
| Enterprise Control Center | `components/infrastructure.tsx` | `PageShell`, `PageHeader`, `SystemHealthSummary`, `AIServiceNode`, `InlineAlert`, `EmptyState`, `ResponsiveGrid` | Existing infrastructure health and admin developer console | Technical admin console remains legacy |

## Legacy CSS Exceptions

| File | Selector or area | Reason retained | Future removal |
| --- | --- | --- | --- |
| `src/app/globals.css` | Legacy `.panel`, `.metric-card`, form, table, chat classes | Still used by Company Brain message bubbles, Developer Console, and older feature internals | Remove after full feature-level component migration |
| `src/app/knowledge-center.css` | `.knowledge-layout`, `.knowledge-library-heading`, `.knowledge-document-list` | Layout compatibility for upload/library split after component migration | Fold into design-system layout utilities after visual QA |
| `src/app/operations-workspace.css` | Table, toolbar, board filters, priority chips | Dense Monday.com table and board filters need specialized behavior | Replace with table/list primitives in Sprint 2.3 or later |
| `src/components/developer-console.tsx` styles in `globals.css` | Developer console classes | Admin-only technical surface outside primary employee modules | Migrate when Enterprise Control Center technical admin view is redesigned |

Still legacy:

- Company Brain conversation UI.
- Company Brain message bubble internals.
- Operations Workspace dense table internals.
- Infrastructure details page.
- Developer console and performance dashboards.
- Login form visual classes.

## Developer Guidance

- Import components from `@/design-system`.
- Use semantic tokens instead of hardcoded colors.
- Prefer composition with `BaseCard` for new cards.
- Use `StatusBadge`, `ProgressBar`, and `InlineAlert` for system state.
- Keep module accents subtle: icons, selected borders, focus, progress, and small highlights.
- Do not expose backend implementation names in employee-facing components.
