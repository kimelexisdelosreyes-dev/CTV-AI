"use client";

import { useCallback, useEffect, useState } from "react";

import { Assistants } from "@/components/assistants";
import { CompanyBrain } from "@/components/company-brain";
import { Infrastructure } from "@/components/infrastructure";
import { KnowledgeCenter } from "@/components/knowledge-center";
import { Login } from "@/components/login";
import { OperationsWorkspace } from "@/components/operations-workspace";
import { Overview } from "@/components/overview";
import { Section, Sidebar } from "@/components/sidebar";
import {
  apiFetch,
  clearToken,
  getToken,
  KnowledgeStats,
  User,
} from "@/lib/api";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [active, setActive] = useState<Section>("overview");
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [infrastructure, setInfrastructure] =
    useState<Record<string, string> | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!getToken()) {
      setLoading(false);
      return;
    }

    try {
      const [me, knowledge, infra] = await Promise.all([
        apiFetch<User>("/auth/me"),
        apiFetch<KnowledgeStats>("/knowledge/stats"),
        apiFetch<Record<string, string>>("/infrastructure/status"),
      ]);

      setUser(me);
      setStats(knowledge);
      setInfrastructure(infra);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function logout() {
    clearToken();
    setUser(null);
  }

  if (loading) {
    return <main className="loading-screen">Loading CTV ONE…</main>;
  }

  if (!user) {
    return <Login onSuccess={load} />;
  }

  return (
    <div className="app-shell">
      <Sidebar active={active} onChange={setActive} onLogout={logout} />

      <main className="content">
        {active === "overview" && (
          <Overview
            user={user}
            stats={stats}
            infrastructure={infrastructure}
          />
        )}

        {active === "assistants" && <Assistants />}
        {active === "brain" && <CompanyBrain onStats={setStats} />}
        {active === "knowledge" && <KnowledgeCenter onStats={setStats} />}
        {active === "operations" && <OperationsWorkspace />}

        {active === "infrastructure" && (
          <Infrastructure data={infrastructure} />
        )}
      </main>
    </div>
  );
}
