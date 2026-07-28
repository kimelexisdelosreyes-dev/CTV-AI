# 19 - Application States

## Shared States

| State | What happened | User can do | Work safety | Retry |
| --- | --- | --- | --- | --- |
| Initial load | App is starting | Wait | Safe | Automatic |
| Skeleton loading | Data is loading | Wait or navigate if shell ready | Safe | Automatic |
| Empty | No content exists | Create or follow guidance | Safe | Not needed |
| Partial data | Some services loaded | Use available areas | Safe | Retry affected area |
| Offline | Network unavailable | View cached context if supported | Unsaved local work should persist | Yes |
| Storage unavailable | Files cannot be reached | Use non-file areas | Existing work safe | Yes |
| AI unavailable | AI actions disabled | Continue manual work | Inputs safe | Yes |
| Knowledge unavailable | Knowledge search delayed | Use projects/files | Work safe | Yes |
| Permission denied | Access not available | Request access or go elsewhere | Safe | No, unless permission changes |
| Session expired | Auth ended | Sign in again | Preserve unsaved work when possible | Yes |
| Rate limited | Too many requests | Wait or reduce action | Safe | Later |
| Quota reached | AI allowance used | Request quota or wait reset | Safe | After quota change |
| Maintenance | Area unavailable | Use unaffected areas | Safe | Later |
| Update available | New app version | Refresh when ready | Warn about unsaved changes | User choice |
| Error with retry | Recoverable failure | Retry | Safe if no save committed | Yes |
| Error without retry | Non-recoverable | Contact support or return | Explain | No |
| Read-only mode | Mutation disabled | View content | Safe | Later |
| Archived resource | Object no longer active | View or restore if permitted | Safe | No |
| Deleted resource | Object removed | Return or recover if permitted | Safe | No |
| Unsaved changes | Local edits pending | Save, discard, continue editing | At risk if leaving | Not applicable |

## Application State Rule

A single service failure must not disable unrelated product areas.

