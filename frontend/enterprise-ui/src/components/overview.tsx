import { KnowledgeStats, User } from "@/lib/api";

type Props = {
  user: User;
  stats: KnowledgeStats | null;
  infrastructure: Record<string, string> | null;
};

export function Overview({ user, stats, infrastructure }: Props) {
  const cards = [
    ["Documents", stats?.total_documents ?? 0],
    ["Knowledge chunks", stats?.total_chunks ?? 0],
    ["Ready sources", stats?.ready_documents ?? 0],
    ["Failed sources", stats?.failed_documents ?? 0],
  ];

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">CTV ONE OPERATIONS</span>
          <h1>Good day, {user.full_name.split(" ")[0]}.</h1>
          <p>Your local AI platform is online and ready.</p>
        </div>
        <span className="role-pill">{user.role}</span>
      </div>

      <div className="metric-grid">
        {cards.map(([label, value]) => (
          <article className="metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>

      <div className="two-column">
        <article className="panel">
          <h2>Platform status</h2>
          {Object.entries(infrastructure ?? {}).map(([name, value]) => (
            <div className="status-row" key={name}>
              <span>{name}</span>
              <b className={value === "healthy" ? "good" : "bad"}>{value}</b>
            </div>
          ))}
        </article>

        <article className="panel">
          <h2>Next capabilities</h2>
          <div className="roadmap-item"><b>Company Brain</b><span>Controlled company knowledge and source-grounded answers.</span></div>
          <div className="roadmap-item"><b>Hokkien AI</b><span>Dictionary, annotation, and verified language learning.</span></div>
          <div className="roadmap-item"><b>Media Intelligence</b><span>Search transcripts, metadata, and eventually footage.</span></div>
        </article>
      </div>
    </section>
  );
}
