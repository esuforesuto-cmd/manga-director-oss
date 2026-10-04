import type { ProjectDetail } from "@/lib/api/types";

import { ProjectActions } from "./project-actions";
import styles from "./project-detail.module.css";

export function ProjectDetailView({ project }: Readonly<{ project: ProjectDetail }>) {
  return (
    <section aria-labelledby="project-heading">
      <div className="pageHeading">
        <div>
          <p className="eyebrow">{project.id}</p>
          <h1 id="project-heading">{project.title}</h1>
        </div>
        <ProjectActions projectId={project.id} />
      </div>
      <dl className={styles.summary}>
        <div><dt>Current chapter</dt><dd>{project.currentChapter ?? "—"}</dd></div>
        <div><dt>Current page</dt><dd>{project.currentPage ?? "—"}</dd></div>
        <div><dt>Workflow state</dt><dd>{project.workflow.currentState}</dd></div>
        <div><dt>Progress</dt><dd>{project.progress.completed} / {project.progress.total}</dd></div>
      </dl>
      <h2>Chapters</h2>
      <ul className={styles.chapters}>
        {project.chapters.map((chapter) => (
          <li key={chapter.id}>
            <a href={`/projects/${encodeURIComponent(project.id)}/chapters/${encodeURIComponent(chapter.id)}`}>
              <strong>{chapter.title}</strong><span>{chapter.approvedPages} / {chapter.pageCount} approved</span>
            </a>
          </li>
        ))}
      </ul>
      {project.currentPage !== null ? (
        <p><a className="button secondary" href={`/projects/${encodeURIComponent(project.id)}/pages/${project.currentPage}`}>Open current page</a></p>
      ) : null}
      <h2>Workflow history</h2>
      <ol className={styles.history}>{project.workflow.history.map((entry, index) => <li key={index}>{JSON.stringify(entry)}</li>)}</ol>
    </section>
  );
}
