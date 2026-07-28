"use client";

import {
  AIConfidenceBadge,
  AIJobStatus,
  AIRecommendationCard,
  AIThinkingPanel,
  ArchiveBadge,
  Banner,
  BaseCard,
  Breadcrumbs,
  Button,
  Checkbox,
  CommandPalette,
  ConnectionStatus,
  ContentPanel,
  DangerButton,
  Display,
  EmptyState,
  ErrorState,
  FileCard,
  FileLocationCard,
  FilterChip,
  GhostButton,
  HealthCard,
  IconButton,
  Inline,
  InlineAlert,
  KnowledgeCard,
  LoadingSkeleton,
  MasterCopyBadge,
  Metadata,
  ModuleTabs,
  PageHeader,
  PageShell,
  PageTitle,
  PrimaryButton,
  ProgressBar,
  ProgressRing,
  ProjectCard,
  RouteTransition,
  RecommendationCard,
  ResponsiveGrid,
  SearchCategoryList,
  SearchEmptyState,
  SearchGroup,
  SearchBadge,
  SearchHighlight,
  SearchInput,
  SearchMetadata,
  SearchPreview,
  SearchResultItem,
  RecentSearch,
  SecondaryButton,
  Select,
  SuggestionCard,
  StatusBadge,
  StorageCard,
  Toast,
  Switch,
  TagInput,
  TextArea,
  TextInput,
  WorkstationBadge,
} from "@/design-system";
import { EnterpriseMap } from "@/components/enterprise-map";
import { ExecutiveDemoGuide } from "@/components/executive-demo-guide";
import { demoSourceActivity } from "@/demo/data/experience";
import { buildWorkspaceBriefing } from "@/features/workspace/workspace-briefing";
import { ContinueWorking } from "@/features/workspace/components/ContinueWorking";
import { DailyBriefing } from "@/features/workspace/components/DailyBriefing";
import { EnterpriseHealthSummary } from "@/features/workspace/components/EnterpriseHealthSummary";
import { OperationalPulse } from "@/features/workspace/components/OperationalPulse";
import { TodayPriorities } from "@/features/workspace/components/TodayPriorities";
import { WorkspaceAIActivity } from "@/features/workspace/components/WorkspaceAIActivity";
import { Bell, ChevronDown, Download, MoreHorizontal, Search, Upload } from "lucide-react";

const swatches = [
  ["Workspace", "var(--ctv-accent-workspace)"],
  ["AI Studio", "var(--ctv-accent-ai-studio)"],
  ["Knowledge Center", "var(--ctv-accent-knowledge)"],
  ["Files", "var(--ctv-accent-files)"],
  ["Projects", "var(--ctv-accent-projects)"],
  ["My AI", "var(--ctv-accent-my-ai)"],
  ["Operations Center", "var(--ctv-accent-operations)"],
];

