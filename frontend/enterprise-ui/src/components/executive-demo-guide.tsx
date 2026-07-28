"use client";

import { ArrowRight, CheckCircle2, Search } from "lucide-react";

import {
  BaseCard,
  GhostButton,
  Inline,
  Metadata,
  PrimaryButton,
  ProgressBar,
  StatusBadge,
} from "@/design-system";
import { Section } from "@/components/sidebar";

type DemoStep = {
  id: string;
  title: string;
  module: string;
  target: Section;
  cue: string;
  actionLabel: string;
  opensSearch?: boolean;
};

const demoSteps: DemoStep[] = [
  {
    id: "workspace",
    title: "Start in Workspace",
    module: "Workspace",
    target: "overview",
    cue: "Review priorities, AI updates, and Enterprise Control Center status.",
    actionLabel: "Open Workspace",
  },
  {
    id: "search",
    title: "Search Lee Chin interview",
    module: "Universal Search",
    target: "overview",
    cue: "Find Caloocan Fire Documentary, Interview_Lee_1987.mov, and related knowledge.",
    actionLabel: "Open Search",
    opensSearch: true,
  },
  {
    id: "files",
    title: "Inspect Enterprise File Discovery",
    module: "Files",
    target: "files",
    cue: "Show master, proxy, duplicate, offline NAS, and Alibaba OSS archive states.",
    actionLabel: "Open Files",
  },
  {
    id: "projects",
    title: "Connect the project",
    module: "Projects",
    target: "operations",
    cue: "Use Project Intelligence to connect files, transcripts, knowledge, and work sessions.",
    actionLabel: "Open Projects",
  },
  {
    id: "knowledge",
    title: "Verify Organizational Memory",
    module: "Knowledge Center",
    target: "knowledge",
    cue: "Surface approved archive interview handling guidance.",
    actionLabel: "Open Knowledge",
  },
  {
    id: "my-ai",
    title: "Ask My AI for a source-grounded summary",
    module: "My AI",
    target: "brain",
    cue: "Show visible AI activity without exposing private reasoning.",
    actionLabel: "Open My AI",
  },
  {
    id: "map",
    title: "Trace Enterprise Infrastructure",
    module: "Enterprise Control Center",
    target: "infrastructure",
    cue: "Follow NAS to Knowledge Center to AI Core to project to Workspace.",
    actionLabel: "Open Map",
  },
  {
    id: "home",
    title: "Return to Workspace",
    module: "Workspace",
    target: "overview",
    cue: "Close with ambient AI completion and the next executive action.",
    actionLabel: "Return Home",
  },
];

type Props = {
  active: Section;
  onNavigate: (section: Section) => void;
  onOpenSearch: () => void;
};

export function ExecutiveDemoGuide({ active, onNavigate, onOpenSearch }: Props) {
  const currentIndex = Math.max(
    demoSteps.findIndex((step) => step.target === active && !step.opensSearch),
    0,
  );
  const nextStep = demoSteps[currentIndex + 1] ?? demoSteps[0];
  const progress = Math.round(((currentIndex + 1) / demoSteps.length) * 100);

  function activate(step: DemoStep) {
    if (step.opensSearch) {
      onOpenSearch();
      return;
    }
    onNavigate(step.target);
  }

  return (
    <BaseCard
      className="ctv-executive-guide ctv-slide-in-down"
      title="Executive Demo Mode"
      meta="Sprint 3.0 guided presentation path"
      action={<StatusBadge status="processing">{progress}%</StatusBadge>}
    >
      <ProgressBar value={progress} label="Executive demo progress" />
      <div className="ctv-demo-steps" aria-label="Executive demonstration steps">
        {demoSteps.map((step, index) => {
          const isCurrent = index === currentIndex;
          const isComplete = index < currentIndex;
          return (
            <button
              aria-current={isCurrent ? "step" : undefined}
              className="ctv-demo-step"
              data-current={isCurrent ? "true" : "false"}
              key={step.id}
              onClick={() => activate(step)}
              type="button"
            >
              {isComplete ? <CheckCircle2 size={15} /> : <span>{index + 1}</span>}
              <strong>{step.module}</strong>
            </button>
          );
        })}
      </div>
      <Inline>
        <PrimaryButton onClick={() => activate(nextStep)} trailingIcon={<ArrowRight size={16} />}>
          {nextStep.actionLabel}
        </PrimaryButton>
        <GhostButton onClick={onOpenSearch} leadingIcon={<Search size={16} />}>
          Search Lee Chin
        </GhostButton>
      </Inline>
      <Metadata>{nextStep.title}: {nextStep.cue}</Metadata>
    </BaseCard>
  );
}
