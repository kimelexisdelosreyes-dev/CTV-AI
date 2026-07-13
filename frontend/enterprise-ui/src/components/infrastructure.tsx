type Props = { data: Record<string, string> | null };

export function Infrastructure({ data }: Props) {
  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">SYSTEM HEALTH</span><h1>Infrastructure</h1><p>Live health from CTV-AI Core.</p></div>
      </div>
      <div className="assistant-grid">
        {Object.entries(data ?? {}).map(([name, value]) => (
          <article className="assistant-card" key={name}>
            <div className={value === "healthy" ? "health-dot good-bg" : "health-dot bad-bg"} />
            <h3>{name}</h3>
            <p className={value === "healthy" ? "good" : "bad"}>{value}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
