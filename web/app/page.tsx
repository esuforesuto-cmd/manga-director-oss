import { EmptyState } from "@/components/empty-state";
import { ProjectList } from "@/components/project-list";
import { api } from "@/lib/api/client";

export default async function ProjectsPage() {
  const projects = await api.projects.list();

  return (
    <section aria-labelledby="projects-heading">
      <div className="pageHeading">
        <div>
          <p className="eyebrow">Production dashboard</p>
          <h1 id="projects-heading">Projects</h1>
        </div>
        <Link className="button" href="/projects/new">
          Create project
        </Link>
      </div>
      {projects.length ? <ProjectList projects={projects} /> : <EmptyState />}
    </section>
  );
}
import Link from "next/link";
