import Link from "next/link";

export function EmptyState() {
  return (
    <section className="emptyState" aria-label="No projects">
      <h2>No projects yet</h2>
      <p>Create a project to begin a page-at-a-time production workflow.</p>
      <Link className="button" href="/projects/new">
        Create project
      </Link>
    </section>
  );
}
