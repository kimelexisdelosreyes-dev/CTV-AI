"use client";

import {
  Dispatch,
  SetStateAction,
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  apiFetch,
  Conversation,
  ConversationDetailResponse,
  ConversationListResponse,
  ConversationMessage,
  KnowledgeAskResponse,
  KnowledgeStats,
  KnowledgeSource,
  Personalization,
} from "@/lib/api";

type Props = {
  onStats: (stats: KnowledgeStats) => void;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  messages: ConversationMessage[];
  setMessages: Dispatch<SetStateAction<ConversationMessage[]>>;
  recents: Conversation[];
  setRecents: Dispatch<SetStateAction<Conversation[]>>;
  draft: string;
  setDraft: (value: string) => void;
};

type Collection = {
  slug: string;
  name: string;
  description: string;
  icon: string;
  employee_visible: boolean;
};

const RECENTS_LIMIT = 20;

export function CompanyBrain({
  onStats,
  activeConversationId,
  setActiveConversationId,
  messages,
  setMessages,
  recents,
  setRecents,
  draft,
  setDraft,
}: Props) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState("auto");
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [askBusy, setAskBusy] = useState(false);
  const [askError, setAskError] = useState("");
  const [useEmployeeContext, setUseEmployeeContext] = useState(true);
  const [personalization, setPersonalization] =
    useState<Personalization | null>(null);
  const [recentsLoading, setRecentsLoading] = useState(false);
  const [recentsError, setRecentsError] = useState("");
  const [hasMoreRecents, setHasMoreRecents] = useState(false);

  const loadRecents = useCallback(
    async (offset: number) => {
      setRecentsLoading(true);
      setRecentsError("");

      try {
        const result = await apiFetch<ConversationListResponse>(
          `/conversations?limit=${RECENTS_LIMIT}&offset=${offset}`,
        );
        setHasMoreRecents(result.has_more);
        setRecents((current) =>
          offset === 0
            ? result.conversations
            : mergeConversations(current, result.conversations),
        );
      } catch (error) {
        setRecentsError(
          error instanceof Error
            ? error.message
            : "Could not load recent conversations.",
        );
      } finally {
        setRecentsLoading(false);
      }
    },
    [setRecents],
  );

  const loadConversation = useCallback(
    async (conversationId: string) => {
      setAskError("");

      try {
        const result = await apiFetch<ConversationDetailResponse>(
          `/conversations/${conversationId}?limit=100`,
        );
        setMessages(result.messages);
        setActiveConversationId(result.conversation.id);
      } catch (error) {
        setAskError(
          error instanceof Error ? error.message : "Could not restore chat.",
        );
        setActiveConversationId(null);
        setMessages([]);
      }
    },
    [setActiveConversationId, setMessages],
  );

  useEffect(() => {
    const handle = window.setTimeout(() => {
      Promise.all([
        apiFetch<Collection[]>("/knowledge/collections"),
        apiFetch<KnowledgeStats>("/knowledge/stats"),
      ])
        .then(([items, stats]) => {
          setCollections(items);
          onStats(stats);
        })
        .catch(console.error);
      void loadRecents(0);
    }, 0);
    return () => window.clearTimeout(handle);
  }, [loadRecents, onStats]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!activeConversationId) {
        setMessages([]);
        setSources([]);
        setPersonalization(null);
        return;
      }
      void loadConversation(activeConversationId);
    }, 0);
    return () => window.clearTimeout(handle);
  }, [activeConversationId, loadConversation, setMessages]);

  async function ask() {
    const question = draft.trim();
    if (askBusy || !question) return;

    setAskBusy(true);
    setAskError("");
    setPersonalization(null);

    let conversationId = activeConversationId;

    try {
      if (!conversationId) {
        const conversation = await apiFetch<Conversation>("/conversations", {
          method: "POST",
          body: JSON.stringify({ first_prompt: question }),
        });
        conversationId = conversation.id;
        setActiveConversationId(conversation.id);
      }

      const result = await apiFetch<KnowledgeAskResponse>("/knowledge/ask", {
        method: "POST",
        body: JSON.stringify({
          question,
          top_k: 5,
          collection: collection === "auto" ? null : collection,
          conversation_id: conversationId,
          assistant: "general",
          use_employee_context: useEmployeeContext,
        }),
      });

      setSources(result.sources);
      setPersonalization(result.personalization);
      setDraft("");
      await loadConversation(conversationId);
      await loadRecents(0);
    } catch (error) {
      setAskError(
        error instanceof Error
          ? error.message
          : "Company Brain request failed.",
      );
      if (conversationId) {
        await loadConversation(conversationId).catch(console.error);
      }
    } finally {
      setAskBusy(false);
    }
  }

  function startNewChat() {
    setActiveConversationId(null);
    setMessages([]);
    setSources([]);
    setPersonalization(null);
    setAskError("");
    setDraft("");
  }

  async function renameConversation(conversation: Conversation) {
    const title = window.prompt("Rename conversation", conversation.title);
    if (!title?.trim()) return;

    const updated = await apiFetch<Conversation>(
      `/conversations/${conversation.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({ title: title.trim() }),
      },
    );
    setRecents((current) =>
      current.map((item) => (item.id === updated.id ? updated : item)),
    );
  }

  async function archiveConversation(conversation: Conversation) {
    if (!window.confirm(`Archive "${conversation.title}"?`)) return;
    await apiFetch<Conversation>(`/conversations/${conversation.id}/archive`, {
      method: "POST",
    });
    setRecents((current) =>
      current.filter((item) => item.id !== conversation.id),
    );
    if (activeConversationId === conversation.id) startNewChat();
  }

  async function deleteConversation(conversation: Conversation) {
    if (!window.confirm(`Delete "${conversation.title}"?`)) return;
    await apiFetch<void>(`/conversations/${conversation.id}`, {
      method: "DELETE",
    });
    setRecents((current) =>
      current.filter((item) => item.id !== conversation.id),
    );
    if (activeConversationId === conversation.id) startNewChat();
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

      <div className="brain-layout">
        <aside className="panel brain-recents">
          <button onClick={startNewChat}>New Chat</button>
          <h2>Recents</h2>
          {recentsLoading && recents.length === 0 && (
            <p className="muted">Loading conversations.</p>
          )}
          {recentsError && <p className="error">{recentsError}</p>}
          {!recentsLoading && recents.length === 0 && (
            <p className="muted">No conversations yet.</p>
          )}

          <div className="recent-list">
            {recents.map((conversation) => (
              <article
                className={
                  activeConversationId === conversation.id
                    ? "recent-item active"
                    : "recent-item"
                }
                key={conversation.id}
              >
                <button onClick={() => setActiveConversationId(conversation.id)}>
                  <b>{conversation.title}</b>
                  <span>{formatDate(conversation.updated_at)}</span>
                </button>
                <div className="recent-actions">
                  <button onClick={() => renameConversation(conversation)}>
                    Rename
                  </button>
                  <button onClick={() => archiveConversation(conversation)}>
                    Archive
                  </button>
                  <button onClick={() => deleteConversation(conversation)}>
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>

          {hasMoreRecents && (
            <button onClick={() => loadRecents(recents.length)}>Load more</button>
          )}
        </aside>

        <div>
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

            <div className="message-list">
              {messages.map((message) => (
                <article className={`chat-message ${message.role}`} key={message.id}>
                  <b>{message.role === "user" ? "You" : "CTV ONE"}</b>
                  <p>{message.content}</p>
                </article>
              ))}
              {messages.length === 0 && (
                <p className="muted">Start a conversation with Company Brain.</p>
              )}
            </div>

            <label>Question</label>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={
                "Ask about policies, manuals, SOPs, tasks, deadlines, boards, " +
                "or priorities..."
              }
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

            <button onClick={ask} disabled={askBusy || !draft.trim()}>
              {askBusy ? "Routing and generating..." : "Ask Company Brain"}
            </button>

            {askError && <p className="error">{askError}</p>}
          </article>

          {personalization && (
            <article className="panel answer-panel">
              <h2>Latest Intelligence Used</h2>
              <div className="personalization-card">
                <span>
                  Intent: {personalization.routed_intent} - Confidence:{" "}
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
                    monday.com - {personalization.operational_tasks_used} task(s)
                    {" - "}
                    {personalization.operational_boards_used} board(s)
                  </span>
                )}

                {personalization.operational_summary && (
                  <span>{personalization.operational_summary}</span>
                )}
              </div>
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
                      {source.category} - score {source.score.toFixed(3)}
                      {source.page_number ? ` - page ${source.page_number}` : ""}
                    </span>
                    <p>{source.text}</p>
                  </div>
                ))}
              </div>
            </article>
          )}
        </div>
      </div>
    </section>
  );
}

function mergeConversations(
  current: Conversation[],
  incoming: Conversation[],
): Conversation[] {
  const byId = new Map(current.map((item) => [item.id, item]));
  for (const item of incoming) {
    byId.set(item.id, item);
  }
  return Array.from(byId.values()).sort(
    (left, right) =>
      new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  );
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}
