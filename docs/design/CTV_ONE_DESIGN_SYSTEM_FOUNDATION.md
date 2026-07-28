# CTV ONE Design System Foundation

Sprint: 2.0.1 UX Foundation and Information Architecture  
Scope: Design-only foundation for the CTV ONE Enterprise Portal, starting with Super Admin IAM.  
Status: Ready for product and engineering review.

## Existing Frontend Review

The current enterprise UI is a Next.js single-page shell located in `frontend/enterprise-ui/src`. It uses a dark operational interface, left sidebar navigation, compact cards, tables, panels, and a strong orange brand accent.

Current implemented navigation:

- Workspace
- Knowledge
- AI Studio
- Projects
- Files
- Professional AI Identity
- Future placeholders: Employees and Settings

Current visual language:

- Dark base: near-black application background with darker sidebar
- Panels: dark gray cards with light borders
- Accent: CTV orange for brand, active states, primary actions, and key signals
- Typography: system sans stack with Inter preference
- Layout: persistent sidebar on desktop, compact icon navigation on mobile
- Component shape: rounded panels and controls, currently larger than the long-term admin standard

Design implications:

- The portal already reads as an enterprise operations product, not a marketing surface.
- Super Admin IAM should extend the existing sidebar and panel grammar instead of introducing a new product frame.
- Administration experiences should be denser, more tabular, and more stateful than the current overview and assistant surfaces.
- The current one-page section-switching model can support Sprint 2.0.1 wireframes, but future implementation may need route-level URLs for deep links, audit review, and admin object pages.

## Product Principles

1. Control without confusion
   Super Admins must understand exactly what a permission, quota, module, or knowledge scope changes before saving.

2. Least privilege by default
   New users receive minimal access until role, department, module, quota, and knowledge assignments are explicitly reviewed.

3. Explainable enterprise AI
   AI responses, professional identity behavior, and knowledge visibility should disclose provenance, routing, and policy boundaries.

4. Fast repeated administration
   Bulk actions, filters, saved views, and copy-from-existing patterns are first-class because Super Admins perform repeated account work.

5. Separation of identity, access, and behavior
   User profile, authentication state, role permissions, module entitlement, quota allocation, knowledge access, and AI identity must be visible as distinct but related concerns.

6. Auditability everywhere
   Every meaningful admin change must expose actor, target, before/after state, timestamp, reason when required, and downstream effect.

7. Professional, not playful
   CTV ONE should feel precise, calm, secure, and executive-ready. Use motion sparingly and reserve expressive UI for AI state feedback.

## Visual Foundation

### Color Tokens

| Token | Value | Use |
| --- | --- | --- |
| `bg.default` | `#090b0e` | Application background |
| `surface.sidebar` | `#0c0f13` | Global navigation |
| `surface.panel` | `#12161b` | Primary panels |
| `surface.raised` | `#191f26` | Inputs, nested tool regions, selected rows |
| `border.default` | `#28313b` | Dividers and table rules |
| `text.primary` | `#f5f7fa` | Main text |
| `text.secondary` | `#9ca8b5` | Supporting text |
| `brand.orange` | `#ff7a1a` | Primary action and CTV brand signal |
| `brand.orange.soft` | `rgba(255, 122, 26, 0.12)` | Active navigation and subtle highlights |
| `status.success` | `#55d693` | Healthy, enabled, successful |
| `status.danger` | `#ff6d78` | Error, revoked, destructive |
| `status.warning` | `#f5b84b` | Limit approaching, pending review |
| `status.info` | `#6ab7ff` | Informational system state |

### Type Scale

| Role | Desktop | Mobile | Use |
| --- | --- | --- | --- |
| Page title | 34-42 px | 28-32 px | Primary object or module title |
| Section title | 20-24 px | 18-22 px | Panel group heading |
| Table header | 12-13 px | 12 px | Dense administrative tables |
| Body | 14-15 px | 14 px | Default content |
| Metadata | 12-13 px | 12 px | IDs, timestamps, secondary labels |
| Control label | 12 px | 12 px | Forms and settings |

Type rules:

