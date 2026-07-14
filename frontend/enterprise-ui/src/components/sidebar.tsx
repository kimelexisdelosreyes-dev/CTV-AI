"use client";

import {
  Bot,
  Brain,
  BookOpen,
  Gauge,
  LayoutDashboard,
  LogOut,
  Settings,
  Users,
  Workflow,
} from "lucide-react";

export type Section =
  | "overview"
  | "assistants"
  | "brain"
  | "knowledge"
  | "operations"
  | "infrastructure";

type Props = {
  active: Section;
  onChange: (section: Section) => void;
  onLogout: () => void;
};

const items = [
  { id: "overview" as const, label: "Overview", icon: LayoutDashboard },
  { id: "assistants" as const, label: "AI Assistants", icon: Bot },
  { id: "brain" as const, label: "Company Brain", icon: Brain },
  { id: "knowledge" as const, label: "Knowledge Center", icon: BookOpen },
  { id: "operations" as const, label: "Operations", icon: Workflow },
  { id: "infrastructure" as const, label: "Infrastructure", icon: Gauge },
];

export function Sidebar({ active, onChange, onLogout }: Props) {
  return (
    <aside className="sidebar">
      <div className="brand-lockup">
        <div className="brand-mark">C</div>
        <div>
          <strong>CTV ONE</strong>
          <span>Enterprise AI</span>
        </div>
      </div>

      <nav>
        {items.map(({ id, label, icon: Icon }) => (
          <button
            className={active === id ? "nav-item active" : "nav-item"}
            key={id}
            onClick={() => onChange(id)}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>

      <div className="sidebar-spacer" />

      <div className="future-nav">
        <span><Users size={15} /> Employees</span>
        <span><Settings size={15} /> Settings</span>
      </div>

      <button className="nav-item logout" onClick={onLogout}>
        <LogOut size={18} /> Sign out
      </button>
    </aside>
  );
}
