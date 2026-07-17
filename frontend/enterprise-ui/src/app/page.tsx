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
  InfrastructureStatus,
  KnowledgeStats,
  Conversation,
  ConversationMessage,
  User,
} from "@/lib/api";
import {
  InfrastructureStatusRow,
  normalizeInfrastructureStatus,
} from "@/lib/infrastructure-status";
import {
  initialOperationsState,
  OperationsState,
} from "@/lib/operations-state";

const ACTIVE_CONVERSATION_KEY = "ctv_company_brain_active_conversation";
const COMPANY_BRAIN_DRAFT_KEY = "ctv_company_brain_draft";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [active, setActive] = useState<Section>("overview");
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [infrastructure, setInfrastructure] =
    useState<InfrastructureStatusRow[] | null>(null);
  const [activeConversationId, setActiveConversationId] =
    useState<string | null>(null);
  const [conversationMessages, setConversationMessages] = useState<
    ConversationMessage[]
  >([]);
  const [conversationRecents, setConversationRecents] = useState<
    Conversation[]
  >([]);
  const [companyBrainDraft, setCompanyBrainDraft] = useState("");
  const [operationsState, setOperationsState] = useState<OperationsState>(
    initialOperationsState,
  );
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!getToken()) {
      setLoading(false);
      return;
    }

    try {
      const me = await apiFetch<User>("/auth/me");
      const [knowledge, infra] = await Promise.allSettled([
        apiFetch<KnowledgeStats>("/knowledge/stats"),
        apiFetch<InfrastructureStatus>("/infrastructure/status"),
      ]);

      setUser(me);
      setStats(knowledge.status === "fulfilled" ? knowledge.value : null);
      setInfrastructure(
        infra.status === "fulfilled"
          ? normalizeInfrastructureStatus(infra.value)
          : normalizeInfrastructureStatus(null),
      );
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [load]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setActiveConversationId(
        window.localStorage.getItem(ACTIVE_CONVERSATION_KEY),
      );
      setCompanyBrainDraft(
        window.localStorage.getItem(COMPANY_BRAIN_DRAFT_KEY) ?? "",
      );
    }, 0);
    return () => window.clearTimeout(handle);
  }, []);

  useEffect(() => {
    if (activeConversationId) {
      window.localStorage.setItem(
        ACTIVE_CONVERSATION_KEY,
        activeConversationId,
      );
    } else {
      window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY);
    }
  }, [activeConversationId]);

  useEffect(() => {
    window.localStorage.setItem(COMPANY_BRAIN_DRAFT_KEY, companyBrainDraft);
  }, [companyBrainDraft]);

  function logout() {
    clearToken();
    setUser(null);
    setActiveConversationId(null);
    setConversationMessages([]);
    setConversationRecents([]);
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
        {active === "brain" && (
          <CompanyBrain
            onStats={setStats}
            activeConversationId={activeConversationId}
            setActiveConversationId={setActiveConversationId}
            messages={conversationMessages}
            setMessages={setConversationMessages}
            recents={conversationRecents}
            setRecents={setConversationRecents}
            draft={companyBrainDraft}
            setDraft={setCompanyBrainDraft}
          />
        )}
        {active === "knowledge" && <KnowledgeCenter onStats={setStats} />}
        {active === "operations" && (
          <OperationsWorkspace
            state={operationsState}
            setState={setOperationsState}
          />
        )}

        {active === "infrastructure" && (
          <Infrastructure data={infrastructure} user={user} />
        )}
      </main>
    </div>
  );
}
