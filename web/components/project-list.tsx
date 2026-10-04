import type { ProjectSummary } from "@/lib/api/types";

import styles from "./project-list.module.css";

export function ProjectList({ projects }: Readonly<{ projects: ProjectSummary[] }>) {
  return (
    <div className={styles.grid} aria-label="Projects">
      {projects.map((project) => (
        <article className={styles.card} key={project.id}>
          <div>
            <p className={styles.id}>{project.id}</p>
            <h2>{project.title}</h2>
          </div>
          <dl className={styles.meta}>
            <div><dt>Current state</dt><dd>{project.currentState ?? "Not started"}</dd></div>
            <div><dt>Progress</dt><dd>{project.progress.completed} / {project.progress.total} pages</dd></div>
            <div><dt>Updated</dt><dd>{new Date(project.updatedAt).toLocaleString()}</dd></div>
          </dl>
          <a className="button" href={`/projects/${encodeURIComponent(project.id)}`}>Open project</a>
        </article>
      ))}
    </div>
  );
}
