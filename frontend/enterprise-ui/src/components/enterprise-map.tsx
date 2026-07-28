"use client";

import { useMemo, useState } from "react";
import type { CSSProperties } from "react";

import {
  BaseCard,
  Inline,
  Metadata,
  StatusBadge,
} from "@/design-system";
import { enterpriseMapDemo } from "@/demo/adapters/experience";
import { DemoMapConnection, DemoMapNode } from "@/demo/types";

function tone(status: DemoMapNode["status"]): "healthy" | "processing" | "warning" | "critical" | "offline" | "neutral" {
  if (status === "completed") return "healthy";
  if (status === "running" || status === "starting" || status === "queued") return "processing";
  if (status === "warning" || status === "waiting") return "warning";
  if (status === "failed") return "critical";
  if (status === "offline") return "offline";
  return "neutral";
}

function connectionStyle(connection: DemoMapConnection, nodes: DemoMapNode[]) {
  const from = nodes.find((node) => node.id === connection.from);
  const to = nodes.find((node) => node.id === connection.to);
  if (!from || !to) return {};
  const x1 = from.x;
  const y1 = from.y;
  const x2 = to.x;
  const y2 = to.y;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);
  return {
    left: `${x1}%`,
    top: `${y1}%`,
    width: `${length}%`,
    transform: `rotate(${angle}deg)`,
  };
}

export function EnterpriseMap() {
  const { nodes, connections } = useMemo(() => enterpriseMapDemo(), []);
  const [selectedId, setSelectedId] = useState("core");
  const selected = nodes.find((node) => node.id === selectedId) ?? nodes[0];
  const related = new Set([selected.id, ...selected.dependencies]);
  const demoPath = ["nas", "knowledge", "core", "ai", "project", "workspace"];

  function nodePosition(node: DemoMapNode): CSSProperties {
    return {
      "--node-x": `${node.x}%`,
      "--node-y": `${node.y}%`,
    } as CSSProperties;
  }

  return (
    <section className="ctv-enterprise-map" aria-label="Enterprise Map demonstration topology">
      <div className="ctv-map-canvas" role="listbox" aria-label="Demonstration topology nodes">
        {connections.map((connection) => (
          <span
            aria-hidden="true"
            className="ctv-map-connection"
            data-active={connection.from === selected.id || connection.to === selected.id ? "true" : "false"}
            key={`${connection.from}-${connection.to}`}
            style={connectionStyle(connection, nodes)}
          />
        ))}
        {nodes.map((node) => (
          <button
            aria-selected={node.id === selected.id}
            className="ctv-map-node"
            data-muted={!related.has(node.id) ? "true" : "false"}
            data-selected={node.id === selected.id ? "true" : "false"}
            key={node.id}
            onClick={() => setSelectedId(node.id)}
            role="option"
            style={nodePosition(node)}
          >
            <strong>{node.label}</strong>
            <Metadata>{node.type}</Metadata>
            <StatusBadge status={tone(node.status)}>{node.status}</StatusBadge>
          </button>
        ))}
      </div>
      <BaseCard title={selected.label} meta="Demonstration topology">
        <Inline>
          {demoPath.map((nodeId) => {
            const node = nodes.find((item) => item.id === nodeId);
            if (!node) return null;
            return (
              <button
                className="ctv-chip"
                data-selected={selected.id === node.id ? "true" : "false"}
                key={node.id}
                onClick={() => setSelectedId(node.id)}
                type="button"
              >
                {node.label}
              </button>
            );
          })}
        </Inline>
        <Inline>
          <StatusBadge status={tone(selected.status)}>{selected.status}</StatusBadge>
          <StatusBadge status="neutral">{selected.type}</StatusBadge>
        </Inline>
        <Metadata>{selected.activity}</Metadata>
        <Metadata>Dependencies: {selected.dependencies.join(", ") || "none"}</Metadata>
        <Metadata>
          Real-time topology is not connected in this sprint. This panel uses
          frontend demonstration data.
        </Metadata>
      </BaseCard>
    </section>
  );
}
