"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Archive, BookOpen, FileText, RefreshCw, Trash2, Upload } from "lucide-react";

import {
  BaseCard,
  EmptyState,
  IconButton,
  Inline,
  InlineAlert,
  LoadingSkeleton,
  PageHeader,
  PageShell,
  PageTitle,
  PrimaryButton,
  ResponsiveGrid,
  SearchInput,
  SecondaryButton,
  Select,
  StatusBadge,
} from "@/design-system";
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
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [collectionData, documentData, stats] = await Promise.all([
        apiFetch<Collection[]>("/knowledge/collections"),
        apiFetch<KnowledgeDocument[]>("/knowledge/documents"),
        apiFetch<KnowledgeStats>("/knowledge/stats"),
      ]);

      setCollections(collectionData);
      setDocuments(documentData);
      onStats(stats);
    } finally {
      setLoading(false);
    }
  }, [onStats]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      refresh().catch(console.error);
    }, 0);
    return () => window.clearTimeout(handle);
  }, [refresh]);

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
    return collections.find((collection) => collection.slug === slug)?.name ?? slug;
  }

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;

    setBusy(true);
    setMessage("Uploading and queueing document...");

    const form = new FormData();
    form.append("file", file);
    form.append("category", selected);

    try {
      const result = await apiFetch<KnowledgeDocument>("/knowledge/documents", {
        method: "POST",
        body: form,
      });

      setMessage(`Queued ${result.filename} in ${collectionName(selected)}.`);
      setFile(null);
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Document upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(document: KnowledgeDocument) {
    if (!confirm(`Delete ${document.filename} from the Knowledge Center?`)) return;
    await apiFetch(`/knowledge/documents/${document.id}`, { method: "DELETE" });
    await refresh();
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow="ORGANIZATIONAL MEMORY"
        title={<PageTitle>Knowledge Center</PageTitle>}
        description={
          <p className="ctv-body">
            Manage policies, manuals, SOPs, training, and approved reference
            materials as governed Organizational Memory.
          </p>
        }
        action={
          <SecondaryButton leadingIcon={<RefreshCw size={16} />} onClick={() => refresh()}>
            Refresh
          </SecondaryButton>
        }
      />

      {loading && <LoadingSkeleton lines={4} />}

      <ResponsiveGrid min="180px">
        <BaseCard
          action={<StatusBadge status={filter === "all" ? "processing" : "neutral"}>{documents.length}</StatusBadge>}
          interactive
          onClick={() => setFilter("all")}
          title={<Inline><Archive size={18} />All Knowledge</Inline>}
        />

        {collections.map((collection) => (
          <BaseCard
            action={<StatusBadge status={filter === collection.slug ? "processing" : "neutral"}>{counts[collection.slug] ?? 0}</StatusBadge>}
            interactive
            key={collection.slug}
            meta={collection.description}
            onClick={() => setFilter(collection.slug)}
            title={<Inline><BookOpen size={18} />{collection.name}</Inline>}
          />
        ))}
      </ResponsiveGrid>

      <div className="knowledge-layout">
        <BaseCard title="Add approved knowledge">
          <form onSubmit={upload}>
            <Select
              label="Knowledge collection"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              {collections.map((collection) => (
                <option key={collection.slug} value={collection.slug}>
                  {collection.name}
                </option>
              ))}
            </Select>

            <label>Document</label>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />

            <PrimaryButton disabled={busy || !file} leadingIcon={<Upload size={16} />}>
              {busy ? "Queueing..." : "Upload to collection"}
            </PrimaryButton>

            {message && (
              <InlineAlert title="Knowledge ingestion" status="processing">
                {message}
              </InlineAlert>
            )}
          </form>
        </BaseCard>

        <BaseCard className="knowledge-library">
          <div className="knowledge-library-heading">
            <div>
              <h2 className="ctv-section-title">Document Library</h2>
              <p className="muted">{visibleDocuments.length} document(s) shown</p>
            </div>

            <SearchInput
              placeholder="Search document names..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onClear={() => setQuery("")}
            />
          </div>

          <div className="knowledge-document-list">
            {visibleDocuments.map((document) => (
              <BaseCard
                action={
                  <Inline>
                    <StatusBadge status={document.status === "ready" ? "healthy" : document.status === "failed" ? "critical" : "processing"}>
                      {document.status}
                    </StatusBadge>
                    {!PROCESSING.has(document.status) && (
                      <IconButton label={`Delete ${document.filename}`} onClick={() => remove(document)}>
                        <Trash2 size={15} />
                      </IconButton>
                    )}
                  </Inline>
                }
                key={document.id}
                meta={`${collectionName(document.category)} - ${document.stage} - ${document.chunk_count} chunks - ${document.page_count} pages`}
                title={<Inline><FileText size={18} />{document.filename}</Inline>}
              >
                {document.error_message && (
                  <InlineAlert title="Document issue" status="critical">
                    {document.error_message}
                  </InlineAlert>
                )}
              </BaseCard>
            ))}

            {visibleDocuments.length === 0 && (
              <EmptyState title="Your organization's memory starts here.">
                Upload manuals, SOPs, presentations, interviews, and historical
                records.
              </EmptyState>
            )}
          </div>
        </BaseCard>
      </div>
    </PageShell>
  );
}
