import { ReactNode } from "react";

export function AppSidebar({ children }: { children: ReactNode }) {
  return <aside className="ctv-sidebar">{children}</aside>;
}

export function SidebarSection({ children, label }: { children: ReactNode; label?: string }) {
  return <nav className="ctv-sidebar-section" aria-label={label}>{children}</nav>;
}

export function SidebarItem({
  active,
  icon,
  label,
  badge,
  onClick,
}: {
  active?: boolean;
  icon?: ReactNode;
  label: string;
  badge?: ReactNode;
  onClick?: () => void;
}) {
  return <button className="ctv-sidebar-item" aria-current={active ? "page" : undefined} onClick={onClick}>{icon}{label}{badge}</button>;
}

export function TopNavigation({ children }: { children: ReactNode }) {
  return <header className="ctv-inline" role="banner">{children}</header>;
}

export function Breadcrumbs({ items }: { items: string[] }) {
  return <nav className="ctv-breadcrumbs" aria-label="Breadcrumb">{items.map((item, index) => <span key={`${item}-${index}`}>{index > 0 ? "/ " : ""}{item}</span>)}</nav>;
}

export function ModuleTabs({ tabs, active }: { tabs: string[]; active: string }) {
  return <div className="ctv-tabs" role="tablist">{tabs.map((tab) => <button className="ctv-tab" role="tab" aria-selected={tab === active} key={tab}>{tab}</button>)}</div>;
}

