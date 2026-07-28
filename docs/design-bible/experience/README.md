# Sprint 3.0.1 - Experience Map & Information Architecture

CTV ONE is an Enterprise AI Operating System for employees, organizational knowledge, projects, files, AI capabilities, and enterprise administration.

This sprint is documentation-only. It does not implement routes, components, APIs, migrations, dependencies, or backend behavior.

## Current Repository Review

Existing frontend application:

- Path: `frontend/enterprise-ui/src`
- Framework: Next.js App Router with one implemented route at `src/app/page.tsx`
- Current shell: authenticated single-page app with component-switched sections
- Current auth: `Login` component posts through `login()` and then loads `/auth/me`
- Current user model in frontend: `admin`, `manager`, `employee`
- Current navigation component: `components/sidebar.tsx`
- Current navigation labels: Overview, AI Assistants, Company Brain, Knowledge Center, Operations, Infrastructure
- Current future placeholders: Employees, Settings
- Current knowledge UI: Company Brain conversation and Knowledge Center document management
- Current project-related UI: Operations Workspace uses connector project/task style data, but there is no route-based Projects area
- Current AI UI: AI Assistants, Company Brain, developer AI operations panels for admins
- Current admin pages: no full Administration IA or route tree exists
- Current settings pages: placeholder only, no implemented settings routes
- Current responsive behavior: desktop sidebar collapses to compact icon nav on small screens

Existing design documentation:

- `docs/design/` contains Sprint 2.0.1 and 2.0.3A foundation, IA, frame, navigation, accessibility, and state specs.
- `docs/design-bible/experience/` is the authoritative Sprint 3.0.1 experience blueprint.

## Existing Versus Proposed

| Area | Existing Behavior | Proposed Future Behavior |
| --- | --- | --- |
| Routes | Single `/` application route | Route-based product IA |
| Navigation | Overview, AI Assistants, Company Brain, Knowledge Center, Operations, Infrastructure | Workspace, Knowledge, AI Studio, Projects, Files, My AI, Administration, Settings |
| Administration | Not implemented as product area | Route-based, permissioned administration |
| Projects | Operations-style connector workspace | Project-centered context container |
| Files | No primary product area | Enterprise media and document layer |
| AI | Exposed as assistants and Company Brain | Capability-first AI Studio |
| Settings | Placeholder | Split User Settings and System Settings |

## Documentation Index

1. `01-product-architecture.md`
2. `02-information-architecture.md`
3. `03-navigation-system.md`
4. `04-role-based-workspaces.md`
5. `05-user-journeys.md`
6. `06-screen-relationship-map.md`
7. `07-workspace-architecture.md`
8. `08-ai-studio-architecture.md`
9. `09-project-architecture.md`
10. `10-knowledge-architecture.md`
11. `11-files-architecture.md`
12. `12-professional-ai-identity.md`
13. `13-administration-architecture.md`
14. `14-settings-architecture.md`
15. `15-universal-search.md`
16. `16-notifications-and-ai-jobs.md`
17. `17-permission-experience.md`
18. `18-responsive-experience.md`
19. `19-application-states.md`
20. `20-accessibility-guidelines.md`
21. `21-open-design-decisions.md`

