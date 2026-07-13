"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  apiFetch,
  KnowledgeDocument,
  KnowledgeStats,
} from "@/lib/api";

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

  async function refresh() {
    const [docs, stats] = await Promise.all([
      apiFetch<KnowledgeDocument[]>("/knowledge/documents"),
      apiFetch<KnowledgeStats>("/knowledge/stats"),
    ]);
    setDocuments(docs);
    onStats(stats);
  }

  useEffect(() => { refresh().catch(console.error); }, []);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setUploadState("Extracting, embedding, and indexing…");
    const form = new FormData();
    form.append("file", file);
    form.append("category", category);
    try {
      const result = await apiFetch<KnowledgeDocument>("/knowledge/documents", {
        method: "POST",
        body: form,
      });
      setUploadState(`Ready — ${result.chunk_count} chunks indexed.`);
      setFile(null);
      await refresh();
    } catch (error) {
      setUploadState(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
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
    setAnswer("Generating grounded answer…");
    const result = await apiFetch<{ answer: string; sources: Source[] }>("/knowledge/ask", {
      method: "POST",
      body: JSON.stringify({
        question,
        top_k: 5,
        category: null,
        assistant: "general",
      }),
    });
    setAnswer(result.answer);
    setSources(result.sources);
  }

  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">COMPANY BRAIN</span><h1>Knowledge Center</h1><p>Curate, search, and test approved company knowledge.</p></div>
      </div>

      <div className="two-column brain-layout">
        <article className="panel">
          <h2>Add knowledge</h2>
          <form onSubmit={upload}>
            <label>Category</label>
            <input value={category} onChange={(event) => setCategory(event.target.value)} />
            <label>Document</label>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <button disabled={busy || !file}>{busy ? "Indexing…" : "Upload and index"}</button>
            {uploadState && <p className="muted">{uploadState}</p>}
          </form>
        </article>

        <article className="panel">
          <h2>Knowledge test</h2>
          <label>Semantic search</label>
          <textarea value={query} onChange={(event) => setQuery(event.target.value)} />
          <button className="secondary-button" onClick={search}>Search sources</button>
          <label>Grounded question</label>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
          <button onClick={ask}>Ask Company Brain</button>
        </article>
      </div>

      {answer && <article className="panel answer-panel"><h2>Answer</h2><p>{answer}</p></article>}

      <article className="panel">
        <h2>Indexed documents</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Document</th><th>Category</th><th>Status</th><th>Chunks</th><th /></tr></thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id}>
                  <td><b>{document.filename}</b><span>{new Date(document.created_at).toLocaleString()}</span></td>
                  <td>{document.category}</td>
                  <td className={document.status === "ready" ? "good" : "bad"}>{document.status}</td>
                  <td>{document.chunk_count}</td>
                  <td><button className="danger-button" onClick={() => remove(document)}>Delete</button></td>
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
                <span>Score {source.score.toFixed(3)} {source.page_number ? `· page ${source.page_number}` : ""}</span>
                <p>{source.text}</p>
              </div>
            ))}
          </div>
        </article>
      )}
    </section>
  );
}
