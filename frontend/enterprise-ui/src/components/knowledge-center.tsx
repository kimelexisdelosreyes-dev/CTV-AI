"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Archive,
  BookOpen,
  FileText,
  RefreshCw,
  Search,
  Trash2,
  Upload,
} from "lucide-react";

import { apiFetch, KnowledgeDocument, KnowledgeStats } from "@/lib/api";

type Props = {
  onStats: (stats: KnowledgeStats) => void;
};

type Collection = {
  slug: string;
  name: string;
  description: string;
  icon: string;
  employee_visible: boolean;
};

const PROCESSING = new Set(["queued", "processing"]);

export function KnowledgeCenter({ onStats }: Props) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [selected, setSelected] = useState("company-policies");
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function refresh() {
    const [collectionData, documentData, stats] = await Promise.all([
      apiFetch<Collection[]>("/knowledge/collections"),
      apiFetch<KnowledgeDocument[]>("/knowledge/documents"),
      apiFetch<KnowledgeStats>("/knowledge/stats"),
    ]);

    setCollections(collectionData);
    setDocuments(documentData);
    onStats(stats);
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  const counts = useMemo(() => {
    const result: Record<string, number> = {};

    for (const document of documents) {
      result[document.category] = (result[document.category] ?? 0) + 1;
    }

    return result;
  }, [documents]);

  const visibleDocuments = useMemo(() => {
    const needle = query.trim().toLowerCase();

    return documents.filter((document) => {
      return (
        (filter === "all" || document.category === filter) &&
        (!needle ||
          document.filename.toLowerCase().includes(needle) ||
          document.category.toLowerCase().includes(needle))
      );
    });
  }, [documents, filter, query]);

  function collectionName(slug: string): string {
    return (
      collections.find((collection) => collection.slug === slug)?.name ??
      slug
    );
  }

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;

    setBusy(true);
    setMessage("Uploading and queueing document…");

    const form = new FormData();
    form.append("file", file);
    form.append("category", selected);

    try {
      const result = await apiFetch<KnowledgeDocument>(
        "/knowledge/documents",
        {
          method: "POST",
          body: form,
        },
      );

      setMessage(`Queued ${result.filename} in ${collectionName(selected)}.`);
      setFile(null);
      await refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Document upload failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function remove(document: KnowledgeDocument) {
    if (!confirm(`Delete ${document.filename} from the Knowledge Center?`)) {
      return;
    }

    await apiFetch(`/knowledge/documents/${document.id}`, {
      method: "DELETE",
    });

    await refresh();
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">APPROVED COMPANY KNOWLEDGE</span>
          <h1>Knowledge Center</h1>
          <p>
            Manage policies, manuals, SOPs, training, and approved reference
            materials separately from Company Brain.
          </p>
        </div>

        <button
          className="knowledge-refresh"
          onClick={() => refresh()}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="knowledge-collection-grid">
        <button
          className={filter === "all" ? "collection-card active" : "collection-card"}
          onClick={() => setFilter("all")}
        >
          <Archive size={20} />
          <span>All Knowledge</span>
          <strong>{documents.length}</strong>
        </button>

        {collections.map((collection) => (
          <button
            key={collection.slug}
            className={
              filter === collection.slug
                ? "collection-card active"
                : "collection-card"
            }
            onClick={() => setFilter(collection.slug)}
          >
            <BookOpen size={20} />
            <span>{collection.name}</span>
            <strong>{counts[collection.slug] ?? 0}</strong>
            <small>{collection.description}</small>
          </button>
        ))}
      </div>

      <div className="knowledge-layout">
        <article className="panel">
          <h2>Add approved knowledge</h2>

          <form onSubmit={upload}>
            <label>Knowledge collection</label>
            <select
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              {collections.map((collection) => (
                <option key={collection.slug} value={collection.slug}>
                  {collection.name}
                </option>
              ))}
            </select>

            <label>Document</label>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(event) =>
                setFile(event.target.files?.[0] ?? null)
              }
            />

            <button disabled={busy || !file}>
              <Upload size={16} />
              {busy ? "Queueing…" : "Upload to collection"}
            </button>

            {message && <p className="muted">{message}</p>}
          </form>
        </article>

        <article className="panel knowledge-library">
          <div className="knowledge-library-heading">
            <div>
              <h2>Document Library</h2>
              <p className="muted">
                {visibleDocuments.length} document(s) shown
              </p>
            </div>

            <div className="knowledge-search">
              <Search size={16} />
              <input
                placeholder="Search document names…"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          </div>

          <div className="knowledge-document-list">
            {visibleDocuments.map((document) => (
              <div className="knowledge-document" key={document.id}>
                <FileText size={20} />

                <div>
                  <b>{document.filename}</b>
                  <span>{collectionName(document.category)}</span>
                  <small>
                    {document.stage} · {document.chunk_count} chunks ·{" "}
                    {document.page_count} pages
                  </small>
                  {document.error_message && (
                    <small className="bad">{document.error_message}</small>
                  )}
                </div>

                <div className="knowledge-document-actions">
                  <span
                    className={
                      document.status === "ready"
                        ? "good"
                        : document.status === "failed"
                          ? "bad"
                          : ""
                    }
                  >
                    {document.status}
                  </span>

                  {!PROCESSING.has(document.status) && (
                    <button
                      className="icon-danger"
                      onClick={() => remove(document)}
                      title="Delete document"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              </div>
            ))}

            {visibleDocuments.length === 0 && (
              <p className="knowledge-empty">
                No documents are stored in this collection yet.
              </p>
            )}
          </div>
        </article>
      </div>
    </section>
  );
}
