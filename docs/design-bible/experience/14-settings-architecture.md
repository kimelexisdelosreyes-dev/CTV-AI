# 14 - Settings Architecture

## Split Settings Model

Settings are split into User Settings and System Settings.

User Settings are personal. System Settings require explicit permission.

## User Settings Routes

| Route | Label |
| --- | --- |
| `/settings/profile` | Profile |
| `/settings/notifications` | Notifications |
| `/settings/appearance` | Appearance |
| `/settings/language` | Language |
| `/settings/accessibility` | Accessibility |
| `/settings/security` | Security |
| `/settings/connected-accounts` | Connected Accounts |
| `/settings/sessions` | Sessions |
| `/settings/privacy` | Privacy |

## System Settings Routes

| Route | Label |
| --- | --- |
| `/admin/settings/organization` | Organization |
| `/admin/settings/branding` | Branding |
| `/admin/settings/authentication` | Authentication |
| `/admin/departments` | Departments |
| `/admin/roles` | Roles |
| `/admin/permissions` | Permissions |
| `/admin/knowledge-spaces` | Knowledge |
| `/admin/settings/ai-services` | AI Services |
| `/admin/storage` | Storage |
| `/admin/integrations` | Integrations |
| `/admin/quotas` | Quotas |
| `/admin/audit` | Audit |
| `/admin/security` | Security |
| `/admin/settings/retention` | Retention |
| `/admin/settings/backups` | Backups |

## Labeling Rule

- Employee nav label: Settings
- Admin nav label: System Settings
- Formal distinction: User Settings versus System Settings

