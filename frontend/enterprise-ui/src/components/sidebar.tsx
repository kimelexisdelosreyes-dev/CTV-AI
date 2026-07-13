"use client";

import {
  Bot,
  Brain,
  Gauge,
  LayoutDashboard,
  Library,
  LogOut,
  Settings,
  Users,
} from "lucide-react";

export type Section = "overview" | "brain" | "assistants" | "infrastructure";

type Props = {
  active: Section;
  onChange: (section: Section) => void;
  onLogout: () => void;
};

const items = [
  { id: "overview" as const, label: "Overview", icon: LayoutDashboard },
  { id: "assistants" as const, label: "AI Assistants", icon: Bot },
  { id: "brain" as const, label: "Company Brain", icon: Brain },
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
        <span><Library size={15} /> Multimedia</span>
        <span><Users size={15} /> Users</span>
        <span><Settings size={15} /> Settings</span>
      </div>

      <button className="nav-item logout" onClick={onLogout}>
        <LogOut size={18} /> Sign out
      </button>
    </aside>
  );
}
