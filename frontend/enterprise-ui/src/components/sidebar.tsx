"use client";

import {
  Bot,
  Brain,
  BookOpen,
  Files,
  Gauge,
  LayoutDashboard,
  LogOut,
  Settings,
  Users,
  Workflow,
} from "lucide-react";
import { AppSidebar, SidebarItem, SidebarSection } from "@/design-system";

export type Section =
  | "overview"
  | "assistants"
  | "brain"
  | "knowledge"
  | "operations"
  | "files"
  | "infrastructure";

type Props = {
  active: Section;
  onChange: (section: Section) => void;
  onLogout: () => void;
};

const items = [
  { id: "overview" as const, label: "Workspace", icon: LayoutDashboard },
  { id: "assistants" as const, label: "AI Studio", icon: Bot },
  { id: "brain" as const, label: "My AI", icon: Brain },
  { id: "knowledge" as const, label: "Knowledge Center", icon: BookOpen },
  { id: "operations" as const, label: "Projects", icon: Workflow },
  { id: "files" as const, label: "Files", icon: Files },
  { id: "infrastructure" as const, label: "Enterprise Control Center", icon: Gauge },
];

export function Sidebar({ active, onChange, onLogout }: Props) {
  return (
    <AppSidebar>
      <div className="brand-lockup">
        <div className="brand-mark">C</div>
        <div>
          <strong>CTV ONE</strong>
          <span>Enterprise AI</span>
        </div>
      </div>

      <SidebarSection label="CTV ONE product areas">
        {items.map(({ id, label, icon: Icon }) => (
          <SidebarItem
            active={active === id}
            icon={<Icon size={18} />}
            key={id}
            label={label}
            onClick={() => onChange(id)}
          />
        ))}
      </SidebarSection>

      <div className="sidebar-spacer" />

      <div className="future-nav">
        <span><Users size={15} /> Employees</span>
        <span><Settings size={15} /> Settings</span>
      </div>

      <SidebarItem icon={<LogOut size={18} />} label="Sign out" onClick={onLogout} />
    </AppSidebar>
  );
}
