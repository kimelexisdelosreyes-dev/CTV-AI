# 21 - Open Design Decisions

| Decision | Context | Options | Recommended Direction | Tradeoffs | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| My AI vs Professional AI Identity | Navigation needs friendly language and formal governance | My AI, Professional AI Identity, My Professional AI | Use My AI in nav and Professional AI Identity as formal page/feature name | Friendlier nav, requires clear page title | Product/Design | Recommended |
| Files primary or utility | Files can be global and project-centered | Primary nav, project-only, both | Use primary Files plus project file context | More nav weight, clearer access | Product | Open |
| AI Jobs placement | Jobs are cross-product background work | Primary nav, top-bar utility, AI Studio subsection | Use top-bar utility plus `/ai-jobs` route | Discoverable without clutter | Product/Design | Recommended |
| Projects tasks vs Monday.com | Existing operations may sync external tasks | Native tasks, integration-only, hybrid | Hybrid with project tasks and integration references | Requires careful source labels | Product/Engineering | Open |
| Knowledge approval | Contributions may need governance | Always required, by space, optional | Require by Knowledge Space policy | Safer, slower publishing | Product/Admin | Recommended |
| Temporary access | Users may need time-limited access | No, yes by approval, admin only | Allow approved temporary access | Adds governance complexity | Security/Product | Open |
| Project templates v1 | Templates speed ChinoyTV workflows | Include v1, later, admin-only | Include core templates if feasible | More upfront design/build | Product | Open |
| Workspace module ordering | Employees may prefer control | Fixed, role default, user customizable | Role default plus optional user reorder | Personalization complexity | Design/Product | Open |
| Mobile administration | Admins may need urgent actions | None, urgent subset, full | Urgent subset only | Avoids poor dense UI | Product | Recommended |
| Export Professional AI Identity | Users own profile | No export, JSON export, readable export | Allow readable export | Privacy and data portability benefit | Legal/Product | Open |
| Admin profile completion visibility | Admins may need onboarding completion | View completion only, view fields, no visibility | Completion only | Protects privacy | Product/Security | Recommended |
| Archived project search | Historical context matters | Searchable, hidden, admin only | Searchable if permissioned | More result complexity | Product | Open |
| Generated assets become knowledge | Outputs may be reusable | Never, automatic, publish flow | Publish flow required | Better governance | Product/Knowledge Owner | Recommended |
| Employee directory in search | People search helps collaboration | All users, scoped, admin only | Scoped by organization policy | Balances utility/privacy | Product/Security | Open |

