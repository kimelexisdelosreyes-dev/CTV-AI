export const moduleAccents = {
  workspace: "var(--ctv-accent-workspace)",
  aiStudio: "var(--ctv-accent-ai-studio)",
  knowledge: "var(--ctv-accent-knowledge)",
  files: "var(--ctv-accent-files)",
  projects: "var(--ctv-accent-projects)",
  myAi: "var(--ctv-accent-my-ai)",
  operations: "var(--ctv-accent-operations)",
} as const;

export const statusTokens = {
  healthy: "var(--ctv-status-healthy)",
  processing: "var(--ctv-status-processing)",
  warning: "var(--ctv-status-warning)",
  critical: "var(--ctv-status-critical)",
  offline: "var(--ctv-status-offline)",
  neutral: "var(--ctv-status-neutral)",
} as const;

export const spacing = {
  1: "4px",
  2: "8px",
  3: "12px",
  4: "16px",
  6: "24px",
  8: "32px",
  12: "48px",
  16: "64px",
  24: "96px",
} as const;

export const radius = {
  button: "10px",
  input: "12px",
  card: "16px",
  dialog: "20px",
  hero: "24px",
  pill: "999px",
} as const;

export const motion = {
  instant: "90ms",
  fast: "150ms",
  buttonPress: "100ms",
  hover: "150ms",
  searchOpen: "200ms",
  fade: "250ms",
  expand: "300ms",
  notification: "250ms",
  cardExpand: "300ms",
  pageTransition: "325ms",
  emphasized: "425ms",
  easeStandard: "cubic-bezier(.2, 0, 0, 1)",
  easeEnter: "cubic-bezier(0, 0, .2, 1)",
  easeExit: "cubic-bezier(.4, 0, 1, 1)",
  easeEmphasized: "cubic-bezier(.2, 0, 0, 1)",
} as const;

export type ModuleAccent = keyof typeof moduleAccents;
export type StatusTone = keyof typeof statusTokens;
