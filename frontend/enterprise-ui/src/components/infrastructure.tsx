import { DeveloperConsole } from "@/components/developer-console";
import { User } from "@/lib/api";
import { InfrastructureStatusRow } from "@/lib/infrastructure-status";

type Props = {
  data: InfrastructureStatusRow[] | null;
  user: User;
};

export function Infrastructure({ data, user }: Props) {
  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">SYSTEM HEALTH</span>
          <h1>Infrastructure</h1>
          <p>Live health from CTV-AI Core.</p>
        </div>
      </div>

      <div className="assistant-grid">
        {(data ?? []).map((service) => (
          <article className="assistant-card" key={service.key}>
            <div
              className={
                service.isHealthy ? "health-dot good-bg" : "health-dot bad-bg"
              }
            />
            <h3>{service.label}</h3>
            <p className={service.isHealthy ? "good" : "bad"}>
              Status: {service.status}
            </p>
            <p>Category: {service.category}</p>
            <p>Model: {service.model}</p>
          </article>
        ))}
      </div>

      {!data?.length && <p className="muted">Status data is unavailable.</p>}

      {user.role === "admin" && <DeveloperConsole />}
    </section>
  );
}
