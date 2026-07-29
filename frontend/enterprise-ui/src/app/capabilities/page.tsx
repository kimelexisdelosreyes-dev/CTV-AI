"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import "./capabilities.css";
import {
  executeCapability,
  listCapabilities,
  type CapabilityExecutionResponse,
  type CapabilitySummary,
} from "@/features/capabilities/api";
import { CapabilityCatalog } from "@/features/capabilities/components/CapabilityCatalog";
import { CapabilityDetail } from "@/features/capabilities/components/CapabilityDetail";
import { CapabilityEmpty } from "@/features/capabilities/components/CapabilityEmpty";
import { CapabilityInput } from "@/features/capabilities/components/CapabilityInput";
import { CapabilityLayout } from "@/features/capabilities/components/CapabilityLayout";
import { CapabilityLoading } from "@/features/capabilities/components/CapabilityLoading";
import { CapabilityResult } from "@/features/capabilities/components/CapabilityResult";

export default function Page() {
  const enabled = process.env.NEXT_PUBLIC_CTV_ONE_CAPABILITIES_ENABLED === "true";
  const [items, setItems] = useState<CapabilitySummary[]>([]);
  const [selected, setSelected] = useState<CapabilitySummary>();
  const [text, setText] = useState("");
  const [result, setResult] = useState<CapabilityExecutionResponse>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(enabled);
  const [busy, setBusy] = useState(false);

  const retry = () => {
    setError("");
    setLoading(true);
    listCapabilities()
      .then(setItems)
      .catch(() => setError("Capabilities could not be loaded. Check your connection and try again."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (enabled) {
      listCapabilities()
        .then(setItems)
        .catch(() => setError("Capabilities could not be loaded. Check your connection and try again."))
        .finally(() => setLoading(false));
    }
  }, [enabled]);

  if (!enabled) {
    return (
      <CapabilityLayout>
        <CapabilityEmpty message="Capability tools are not currently enabled." />
      </CapabilityLayout>
    );
  }

  return (
    <CapabilityLayout>
      <Link href="/">Back to chat</Link>
      <h1>Capabilities</h1>
      {error && <section className="capability-error" role="alert"><h2>We could not complete that request</h2><p>{error}</p><p>Try again in a moment. If this continues, contact your support team.</p><button type="button" onClick={retry}>Retry</button></section>}
      {loading ? (
        <CapabilityLoading capabilityId={selected?.capability_id} />
      ) : items.length ? (
        <div className="capability-grid">
          <CapabilityCatalog items={items} selectedId={selected?.capability_id} onSelect={(item) => { setSelected(item); setResult(undefined); setError(""); }} />
          <div className="capability-workspace__main">
            <CapabilityDetail item={selected} />
            {selected && (
              <CapabilityInput
                value={text}
                onChange={setText}
                busy={busy}
                capabilityName={selected.name}
                onSubmit={() => {
                  setBusy(true);
                  executeCapability(selected.capability_id, text)
                    .then(setResult)
                    .catch(() => setError("The capability could not complete this request."))
                    .finally(() => setBusy(false));
                }}
              />
            )}
            <CapabilityResult result={result} />
          </div>
        </div>
      ) : (
        <CapabilityEmpty message="No capabilities are available." />
      )}
    </CapabilityLayout>
  );
}
