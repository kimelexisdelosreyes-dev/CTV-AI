const assistants = [
  ["CTV-AI Auto", "Automatically routes each request to the correct specialist."],
  ["Production", "Documentaries, interviews, scripts, shot lists, and editing."],
  ["Graphics", "Branding, posters, thumbnails, and creative prompts."],
  ["Drone", "Aerial cinematography, planning, and equipment workflows."],
  ["IT", "Networking, NAS, Windows, Docker, storage, and troubleshooting."],
  ["Comedy", "Opt-in burnout breaks, friendly roasting, and team banter."],
];

export function Assistants() {
  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">SPECIALISTS</span><h1>AI Assistants</h1><p>One platform, multiple areas of expertise.</p></div>
      </div>
      <div className="assistant-grid">
        {assistants.map(([name, description]) => (
          <article className="assistant-card" key={name}>
            <div className="assistant-orb">{name.slice(0, 1)}</div>
            <h3>{name}</h3>
            <p>{description}</p>
            <span>Available in Open WebUI</span>
          </article>
        ))}
      </div>
    </section>
  );
}
