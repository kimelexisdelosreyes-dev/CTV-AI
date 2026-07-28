# CTV ONE Professional AI Identity UX

Sprint: 2.0.1 UX Foundation and Information Architecture  
Scope: Professional AI Identity model for user representation, authority, behavior, and privacy.

## Purpose

Professional AI Identity defines how CTV ONE represents a user in AI-assisted work. It is not a personal profile, social profile, or unrestricted persona. It is a governed business identity used to route work, phrase outputs, determine permitted authority, and maintain trust.

## Identity Objects

| Object | Description | Example |
| --- | --- | --- |
| Display name | Business name used in AI-generated work | Ada Cruz |
| Job title | Professional role | Operations Administrator |
| Department | Organization context | Operations |
| Manager | Escalation context | Leo Reyes |
| Authority statement | What the user can approve or represent | Can approve dispatch workflow changes |
| Communication defaults | Tone, signature, disclosure preferences | Internal concise tone |
| Module behavior | Which modules may use identity context | Knowledge, Projects |
| External permission | Whether AI may use identity in external-facing output | Disabled by default |
| Review state | Governance status | Draft, Ready, Needs review |

## Identity States

- Draft: created from user profile but incomplete.
- Ready: complete and allowed for internal AI interactions.
- Needs review: changed fields require approval.
- Restricted: identity cannot be used for selected modules.
- Suspended: follows user suspension.
- Archived: retained for audit after user deactivation.

## Professional AI Identity Flow

```text
User created
  |
  v
Identity draft generated
  |
  v
Admin reviews role, department, authority, and module behavior
  |
  v
Sensitive options require approval
  |
  v
Identity marked Ready
  |
  v
AI modules may use professional context within policy
```

## UX Requirements

The identity page must show:

- Current state
- Source of each field
- Last reviewer
- Modules allowed to use identity context
- External-facing status
- Authority limits
- Audit timeline
- Preview of how identity appears in generated work

The page must not show:

- Private prompt content
- Personal notes unrelated to business function
- Hidden employee attributes
- Sensitive HR data unless explicitly authorized

## Boundary Language

Use direct notices:

- "This identity can be used inside CTV ONE only."
- "External-facing AI signatures are disabled."
- "This user can approve Operations workflow changes, not legal commitments."
- "Suspending the user also suspends Professional AI Identity use."

## Review Policy

Require review when:

- Authority statement changes.
- External-facing AI signature is enabled.
- Department or role changes from a source outside the user creation wizard.
- Identity is assigned to a sensitive module.
- The user is granted confidential knowledge access.

## Professional AI Identity Wireframe

```text
+--------------------------------------------------------------------------------+
| Professional AI Identity                                                       |
| Target: Ada Cruz                                      Status: Needs review      |
|                                                                                |
| Business identity                                                              |
| Display name [Ada Cruz]                                                        |
| Title        [Operations Administrator]                                        |
| Department   [Operations]                                                      |
| Manager      [Leo Reyes]                                                       |
|                                                                                |
| Authority                                                                      |
| [Can approve dispatch workflow changes______________________________]          |
| [ ] May represent company externally                                           |
|                                                                                |
| Module use                                                                     |
| [x] Knowledge          [x] Projects        [ ] External communications         |
|                                                                                |
| Preview                                                                        |
| "Ada Cruz, Operations Administrator, can assist with internal dispatch work."   |
|                                                                                |
| [Discard]                                            [Approve identity]         |
+--------------------------------------------------------------------------------+
```

## AI Response Disclosure

When Professional AI Identity influences output, user-facing interfaces should expose:

- Identity used
- Module used
- Knowledge scope used
- Authority boundary
- Generated timestamp

## Privacy And Compliance

Professional AI Identity is governed identity metadata. It should be treated as administrative data:

- Only authorized admins can edit it.
- Auditors can inspect state changes.
- Standard employees can view their own business identity fields when policy allows.
- AI modules can consume identity context only through permissioned server behavior.
- Exported audit logs should include changed fields, not unrelated user content.