- Keep letter spacing at 0 except short uppercase eyebrow labels.
- Avoid viewport-scaled text in admin tools.
- Do not use hero-scale type inside admin panels.
- Truncate object names only when the full value is available on hover or in detail view.

### Spacing

| Token | Value | Use |
| --- | --- | --- |
| `space.1` | 4 px | Icon gaps, dense metadata |
| `space.2` | 8 px | Button icon gaps, compact rows |
| `space.3` | 12 px | Input padding, table cells |
| `space.4` | 16 px | Panel internal spacing |
| `space.5` | 20 px | Toolbar groups |
| `space.6` | 24 px | Page block rhythm |
| `space.8` | 32 px | Major page sections |

### Shape

- Admin panels and cards: 8 px radius target.
- Inputs, menus, and buttons: 8 px radius target.
- Modals: 8 px radius with clear header, body, footer separation.
- Pills: fully rounded only for compact status, role, and scope indicators.

The current frontend uses 10-20 px radii. Future admin implementation should move IAM surfaces toward 8 px while avoiding unrelated restyling of existing production sections.

## Interaction Principles

- Primary actions appear once per task region.
- Destructive actions are never the default focus and require confirmation when they affect access, identity, quota, or knowledge visibility.
- Permission changes should preview impact before save.
- Bulk changes must include dry-run counts and affected user lists.
- Disabled controls must explain why they are unavailable.
- Unsaved changes must survive accidental tab changes inside admin detail pages until the user saves, discards, or exits.

## State Model

Every admin surface needs explicit states:

- Empty: no objects or no matching filters.
- Loading: skeleton table rows and disabled toolbar controls.
- Ready: full object list or form state.
- Partial: data loaded but dependent system state unavailable.
- Error: retryable state with service name and correlation ID if available.
- Dirty: unsaved local edits.
- Saving: optimistic only for reversible edits; blocking for access and identity mutations.
- Saved: timestamped confirmation.
- Conflict: show changed fields, current server value, proposed value, and merge action.
- Permission denied: explain missing permission without revealing restricted content.

## Component Inventory

### Global

- App shell
- Persistent sidebar
- Mobile rail or bottom command bar
- Page header
- Breadcrumb
- Global search entry
- Notification center
- Account menu
- Environment badge
- Tenant switcher, future multi-tenant capable

### IAM

- User table
- User status badge
- User detail header
- Create user wizard
- Department tree
- Department member list
- Role table
- Role builder
- Permission matrix
- Module assignment checklist
- Quota editor
- Knowledge scope selector
- Professional AI Identity profile card
- Access preview panel
- Change impact summary
- Audit timeline
- Reason-for-change prompt
- Bulk action drawer

### Inputs And Controls

- Text input
- Email input
- Search box
- Select
- Combobox
- Checkbox
- Toggle
- Segmented control
- Slider
- Numeric stepper
- Date range picker
- Filter chips
- Tab list
- Data table column menu
- Overflow action menu
- Confirmation dialog
- Toast
- Inline alert

### AI-Specific

- Agent/module entitlement card
- Professional identity status badge
- AI capability disclosure row
- Knowledge provenance row
- Routing confidence indicator
- Quota consumption meter
- Sensitive-data boundary notice
- Policy override request drawer

## Content Voice

CTV ONE speaks in clear operational language:

- Use direct labels: "Create user", "Assign modules", "Suspend access".
- Avoid vague AI phrasing such as "unlock intelligence" in admin workflows.
- Explain consequences in plain terms: "This removes an AI drafting capability from 14 users."
- Use "disabled", "suspended", "revoked", and "archived" consistently.
- Prefer "knowledge access" over "brain permissions" in IAM contexts.

## Design Governance

New admin screens must pass these checks before build:

- Does the screen identify the object being changed?
- Does it show current access state?
- Does it separate role permissions from module assignment?
- Does it expose knowledge scope boundaries?
- Does it require confirmation for irreversible or high-risk actions?
- Does it show an audit trail or link to one?
- Does the layout work at 1440, 1024, 768, and 390 px widths?
- Does keyboard navigation cover every interactive element?
