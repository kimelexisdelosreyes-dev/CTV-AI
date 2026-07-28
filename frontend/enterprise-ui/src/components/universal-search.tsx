"use client";

import { RefObject, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Command, Eye, History, Search, Sparkles, X } from "lucide-react";

import {
  IconButton,
  Inline,
  Metadata,
  ProgressBar,
  SearchEmptyState,
  SearchInput,
  RelationshipMap,
  RelationshipStrip,
  SecondaryButton,
  StatusBadge,
} from "@/design-system";
import {
  buildSearchViewModel,
  defaultSearchHistory,
  searchHistoryFromStorage,
  updateSearchHistory,
} from "@/features/search/search-intelligence";
import { relationshipPresentationForSearchResult, searchWithService } from "@/features/search/search-service-adapter";
import { createSearchService } from "@/services/search";
import type { SearchViewModel } from "@/features/search/search-types";
import type { RichSearchResult, SearchActionTarget } from "@/features/search/search-types";

type Props = {
  open: boolean;
  onClose: () => void;
  onNavigate: (target: SearchActionTarget) => void;
  returnFocusRef?: RefObject<HTMLElement | null>;
  activeContext?: SearchActionTarget;
};

const HISTORY_KEY = "ctv_universal_search_history";

export function UniversalSearch({
  open,
  onClose,
  onNavigate,
  returnFocusRef,
  activeContext = "overview",
}: Props) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [previewPinned, setPreviewPinned] = useState(false);
  const [viewModel, setViewModel] = useState<SearchViewModel>(() => buildSearchViewModel("Lee Chin interview", activeContext));
  const [history, setHistory] = useState<string[]>(defaultSearchHistory);
  const inputRef = useRef<HTMLInputElement>(null);
  const searchService = useMemo(() => createSearchService(), []);
  const searchAbortRef = useRef<AbortController | null>(null);
  const selected =
    viewModel.flatResults[selectedIndex] ?? viewModel.flatResults[0] ?? null;
  const selectedRelationshipPresentation = selected ? relationshipPresentationForSearchResult(selected) : null;

  const commitHistory = useCallback((nextQuery: string) => {
    const next = updateSearchHistory(history, nextQuery);
    setHistory(next);
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  }, [history]);

  const closeAndReturnFocus = useCallback(() => {
    onClose();
    returnFocusRef?.current?.focus();
  }, [onClose, returnFocusRef]);

  const openResult = useCallback((result: RichSearchResult) => {
    commitHistory(query || result.title);
    onNavigate(result.target);
    closeAndReturnFocus();
  }, [closeAndReturnFocus, commitHistory, onNavigate, query]);

  useEffect(() => {
    if (!open) return;
    const handle = window.setTimeout(() => {
      setHistory(
        searchHistoryFromStorage(window.localStorage.getItem(HISTORY_KEY)),
      );
      inputRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(handle);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    searchAbortRef.current?.abort();
    searchAbortRef.current = controller;
    const handle = window.setTimeout(() => {
      void searchWithService(searchService, query || "Lee Chin interview", { module: activeContext, signal: controller.signal }).then((next) => {
        if (!controller.signal.aborted) {
          setViewModel(next);
          setSelectedIndex(0);
        }
      }).catch(() => undefined);
    }, query ? 140 : 0);
    return () => { window.clearTimeout(handle); controller.abort(); };
  }, [activeContext, open, query, searchService]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeAndReturnFocus();
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedIndex((current) =>
          Math.min(current + 1, Math.max(viewModel.flatResults.length - 1, 0)),
        );
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedIndex((current) => Math.max(current - 1, 0));
      }
      if (event.key === "Tab") {
        event.preventDefault();
        setSelectedIndex((current) => {
          const last = Math.max(viewModel.flatResults.length - 1, 0);
          return event.shiftKey
            ? Math.max(current - 1, 0)
            : Math.min(current + 1, last);
        });
      }
      if (event.key === "Enter" && selected) {
        event.preventDefault();
        if (event.ctrlKey || event.metaKey) {
          setPreviewPinned((current) => !current);
        } else {
          openResult(selected);
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closeAndReturnFocus, open, openResult, selected, viewModel.flatResults.length]);

  if (!open) return null;

  return (
    <div className="ctv-overlay ctv-fade-in" role="presentation">
      <div
        aria-label="Universal Search"
        aria-modal="true"
        className="ctv-card ctv-command-shell ctv-slide-in-down search-command-center"
        role="dialog"
      >
        <Inline className="search-command-center__topbar">
          <StatusBadge status={viewModel.state === "partial" ? "warning" : "processing"}>
            {viewModel.state}
          </StatusBadge>
          <Metadata>Ctrl/Cmd+K / Arrows / Tab / Enter / Ctrl+Enter preview</Metadata>
          <IconButton label="Close Universal Search" onClick={closeAndReturnFocus}>
            <X size={16} />
          </IconButton>
        </Inline>

        <SearchInput
          aria-label="Search CTV ONE"
          onChange={(event) => {
            setQuery(event.target.value);
            setSelectedIndex(0);
          }}
          onClear={() => {
            setQuery("");
            setSelectedIndex(0);
          }}
          placeholder="Search projects, files, knowledge, people, AI jobs, and settings"
          ref={inputRef}
          value={query}
        />

        <div className="search-history-suggestions">
          <section aria-label="Recent searches">
            <Inline>
              <History size={15} aria-hidden="true" />
              <strong>Recent</strong>
            </Inline>
            <Inline gap="8px">
              {(history.length ? history : defaultSearchHistory)
                .slice(0, 6)
                .map((item) => (
                  <button
                    className="ctv-chip"
                    key={item}
                    onClick={() => {
                      setQuery(item);
                      setSelectedIndex(0);
                    }}
                    type="button"
                  >
                    {item}
                  </button>
                ))}
              {history.length > 0 && (
                <button
                  className="ctv-chip"
                  onClick={() => {
                    setHistory([]);
                    window.localStorage.removeItem(HISTORY_KEY);
                  }}
                  type="button"
                >
                  Clear
                </button>
              )}
            </Inline>
          </section>
          <section aria-label="Suggested searches">
            <Inline>
              <Sparkles size={15} aria-hidden="true" />
              <strong>Suggested</strong>
            </Inline>
            <Inline gap="8px">
              {viewModel.suggestions.map((suggestion) => (
                <button
                  className="ctv-chip"
                  key={suggestion.id}
                  onClick={() => {
                    setQuery(suggestion.query);
                    setSelectedIndex(0);
                  }}
                  type="button"
                >
                  <Command size={13} aria-hidden="true" />
                  {suggestion.label}
                  <span className="ctv-caption">{suggestion.context}</span>
                </button>
              ))}
            </Inline>
          </section>
        </div>

        <div className="search-source-strip" aria-live="polite">
          {viewModel.sources.map((source) => (
            <div className="search-source" key={source.id}>
              <Inline>
                <strong>{source.label}</strong>
                <StatusBadge status={source.tone}>{source.status}</StatusBadge>
              </Inline>
              <Metadata>
                {source.itemsFound} found / {source.time} / {source.availability}
              </Metadata>
              <Metadata>{source.message}</Metadata>
            </div>
          ))}
        </div>

        <div className="search-main-grid">
          <div
            aria-activedescendant={
              selected ? `search-result-${selected.id}` : undefined
            }
            aria-label="Search results"
            className="search-results-pane"
            role="listbox"
          >
            <div className="ctv-caption" aria-live="polite">
              {viewModel.announcement}
            </div>
            {viewModel.flatResults.length === 0 ? <SearchEmptyState /> : null}
            {viewModel.groups.map((group) => (
              <section
                aria-label={group.category}
                className="search-result-group"
                key={group.category}
              >
                <h2 className="ctv-card-title">{group.category}</h2>
                {group.results.map((item) => {
                  const index = viewModel.flatResults.findIndex(
                    (result) => result.id === item.id,
                  );
                  const selectedResult = index === selectedIndex;
                  return (
                    <button
                      aria-selected={selectedResult}
                      className="search-result-row"
                      id={`search-result-${item.id}`}
                      key={item.id}
                      onClick={() => setSelectedIndex(index)}
                      onDoubleClick={() => openResult(item)}
                      role="option"
                      type="button"
                    >
                      <span className="search-result-icon" aria-hidden="true">
                        <Search size={16} />
                      </span>
                      <span className="ctv-search-result-copy">
                        <strong>{item.title}</strong>
                        <Metadata>{item.metadata.join(" / ")}</Metadata>
                        {item.progress !== undefined && (
                          <ProgressBar
                            label={`${item.title} progress`}
                            value={item.progress}
                          />
                        )}
                      </span>
                      <StatusBadge status={item.tone}>{item.status}</StatusBadge>
                      {selectedResult ? <ArrowRight size={16} aria-hidden="true" /> : null}
                    </button>
                  );
                })}
              </section>
            ))}
          </div>

          <aside
            aria-label="Search result preview"
            aria-live="polite"
            className="search-preview-panel"
            data-pinned={previewPinned ? "true" : "false"}
          >
            {selected ? (
              <>
                <Inline className="search-preview-panel__title">
                  <Eye size={18} aria-hidden="true" />
                  <div>
                    <h2 className="ctv-card-title">{selected.title}</h2>
                    <Metadata>
                      {selected.iconLabel} / {selected.category}
                    </Metadata>
                  </div>
                  <StatusBadge status={selected.tone}>{selected.status}</StatusBadge>
                </Inline>
                <p className="ctv-body">{selected.summary}</p>
                <div className="search-preview-facts">
                  {selected.preview.map((fact) => (
                    <div key={fact.label}>
                      <span className="ctv-caption">{fact.label}</span>
                      <strong>{fact.value}</strong>
                    </div>
                  ))}
                </div>
                <section
                  aria-label="Enterprise relationships"
                  className="search-relationships"
                >
                  <h3 className="ctv-card-title">Enterprise Relationships</h3>
                  {(selectedRelationshipPresentation?.relationships ?? selected.relationships).map((relationship) => (
                    <div
                      className="search-relationship"
                      key={`${relationship.label}-${relationship.value}`}
                    >
                      <span>{relationship.label}</span>
                      <StatusBadge status={"tone" in relationship ? relationship.tone : relationship.resolved ? "healthy" : "neutral"}>
                        {relationship.value}
                      </StatusBadge>
                    </div>
                  ))}
                </section>
                <RelationshipStrip items={(selectedRelationshipPresentation?.relationships ?? selected.relationships).slice(0, 4).map((relationship) => ({ type: relationship.label as "Project", title: relationship.value, tone: "tone" in relationship ? relationship.tone : relationship.resolved ? "healthy" : "neutral" }))} />
                <RelationshipMap items={(selectedRelationshipPresentation?.relationships ?? selected.relationships).slice(0, 5).map((relationship) => ({ type: relationship.label as "Project", title: relationship.value, tone: "tone" in relationship ? relationship.tone : relationship.resolved ? "healthy" : "neutral" }))} />
                <SecondaryButton
                  leadingIcon={<ArrowRight size={15} aria-hidden="true" />}
                  onClick={() => openResult(selected)}
                >
                  {selected.action}
                </SecondaryButton>
              </>
            ) : (
              <SearchEmptyState />
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
