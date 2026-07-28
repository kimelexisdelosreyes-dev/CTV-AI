"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, RefreshCw, Server, Trash2 } from "lucide-react";

import { ModelsDashboard } from "@/components/models-dashboard";
import { PerformanceDashboard } from "@/components/performance-dashboard";
import {
  apiFetch,
  DeveloperStatus,
  PerformanceEvent,
  PerformanceSummary,
} from "@/lib/api";

type DeveloperTab =
  | "performance"
  | "models"
  | "cache"
  | "connectors"
  | "context"
  | "metrics";

const developerTabs: { id: DeveloperTab; label: string }[] = [
  { id: "performance", label: "Performance" },
  { id: "models", label: "Models" },
  { id: "cache", label: "Cache" },
  { id: "connectors", label: "Connectors" },
  { id: "context", label: "Context Engine" },
  { id: "metrics", label: "AI Metrics" },
];

export function DeveloperConsole() {
  const [activeTab, setActiveTab] = useState<DeveloperTab>("performance");
  const [developerStatus, setDeveloperStatus] =
    useState<DeveloperStatus | null>(null);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [events, setEvents] = useState<PerformanceEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadDeveloperConsole = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const status = await apiFetch<DeveloperStatus>("/developer/status");
      setDeveloperStatus(status);

      if (!status.enabled) {
        setSummary(null);
        setEvents([]);
        setError("Developer mode is disabled.");
        return;
      }

      const [summaryData, recentData] = await Promise.all([
        apiFetch<PerformanceSummary>("/developer/performance/summary"),
        apiFetch<PerformanceEvent[]>("/developer/performance/recent"),
      ]);

      setSummary(summaryData);
      setEvents(recentData);
    } catch (caught) {
      setSummary(null);
      setEvents([]);
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not load Developer Console.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadDeveloperConsole();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [loadDeveloperConsole]);

  async function setDeveloperMode(enabled: boolean) {
    setLoading(true);
    setError("");

    try {
      const status = await apiFetch<DeveloperStatus>("/developer/status", {
        method: "PUT",
        body: JSON.stringify({ enabled }),
      });

      setDeveloperStatus(status);
      if (!status.enabled) {
        setSummary(null);
        setEvents([]);
        setError("Developer mode is disabled.");
      } else {
        await loadDeveloperConsole();
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not update Developer Console.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function clearMetrics() {
    if (!confirm("Clear all stored AI performance metrics?")) return;

    setLoading(true);
    setError("");

    try {
      await apiFetch<void>("/developer/performance/recent", {
        method: "DELETE",
      });
      await loadDeveloperConsole();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not clear metrics.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="developer-console">
      <div className="developer-console-heading">
        <div>
          <span className="eyebrow">DEVELOPER CONSOLE</span>
          <h2>AI Operations</h2>
        </div>

        <div className="developer-actions">
          <button
            className="developer-toggle"
            onClick={() => setDeveloperMode(!developerStatus?.enabled)}
            disabled={loading}
          >
            <Activity size={16} />
            {developerStatus?.enabled ? "Disable" : "Enable"}
          </button>
          <button onClick={loadDeveloperConsole} disabled={loading}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button
            className="developer-danger"
            onClick={clearMetrics}
            disabled={loading || !developerStatus?.enabled}
          >
            <Trash2 size={16} />
            Clear
          </button>
        </div>
      </div>

      <div className="developer-tabs">
        {developerTabs.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab !== "performance" && activeTab !== "models" && (
        <article className="developer-state">
          <Server size={18} />
          <p>
            {developerTabs.find((tab) => tab.id === activeTab)?.label} is
            reserved for a future console module.
          </p>
        </article>
      )}

      {activeTab === "performance" && (
        <PerformanceDashboard
          developerStatus={developerStatus}
          events={events}
          error={error}
          loading={loading}
          summary={summary}
        />
      )}

      {activeTab === "models" && (
        <ModelsDashboard developerStatus={developerStatus} />
      )}
    </section>
  );
}
