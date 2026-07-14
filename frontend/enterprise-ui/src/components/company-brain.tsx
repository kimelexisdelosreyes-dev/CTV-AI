"use client";

import { useEffect, useState } from "react";
import { apiFetch, KnowledgeStats } from "@/lib/api";

type Props = { onStats: (stats: KnowledgeStats) => void };

type Collection = {
  slug: string;
  name: string;
  description: string;
  icon: string;
  employee_visible: boolean;
};

type Source = {
  document_id: string;
  filename: string;
  category: string;
  chunk_index: number;
  page_number: number | null;
  text: string;
  score: number;
};

type Personalization = {
  applied: boolean;
  job_title: string | null;
  experience_level: string | null;
  preferred_language: string | null;
  response_style: string | null;
  detail_level: string | null;
  skills_used: string[];
  tools_used: string[];
  memories_used: number;
  operational_context_applied: boolean;
  operational_tasks_used: number;
  operational_boards_used: number;
  operational_summary: string | null;
  routed_intent: string;
  routing_confidence: number;
  routed_collections: string[];
  intelligence_sources: string[];
};

export function CompanyBrain({ onStats }: Props) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState("auto");
  const [question, setQuestion] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [answer, setAnswer] = useState("");
  const [askBusy, setAskBusy] = useState(false);
  const [askError, setAskError] = useState("");
  const [useEmployeeContext, setUseEmployeeContext] = useState(true);
  const [personalization, setPersonalization] =
    useState<Personalization | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<Collection[]>("/knowledge/collections"),
      apiFetch<KnowledgeStats>("/knowledge/stats"),
    ])
      .then(([items, stats]) => {
        setCollections(items);
        onStats(stats);
      })
      .catch(console.error);
  }, []);

  async function ask() {
    if (askBusy || !question.trim()) return;

    setAskBusy(true);
    setAskError("");
    setAnswer("Generating routed answer…");
    setPersonalization(null);

    try {
      const result = await apiFetch<{
        answer: string;
        sources: Source[];
        personalization: Personalization;
      }>("/knowledge/ask", {
        method: "POST",
        body: JSON.stringify({
          question: question.trim(),
          top_k: 5,
          collection: collection === "auto" ? null : collection,
          assistant: "general",
          use_employee_context: useEmployeeContext,
        }),
      });

      setAnswer(result.answer);
      setSources(result.sources);
      setPersonalization(result.personalization);
    } catch (error) {
      setAnswer("");
      setAskError(
        error instanceof Error
          ? error.message
          : "Company Brain request failed.",
      );
    } finally {
      setAskBusy(false);
    }
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">ROUTED ENTERPRISE INTELLIGENCE</span>
          <h1>Company Brain</h1>
          <p>
            CTV ONE chooses the right knowledge and operational sources before
            generating an answer.
          </p>
        </div>
      </div>

      <article className="panel company-brain-chat">
        <label>Knowledge routing</label>
        <select
          value={collection}
          onChange={(event) => setCollection(event.target.value)}
        >
          <option value="auto">Automatic Intelligence Routing</option>
          {collections.map((item) => (
            <option key={item.slug} value={item.slug}>
              Force: {item.name}
            </option>
          ))}
        </select>

        <label>Question</label>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about policies, manuals, SOPs, tasks, deadlines, boards, or priorities…"
        />

        <label className="context-toggle">
          <input
            type="checkbox"
            checked={useEmployeeContext}
            onChange={(event) =>
              setUseEmployeeContext(event.target.checked)
            }
          />
          Use employee context
        </label>

        <button
          onClick={ask}
          disabled={askBusy || !question.trim()}
        >
          {askBusy ? "Routing and generating…" : "Ask Company Brain"}
        </button>

        {askError && <p className="error">{askError}</p>}
      </article>

      {answer && (
        <article className="panel answer-panel">
          <h2>Answer</h2>
          <p>{answer}</p>

          {personalization && (
            <div className="personalization-card">
              <b>Intelligence Used</b>
              <span>
                Intent: {personalization.routed_intent} · Confidence:{" "}
                {Math.round(personalization.routing_confidence * 100)}%
              </span>
              <span>
                Sources:{" "}
                {personalization.intelligence_sources.join(", ") || "none"}
              </span>
              <span>
                Collections:{" "}
                {personalization.routed_collections.join(", ") || "none"}
              </span>

              {personalization.operational_context_applied && (
                <span>
                  monday.com · {personalization.operational_tasks_used} task(s) ·{" "}
                  {personalization.operational_boards_used} board(s)
                </span>
              )}

              {personalization.operational_summary && (
                <span>{personalization.operational_summary}</span>
              )}
            </div>
          )}
        </article>
      )}

      {sources.length > 0 && (
        <article className="panel">
          <h2>Document Sources</h2>

          <div className="source-list">
            {sources.map((source, index) => (
              <div
                className="source-card"
                key={`${source.document_id}-${source.chunk_index}`}
              >
                <b>
                  Source {index + 1}: {source.filename}
                </b>
                <span>
                  {source.category} · score {source.score.toFixed(3)}
                  {source.page_number
                    ? ` · page ${source.page_number}`
                    : ""}
                </span>
                <p>{source.text}</p>
              </div>
            ))}
          </div>
        </article>
      )}
    </section>
  );
}
