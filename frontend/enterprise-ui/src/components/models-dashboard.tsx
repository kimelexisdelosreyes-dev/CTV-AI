"use client";

import { useEffect, useMemo, useState } from "react";
import { Play, RefreshCw } from "lucide-react";

import {
  apiFetch,
  DeveloperModels,
  DeveloperStatus,
  ModelBenchmarkResponse,
} from "@/lib/api";

type Props = {
  developerStatus: DeveloperStatus | null;
};

function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0 ms";
  return `${Math.round(value)} ms`;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0";
  return Math.round(value).toLocaleString();
}

function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0 tok/s";
  return `${value.toFixed(1)} tok/s`;
}

function caseLabel(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function ModelsDashboard({ developerStatus }: Props) {
  const [models, setModels] = useState<DeveloperModels | null>(null);
  const [comparisonModel, setComparisonModel] = useState("");
  const [benchmark, setBenchmark] = useState<ModelBenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const comparisonOptions = useMemo(() => {
    return (models?.available_models ?? []).filter(
      (model) => model !== models?.default_model,
    );
  }, [models]);

  async function loadModels() {
    if (!developerStatus?.enabled) return;

    setLoading(true);
    setError("");

    try {
      const data = await apiFetch<DeveloperModels>("/developer/models");
      setModels(data);
      setComparisonModel((current) => {
        if (current && data.available_models.includes(current)) return current;
        return data.available_models.find((model) => model !== data.default_model) ?? "";
      });
    } catch (caught) {
      setModels(null);
      setError(caught instanceof Error ? caught.message : "Could not load models.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadModels();
  }, [developerStatus?.enabled]);

  async function runBenchmark() {
    if (!comparisonModel) return;

    setRunning(true);
    setError("");

    try {
      const data = await apiFetch<ModelBenchmarkResponse>(
        "/developer/models/benchmark",
        {
          method: "POST",
          body: JSON.stringify({ comparison_model: comparisonModel }),
        },
      );
      setBenchmark(data);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not run benchmark.",
      );
    } finally {
      setRunning(false);
    }
  }

  if (!developerStatus?.enabled) {
    return (
      <article className="developer-state developer-error">
        <p>Developer mode is disabled.</p>
      </article>
    );
  }

  return (
    <>
      <article className="developer-state">
        <p>
          Benchmarking runs six full AI requests and may take several minutes on
          the current hardware.
        </p>
      </article>

      <article className="panel">
        <div className="developer-console-heading">
          <div>
            <h2>Model comparison</h2>
            <p className="muted">
              Current default model: {models?.default_model ?? "Loading"}
            </p>
          </div>

          <div className="developer-actions">
            <button onClick={loadModels} disabled={loading || running}>
              <RefreshCw size={16} />
              Refresh
            </button>
            <button
              className="developer-toggle"
              onClick={runBenchmark}
              disabled={!comparisonModel || loading || running}
            >
              <Play size={16} />
              {running ? "Running" : "Run benchmark"}
            </button>
          </div>
        </div>

        <label>Comparison model</label>
        <select
          value={comparisonModel}
          onChange={(event) => setComparisonModel(event.target.value)}
          disabled={loading || running}
        >
          {comparisonOptions.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>

        {loading && <p className="muted">Loading installed models.</p>}
        {running && <p className="muted">Benchmark is running sequentially.</p>}
        {error && <p className="error">{error}</p>}
        {!loading && comparisonOptions.length === 0 && (
          <p className="muted">No comparison model is available.</p>
        )}
      </article>

      {benchmark && (
        <article className="panel">
          <h2>Benchmark results</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Case</th>
                  <th>Outcome</th>
                  <th>Total</th>
                  <th>Ollama</th>
                  <th>Input tokens</th>
                  <th>Output tokens</th>
                  <th>Tok/s</th>
                  <th>Answer chars</th>
                  <th>Intent</th>
                </tr>
              </thead>
              <tbody>
                {benchmark.results.map((result) => (
                  <tr key={`${result.model_name}-${result.case_label}`}>
                    <td>{result.model_name}</td>
                    <td>{caseLabel(result.case_label)}</td>
                    <td>
                      {result.outcome}
                      {result.skipped_no_evidence && (
                        <span>Skipped because no evidence was found</span>
                      )}
                      {result.error_category && (
                        <span>{result.error_category}</span>
                      )}
                    </td>
                    <td>{formatMs(result.total_request_ms)}</td>
                    <td>{formatMs(result.ollama_request_ms)}</td>
                    <td>{formatNumber(result.estimated_input_tokens)}</td>
                    <td>{formatNumber(result.estimated_output_tokens)}</td>
                    <td>{formatRate(result.tokens_per_second)}</td>
                    <td>{formatNumber(result.answer_character_count)}</td>
                    <td>{result.routed_intent ?? "unknown"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}
    </>
  );
}
