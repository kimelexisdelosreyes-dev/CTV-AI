"use client";

import {
  Dispatch,
  SetStateAction,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  AIConfidenceBadge,
  AIThinkingPanel,
  AISourceReference,
  BaseCard,
  EmptyState,
  Inline,
  InlineAlert,
  LoadingSkeleton,
  PageHeader,
  PageShell,
  PageTitle,
  PrimaryButton,
  SecondaryButton,
  Select,
  StatusBadge,
  TextArea,
  Checkbox,
  ResponsiveGrid,
} from "@/design-system";
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
  streamKnowledgeAsk,
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
  const [streamStatus, setStreamStatus] = useState<
    "preparing" | "generating" | "streaming" | null
  >(null);
  const streamAbortController = useRef<AbortController | null>(null);

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
      if (askBusy) return;
      void loadConversation(activeConversationId);
    }, 0);
    return () => window.clearTimeout(handle);
  }, [activeConversationId, askBusy, loadConversation, setMessages]);

  async function ask() {
    const question = draft.trim();
    if (askBusy || !question) return;

    setAskBusy(true);
    setAskError("");
    setPersonalization(null);
    setStreamStatus("preparing");

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
      const createdAt = new Date().toISOString();
      const clientMessageId = crypto.randomUUID();
      const userMessage: ConversationMessage = {
        id: `pending-user-${clientMessageId}`,
        conversation_id: conversationId,
        role: "user",
        content: question,
        created_at: createdAt,
      };
      const assistantMessageId = `pending-assistant-${crypto.randomUUID()}`;
      const assistantMessage: ConversationMessage = {
        id: assistantMessageId,
        conversation_id: conversationId,
        role: "assistant",
        content: "",
        created_at: createdAt,
      };
      setMessages((current) => [...current, userMessage, assistantMessage]);

      const payload = {
        question,
        top_k: 5,
        collection: collection === "auto" ? null : collection,
        conversation_id: conversationId,
        assistant: "general",
        use_employee_context: useEmployeeContext,
        client_message_id: clientMessageId,
      };
      const abortController = new AbortController();
      streamAbortController.current = abortController;
      let streamStarted = false;
      let streamCompleted = false;
      let streamFailed = false;
      let assistantChars = 0;
      try {
        await streamKnowledgeAsk(
          payload,
          (event) => {
            if (event.type === "start") streamStarted = true;
            if (event.type === "context_ready") setStreamStatus("generating");
            if (event.type === "token") {
              if (!event.text) return;
              assistantChars += event.text.length;
              setStreamStatus("streaming");
              setMessages((current) =>
                current.map((message) =>
                  message.id === assistantMessageId
                    ? { ...message, content: message.content + event.text }
                    : message,
                ),
              );
            }
            if (event.type === "done") {
              if (event.answer_chars <= 0 || assistantChars <= 0) {
                throw new Error("Company Brain returned an empty answer.");
              }
              streamCompleted = true;
            }
            if (event.type === "error") throw new Error(event.safe_detail);
          },
          abortController.signal,
        );
      } catch (streamError) {
        if (abortController.signal.aborted) {
          const stoppedMessage = "Generation stopped.";
          streamFailed = true;
          setAskError(stoppedMessage);
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    content: message.content
                      ? `${message.content}\n\n[Generation stopped]`
                      : stoppedMessage,
                  }
                : message,
            ),
          );
        } else if (!streamStarted) {
          const result = await apiFetch<KnowledgeAskResponse>("/knowledge/ask", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          setSources(result.sources);
          setPersonalization(result.personalization);
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: result.answer }
                : message,
            ),
          );
          streamCompleted = true;
        } else {
          const safeMessage =
            streamError instanceof Error
              ? streamError.message
              : "Company Brain could not complete this answer.";
          streamFailed = true;
          setAskError(safeMessage);
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    content: message.content
                      ? `${message.content}\n\n[${safeMessage}]`
                      : safeMessage,
                  }
                : message,
            ),
          );
        }
      }
      if (!streamCompleted && !streamFailed) {
        throw new Error("Company Brain stream ended before completion.");
      }
      setDraft("");
      if (streamCompleted) await loadConversation(conversationId);
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
      streamAbortController.current = null;
      setStreamStatus(null);
      setAskBusy(false);
    }
  }

  function stopStreaming() {
    streamAbortController.current?.abort();
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
    <PageShell>
      <PageHeader
        eyebrow="MY AI"
        title={<PageTitle>My AI</PageTitle>}
        description={<p className="ctv-body">Personal Memory, Organizational Memory, and Work Sessions help CTV ONE support your work without exposing internal AI systems.</p>}
        action={<StatusBadge status={askBusy ? "processing" : "healthy"}>{askBusy ? "AI Activity running" : "Ready"}</StatusBadge>}
      />

      <div className="brain-layout">
        <aside className="brain-recents">
          <PrimaryButton onClick={startNewChat}>New Work Session</PrimaryButton>
          <h2 className="ctv-section-title">Work Sessions</h2>
          {recentsLoading && recents.length === 0 && (
            <LoadingSkeleton lines={4} />
          )}
          {recentsError && <InlineAlert title="Could not load Work Sessions" status="critical">{recentsError}</InlineAlert>}
          {!recentsLoading && recents.length === 0 && (
            <EmptyState title="Your AI is ready to learn how you work.">
              Begin a Work Session or teach it a professional workflow.
            </EmptyState>
          )}

          <div className="recent-list">
            {recents.map((conversation) => (
              <BaseCard
                interactive
                key={conversation.id}
                title={conversation.title}
                meta={formatDate(conversation.updated_at)}
                action={activeConversationId === conversation.id ? <StatusBadge status="processing">Active</StatusBadge> : undefined}
              >
                <Inline>
                  <SecondaryButton size="small" onClick={() => setActiveConversationId(conversation.id)}>
                    Resume
                  </SecondaryButton>
                  <SecondaryButton size="small" onClick={() => renameConversation(conversation)}>
                    Rename
                  </SecondaryButton>
                  <SecondaryButton size="small" onClick={() => archiveConversation(conversation)}>
                    Archive
                  </SecondaryButton>
                  <SecondaryButton size="small" onClick={() => deleteConversation(conversation)}>
                    Delete
                  </SecondaryButton>
                </Inline>
              </BaseCard>
            ))}
          </div>

          {hasMoreRecents && (
            <SecondaryButton onClick={() => loadRecents(recents.length)}>Load more</SecondaryButton>
          )}
        </aside>

        <div>
          <BaseCard className="company-brain-chat" title="Ask CTV ONE" meta="Visible activity only. No private reasoning is shown.">
            <Select
              label="Knowledge routing"
              value={collection}
              onChange={(event) => setCollection(event.target.value)}
            >
              <option value="auto">Automatic Intelligence Routing</option>
              {collections.map((item) => (
                <option key={item.slug} value={item.slug}>
                  Force: {item.name}
                </option>
              ))}
            </Select>

            <div className="message-list">
              {messages.map((message) => (
                <article className={`chat-message ${message.role}`} key={message.id}>
                  <b>{message.role === "user" ? "You" : "CTV ONE"}</b>
                  <p>
                    {message.content ||
                      (message.role === "assistant" && askBusy
                        ? "Generating answer..."
                        : "")}
                  </p>
                </article>
              ))}
              {messages.length === 0 && (
                <EmptyState title="Your AI is ready to learn how you work.">
                  Ask about policies, work sessions, project context, deadlines,
                  and Knowledge Center sources.
                </EmptyState>
              )}
            </div>

            {askBusy && (
              <AIThinkingPanel steps={[
                { label: "Understanding your request", complete: streamStatus !== "preparing" },
                { label: "Searching Enterprise Files", complete: streamStatus === "generating" || streamStatus === "streaming" },
                { label: "Reading Knowledge Center", complete: streamStatus === "streaming" },
                { label: "Preparing response", complete: streamStatus === "streaming" },
              ]} />
            )}

            <TextArea
              label="Request"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={
                "Ask about policies, manuals, SOPs, tasks, deadlines, boards, " +
                "or priorities..."
              }
            />

            <Checkbox
              label="Use Personal Memory and Work Sessions"
              checked={useEmployeeContext}
              onChange={(event) => setUseEmployeeContext(event.target.checked)}
            />

            <PrimaryButton onClick={ask} disabled={askBusy || !draft.trim()}>
              {askBusy
                ? streamStatus === "preparing"
                  ? "Preparing context..."
                  : streamStatus === "generating"
                    ? "Generating answer..."
                    : "Generating..."
                : "Ask Company Brain"}
            </PrimaryButton>
            {askBusy && (
              <SecondaryButton onClick={stopStreaming} type="button">
                Stop
              </SecondaryButton>
            )}

            {askError && <InlineAlert title="AI Activity stopped" status="critical">{askError}</InlineAlert>}
          </BaseCard>

          {personalization && (
            <BaseCard className="answer-panel" title="Latest Intelligence Used">
              <div className="personalization-card">
                <AIConfidenceBadge value={personalization.routing_confidence > 0.75 ? "high" : personalization.routing_confidence > 0.45 ? "medium" : "low"} />
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
            </BaseCard>
          )}

          {sources.length > 0 && (
            <BaseCard title="Document Sources">

              <ResponsiveGrid min="260px">
                {sources.map((source, index) => (
                  <AISourceReference
                    key={`${source.document_id}-${source.chunk_index}`}
                    title={`Source ${index + 1}: ${source.filename}`}
                    source={`${source.category} - score ${source.score.toFixed(3)}${source.page_number ? ` - page ${source.page_number}` : ""}`}
                  />
                ))}
              </ResponsiveGrid>
            </BaseCard>
          )}
        </div>
      </div>
    </PageShell>
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