export default function DesignSystemPage() {
  const workspaceBriefing = buildWorkspaceBriefing({
    user: { email: "demo@chinoy.tv", full_name: "Alvin Demo", role: "manager", is_active: true },
    stats: { total_documents: 24, ready_documents: 17, failed_documents: 0, processing_documents: 2, total_chunks: 418, categories: { production: 12 } },
    infrastructure: [
      { key: "postgresql", label: "PostgreSQL", status: "healthy", category: "database", model: "Unknown", isHealthy: true },
      { key: "qdrant", label: "Qdrant", status: "healthy", category: "vector", model: "Unknown", isHealthy: true },
      { key: "embedding", label: "Embedding", status: "degraded", category: "ai", model: "local", isHealthy: false },
    ],
    now: new Date("2026-07-28T09:00:00"),
  });

  return (
    <main className="content">
      <PageShell className="ctv-showcase">
        <Breadcrumbs items={["CTV ONE", "Design System"]} />
        <PageHeader
          eyebrow="DESIGN SYSTEM V1.0"
          title={<PageTitle>CTV ONE component foundation</PageTitle>}
          description={<p className="ctv-body">Reusable tokens, states, and enterprise patterns for the Enterprise Intelligence Platform.</p>}
          action={<StatusBadge status="processing">Development reference</StatusBadge>}
        />

        <section className="ctv-section">
          <h2 className="ctv-section-title">Color Tokens</h2>
          <ResponsiveGrid min="170px">
            {swatches.map(([label, value]) => (
              <div className="ctv-token-swatch" key={label} style={{ background: value }}>
                {label}
              </div>
            ))}
          </ResponsiveGrid>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Typography</h2>
          <ContentPanel>
            <Display>Display Hero</Display>
            <PageTitle>Page Title</PageTitle>
            <h2 className="ctv-section-title">Section Title</h2>
            <h3 className="ctv-card-title">Card Title</h3>
            <p className="ctv-body">Body text supports calm, readable enterprise work.</p>
            <Metadata>Metadata describes source, timing, and status.</Metadata>
            <span className="ctv-caption">Caption text stays legible on dark surfaces.</span>
          </ContentPanel>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Buttons</h2>
          <Inline>
            <PrimaryButton leadingIcon={<Upload size={16} />}>Primary</PrimaryButton>
            <SecondaryButton>Secondary</SecondaryButton>
            <GhostButton>Ghost</GhostButton>
            <DangerButton>Danger</DangerButton>
            <Button variant="success">Success</Button>
            <Button loading>Loading</Button>
            <IconButton label="More actions"><MoreHorizontal size={18} /></IconButton>
          </Inline>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Inputs</h2>
          <ResponsiveGrid>
            <TextInput label="Project name" placeholder="Caloocan Fire Documentary" helperText="Use the public project title." />
            <SearchInput placeholder="Search Enterprise Assets" value="" />
            <Select label="Knowledge Space" defaultValue="production">
              <option value="production">Production</option>
              <option value="marketing">Marketing</option>
            </Select>
            <TextArea label="Brief" placeholder="Describe the work request." />
            <Checkbox label="Required reading" />
            <Switch label="Notify project team" checked readOnly />
            <TagInput tags={["Documentary", "Archive", "Approved"]} />
            <Inline><FilterChip selected>Projects</FilterChip><FilterChip>Files</FilterChip><FilterChip>Knowledge</FilterChip></Inline>
          </ResponsiveGrid>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Cards</h2>
          <ResponsiveGrid>
            <ProjectCard name="Caloocan Fire Documentary" status="In review" progress={72} nextAction="Review Interview_Lee_1987.mov summary" />
            <FileCard name="FireStation_Archive_1978.tif" location="Alibaba OSS / Archive Restoration" status="healthy" />
            <KnowledgeCard title="Production style guide" source="Knowledge Center / Production" required />
            <AIRecommendationCard title="Suggested next action" recommendation="Review the completed subtitle job before exporting the cut." />
            <HealthCard title="Knowledge Center" healthy detail="All approved sources are available." />
            <StorageCard title="CTV NAS" source="Enterprise File Discovery" online />
            <RecommendationCard title="Marketing presentation" reason="Recent campaign work uses approved brand assets." />
          </ResponsiveGrid>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Statuses</h2>
          <Inline>
            <StatusBadge status="healthy" />
            <StatusBadge status="processing" />
            <StatusBadge status="warning" />
            <StatusBadge status="critical" />
            <StatusBadge status="offline" />
            <ProgressRing value={68} />
          </Inline>
          <ProgressBar value={58} label="Indexing progress" />
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Alerts And States</h2>
          <ResponsiveGrid>
            <InlineAlert title="Knowledge updated" status="healthy">Production SOPs were refreshed today.</InlineAlert>
            <Banner title="Storage temporarily unavailable" status="warning">NAS discovery is delayed. Projects and Knowledge remain available.</Banner>
            <EmptyState title="No enterprise assets have been indexed yet">Connect a workstation, NAS, or cloud storage source to begin discovering company files.</EmptyState>
            <ErrorState title="AI job failed">The result could not be prepared. Try again or report the issue.</ErrorState>
            <BaseCard title="Loading skeleton"><LoadingSkeleton lines={4} /></BaseCard>
          </ResponsiveGrid>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">File Intelligence</h2>
          <ResponsiveGrid>
            <FileLocationCard source="CTV-NAS-01" owner="Production" drive="Z:" path="/Documentaries/Fire/Archive" online lastIndexed="12 min ago" access="Project team" />
            <BaseCard title="Copy state"><Inline><MasterCopyBadge /><ArchiveBadge /><WorkstationBadge name="EDIT-WS-02" /></Inline></BaseCard>
            <BaseCard title="Connection"><ConnectionStatus online /></BaseCard>
          </ResponsiveGrid>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">AI Components</h2>
          <ResponsiveGrid>
            <AIThinkingPanel steps={[
              { label: "Understanding your request", complete: true },
              { label: "Searching Enterprise Files", complete: true },
              { label: "Reading Knowledge Center" },
              { label: "Preparing response" },
            ]} />
            <BaseCard title="Job state"><Inline><AIJobStatus status="running" /><AIConfidenceBadge value="high" /></Inline></BaseCard>
          </ResponsiveGrid>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Universal Search</h2>
          <CommandPalette>
            <SearchInput placeholder="Search CTV ONE" value="" />
            <SearchCategoryList />
            <SearchGroup title="Projects">
              <SearchResultItem title="Caloocan Fire Documentary" meta="Project / In review" category="Projects" />
            </SearchGroup>
            <SearchEmptyState />
          </CommandPalette>
          <ResponsiveGrid min="240px">
            <BaseCard title="Search Source Status" meta="Progressive source discovery">
              <Inline>
                <SearchBadge status="healthy">Projects complete</SearchBadge>
                <SearchBadge status="processing">Checking Cloud</SearchBadge>
                <SearchBadge status="offline">NAS offline</SearchBadge>
              </Inline>
              <SearchMetadata>Each source reports status, count, availability, and timing independently.</SearchMetadata>
            </BaseCard>
            <BaseCard title="Recent Search" meta="Local history">
              <Inline>
                <RecentSearch label="Lee Chin" />
                <RecentSearch label="Archive" />
                <RecentSearch label="Storage Warning" />
              </Inline>
            </BaseCard>
            <SuggestionCard label="Continue Working" context="Workspace suggestion" />
            <SearchPreview title="Interview_Lee_1987.mov" meta="Files / Master / Indexed offline">
              <SearchMetadata>Owner: Production Archive</SearchMetadata>
              <SearchMetadata>Related project: <SearchHighlight>Caloocan Fire Documentary</SearchHighlight></SearchMetadata>
              <Inline>
                <SearchBadge status="healthy">Transcript available</SearchBadge>
                <SearchBadge status="processing">AI summary ready</SearchBadge>
              </Inline>
            </SearchPreview>
          </ResponsiveGrid>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Navigation And Motion</h2>
          <Inline>
            <ModuleTabs tabs={["Overview", "Files", "Knowledge"]} active="Overview" />
            <IconButton label="Search"><Search size={18} /></IconButton>
            <IconButton label="Notifications"><Bell size={18} /></IconButton>
            <IconButton label="Downloads"><Download size={18} /></IconButton>
            <IconButton label="Expand"><ChevronDown size={18} /></IconButton>
          </Inline>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Experience Layer</h2>
          <RouteTransition>
            <ResponsiveGrid>
              <BaseCard title="Executive Demo Mode" meta="Guided Sprint 3.0 presentation">
                <Metadata>
                  Workspace to Universal Search to Enterprise File Discovery to
                  Projects, Knowledge Center, My AI, Enterprise Map, and back home.
                </Metadata>
              </BaseCard>
              <BaseCard title="Page transition" meta="Subtle 325ms route reveal" interactive>
                <p className="ctv-metadata">Content enters without disturbing the stable shell.</p>
              </BaseCard>
              <BaseCard title="Source scan" meta="Demonstration data">
                <div className="ctv-source-scan">
                  {demoSourceActivity.slice(0, 3).map((source) => (
                    <div className="ctv-source-row" key={source.id}>
                      <span>{source.name}</span>
                      <StatusBadge status={source.status === "completed" ? "healthy" : "processing"}>
                        {source.resultsFound} found
                      </StatusBadge>
                    </div>
                  ))}
                </div>
              </BaseCard>
              <BaseCard title="Ambient AI presence" meta="Restrained notification pattern">
                <InlineAlert title="OCR completed" status="healthy">
                  OCR completed for FireStation_Archive_1978.tif. Demonstration data.
                </InlineAlert>
              </BaseCard>
              <BaseCard title="Offline state" meta="Non-color status language">
                <StatusBadge status="offline">Indexed but source offline</StatusBadge>
              </BaseCard>
            </ResponsiveGrid>
          </RouteTransition>
          <ExecutiveDemoGuide active="overview" onNavigate={() => undefined} onOpenSearch={() => undefined} />
          <EnterpriseMap />
          <Toast title="Demo completion">
            Project summary is ready. Demonstration data.
          </Toast>
        </section>

        <section className="ctv-section">
          <h2 className="ctv-section-title">Workspace Intelligence</h2>
          <DailyBriefing briefing={workspaceBriefing} />
          <OperationalPulse metrics={workspaceBriefing.pulse} />
          <ResponsiveGrid min="320px">
            <ContinueWorking item={workspaceBriefing.continueItem} />
            <TodayPriorities priorities={workspaceBriefing.priorities} />
          </ResponsiveGrid>
          <ResponsiveGrid min="320px">
            <WorkspaceAIActivity groups={workspaceBriefing.activityGroups} />
            <EnterpriseHealthSummary services={workspaceBriefing.health} />
          </ResponsiveGrid>
          <ResponsiveGrid min="260px">
            <BaseCard title="Workspace loading"><LoadingSkeleton lines={5} /></BaseCard>
            <EmptyState title="No urgent priorities require attention.">Workspace empty states stay section-level.</EmptyState>
            <InlineAlert title="Storage warning" status="warning">NAS usage at 91%. Demonstration data.</InlineAlert>
          </ResponsiveGrid>
        </section>
      </PageShell>
    </main>
  );
}
