"use client";

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Briefcase,
  FileSearch,
  LayoutDashboard,
  LogOut,
  Moon,
  ScrollText,
  Shield,
  Sun,
} from "lucide-react";
import { useEffect, useState } from "react";

import type { FraudAlert, FraudCase, OperatorPrincipal } from "@/lib/contracts";

export type ActiveView =
  | "overview"
  | "investigate"
  | "analyze"
  | "cases"
  | "alerts"
  | "audit";

type SidebarProps = {
  activeView: ActiveView;
  alerts: FraudAlert[];
  cases: FraudCase[];
  operator: OperatorPrincipal;
  onLogout: () => void;
  onViewChange: (view: ActiveView) => void;
};

const viewConfig: {
  id: ActiveView;
  label: string;
  icon: typeof LayoutDashboard;
  adminOnly?: boolean;
}[] = [
  { id: "overview", label: "Workspace", icon: LayoutDashboard },
  { id: "analyze", label: "Analyze Data", icon: BarChart3 },
  { id: "alerts", label: "Alerts", icon: AlertTriangle },
  { id: "cases", label: "Cases", icon: Briefcase },
  { id: "investigate", label: "Scenarios", icon: FileSearch },
  { id: "audit", label: "Audit Trail", icon: ScrollText, adminOnly: true },
];

export function Sidebar({
  activeView,
  alerts,
  cases,
  operator,
  onLogout,
  onViewChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  const newAlertsCount = alerts.filter((a) => a.status === "new").length;
  const activeCasesCount = cases.filter(
    (c) => c.status === "open" || c.status === "investigating",
  ).length;

  useEffect(() => {
    const saved = localStorage.getItem("rfi.theme") as "light" | "dark" | null;
    const initial = saved ?? "dark";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("rfi.theme", next);
  }

  const visibleViews = viewConfig.filter(
    (v) => !v.adminOnly || operator.role === "admin",
  );

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-top">
        <button
          className="sidebar-brand"
          onClick={() => setCollapsed(!collapsed)}
          type="button"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <Shield size={22} strokeWidth={2.2} />
          {!collapsed && <span className="brand-text">Fraud Intel</span>}
        </button>
      </div>

      <nav className="sidebar-nav">
        {visibleViews.map((view) => {
          const isActive = activeView === view.id;
          const Icon = view.icon;
          const badge =
            view.id === "alerts"
              ? newAlertsCount
              : view.id === "cases"
                ? activeCasesCount
                : 0;

          return (
            <button
              key={view.id}
              className={`sidebar-link ${isActive ? "active" : ""}`}
              onClick={() => onViewChange(view.id)}
              type="button"
              title={view.label}
              aria-label={view.label}
            >
              <Icon size={18} strokeWidth={isActive ? 2.4 : 1.8} />
              {!collapsed && <span>{view.label}</span>}
              {badge > 0 && <span className="sidebar-badge">{badge}</span>}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-bottom">
        <button
          className="sidebar-link"
          onClick={toggleTheme}
          type="button"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          {!collapsed && <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>}
        </button>

        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {operator.display_name
              .split(" ")
              .map((n) => n[0])
              .join("")
              .slice(0, 2)
              .toUpperCase()}
          </div>
          {!collapsed && (
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{operator.display_name}</span>
              <span className="sidebar-user-role">{operator.role}</span>
            </div>
          )}
        </div>

        <button
          className="sidebar-link logout"
          onClick={onLogout}
          type="button"
          title="Sign out"
        >
          <LogOut size={18} />
          {!collapsed && <span>Sign Out</span>}
        </button>
      </div>
    </aside>
  );
}

type TopBarProps = {
  title: string;
  subtitle?: string;
  healthStatus?: string;
  children?: React.ReactNode;
};

export function TopBar({ title, subtitle, healthStatus, children }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1 className="topbar-title">{title}</h1>
        {subtitle && <span className="topbar-subtitle">{subtitle}</span>}
      </div>
      <div className="topbar-right">
        {healthStatus && (
          <span
            className={`topbar-health ${healthStatus === "ready" ? "good" : "warning"}`}
          >
            <Activity size={14} />
            {healthStatus}
          </span>
        )}
        {children}
      </div>
    </header>
  );
}
