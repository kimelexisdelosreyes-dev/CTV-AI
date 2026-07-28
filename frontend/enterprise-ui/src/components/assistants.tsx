import {
  AIRecommendationCard,
  EmptyState,
  PageHeader,
  PageShell,
  PageTitle,
  PrimaryButton,
  ResponsiveGrid,
  StatusBadge,
} from "@/design-system";

const assistants = [
  ["Write", "Draft scripts, briefs, captions, and production notes."],
  ["Research", "Search approved Organizational Memory and project context."],
  ["Generate Subtitles", "Prepare subtitles for review and export."],
  ["Enhance Images", "Improve production and archive images for review."],
  ["Build Presentations", "Create polished decks from approved context."],
  ["Search Archives", "Find useful historical material and Enterprise Assets."],
];

export function Assistants() {
  return (
    <PageShell>
      <PageHeader
        eyebrow="AI STUDIO"
        title={<PageTitle>AI Studio</PageTitle>}
        description={<p className="ctv-body">Capability-first AI workflows for writing, research, media, and production work.</p>}
        action={<StatusBadge status="processing">AI Activity ready</StatusBadge>}
      />
      <ResponsiveGrid min="240px">
        {assistants.map(([name, description]) => (
          <AIRecommendationCard
            action={<PrimaryButton size="small">Open</PrimaryButton>}
            key={name}
            recommendation={description}
            title={name}
          />
        ))}
      </ResponsiveGrid>
      <EmptyState title="No AI jobs are currently running.">
        Start a capability above when you are ready to create, research, or
        prepare production assets.
      </EmptyState>
    </PageShell>
  );
}
