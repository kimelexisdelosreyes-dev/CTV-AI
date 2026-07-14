"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { apiFetch, KnowledgeDocument, KnowledgeStats } from "@/lib/api";

type Props = { onStats: (stats: KnowledgeStats) => void };

type Source = {
  document_id: string;
  filename: string;
  category: string;
  chunk_index: number;
  page_number: number | null;
  text: string;
  score: number;
};

const ACTIVE = new Set(["queued", "processing"]);

export function CompanyBrain({ onStats }: Props) {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [category, setCategory] = useState("general");
  const [file, setFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState("");
  const [query, setQuery] = useState("");
  const [question, setQuestion] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [askBusy, setAskBusy] = useState(false);
  const [askError, setAskError] = useState("");

  async function refresh() {
    const [docs, stats] = await Promise.all([
      apiFetch<KnowledgeDocument[]>("/knowledge/documents"),
      apiFetch<KnowledgeStats>("/knowledge/stats"),
    ]);
    setDocuments(docs);
    onStats(stats);
  }

  useEffect(() => {
    refresh().catch(console.error);
    timer.current = setInterval(() => refresh().catch(console.error), 2500);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;

    setBusy(true);
    setUploadState("Uploading and queueing…");

    const form = new FormData();
    form.append("file", file);
    form.append("category", category);

    try {
      const result = await apiFetch<KnowledgeDocument>("/knowledge/documents", {
        method: "POST",
        body: form,
      });
      setUploadState(`Queued: ${result.filename}`);
      setFile(null);
      await refresh();
    } catch (error) {
      setUploadState(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function retry(document: KnowledgeDocument) {
    await apiFetch(`/knowledge/documents/${document.id}/retry`, { method: "POST" });
    await refresh();
  }

  async function remove(document: KnowledgeDocument) {
    if (!confirm(`Delete ${document.filename} from all knowledge storage?`)) return;
    await apiFetch(`/knowledge/documents/${document.id}`, { method: "DELETE" });
    await refresh();
  }

  async function search() {
    const result = await apiFetch<{ sources: Source[] }>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k: 5, category: null }),
    });
    setSources(result.sources);
  }

  async function ask() {
  if (askBusy || !question.trim()) return;

  setAskBusy(true);
  setAskError("");
  setAnswer("Generating grounded answer…");

  try {
    const result = await apiFetch<{
      answer: string;
      sources: Source[];
    }>("/knowledge/ask", {
      method: "POST",
      body: JSON.stringify({
        question: question.trim(),
        top_k: 3,
        category: null,
        assistant: "general",
      }),
    });

    setAnswer(result.answer);
    setSources(result.sources);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Company Brain request failed.";

    setAnswer("");
    setAskError(message);
  } finally {
    setAskBusy(false);
  }
}

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">COMPANY BRAIN</span>
          <h1>Knowledge Center</h1>
          <p>OCR, index, search, and manage approved company documents.</p>
        </div>
      </div>

      <div className="two-column brain-layout">
        <article className="panel">
          <h2>Add knowledge</h2>
          <form onSubmit={upload}>
            <label>Category</label>
            <input value={category} onChange={(e) => setCategory(e.target.value)} />

            <label>Document</label>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />

            <button disabled={busy || !file}>
              {busy ? "Queueing…" : "Upload and queue"}
            </button>

            {uploadState && <p className="muted">{uploadState}</p>}
          </form>
        </article>

        <article className="panel">
          <h2>Knowledge test</h2>

          <label>Semantic search</label>
          <textarea value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="secondary-button" onClick={search}>Search sources</button>

          <label>Grounded question</label>
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
          <button onClick={ask} disabled={askBusy || !question.trim()}>
            {askBusy ? "Generating…" : "Ask Company Brain"}
          </button>

{askError && <p className="error">{askError}</p>}
        </article>
      </div>

      {answer && (
        <article className="panel answer-panel">
          <h2>Answer</h2>
          <p>{answer}</p>
        </article>
      )}

      <article className="panel">
        <h2>Indexed documents</h2>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Document</th>
                <th>Category</th>
                <th>Stage</th>
                <th>Progress</th>
                <th>Pages / OCR</th>
                <th>Chunks</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id}>
                  <td>
                    <b>{document.filename}</b>
                    <span>{document.error_message ?? new Date(document.created_at).toLocaleString()}</span>
                  </td>
                  <td>{document.category}</td>
                  <td className={document.status === "ready" ? "good" : document.status === "failed" ? "bad" : ""}>
                    {document.stage}
                  </td>
                  <td>
                    <div className="progress-track">
                      <div className="progress-fill" style={{ width: `${document.progress_percent}%` }} />
                    </div>
                    <span>{document.progress_percent}%</span>
                  </td>
                  <td>
                    {document.pages_processed}/{document.page_count}
                    <span>{document.ocr_pages} OCR page(s)</span>
                  </td>
                  <td>{document.chunk_count}</td>
                  <td>
                    {document.status === "failed" && (
                      <button className="secondary-button compact-button" onClick={() => retry(document)}>
                        Retry
                      </button>
                    )}
                    {!ACTIVE.has(document.status) && (
                      <button className="danger-button" onClick={() => remove(document)}>
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      {sources.length > 0 && (
        <article className="panel">
          <h2>Retrieved sources</h2>
          <div className="source-list">
            {sources.map((source, index) => (
              <div className="source-card" key={`${source.document_id}-${source.chunk_index}`}>
                <b>Source {index + 1}: {source.filename}</b>
                <span>
                  Score {source.score.toFixed(3)}
                  {source.page_number ? ` · page ${source.page_number}` : ""}
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
