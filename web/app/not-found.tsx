import Link from "next/link";

export default function NotFound() {
  return (
    <section className="errorPanel">
      <h1>Not found</h1>
      <p>The requested project, chapter, or page is unavailable.</p>
      <Link className="button" href="/">
        Back to projects
      </Link>
    </section>
  );
}
