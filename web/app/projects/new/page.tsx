"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ApiClientError, api } from "@/lib/api/client";

export default function NewProjectPage() {
  const router = useRouter();
  const [id, setId] = useState("");
  const [title, setTitle] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const project = await api.projects.create({ id, title });
      router.push(`/projects/${encodeURIComponent(project.id)}`);
    } catch (cause) {
      setError(cause instanceof ApiClientError ? cause.message : "Project creation failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="formPanel" aria-labelledby="new-project-heading">
      <p className="eyebrow">Project setup</p>
      <h1 id="new-project-heading">Create project</h1>
      <form onSubmit={submit}>
        <label htmlFor="project-id">Project ID</label>
        <input id="project-id" value={id} required onChange={(event) => setId(event.target.value)} />
        <label htmlFor="project-title">Title</label>
        <input id="project-title" value={title} required onChange={(event) => setTitle(event.target.value)} />
        <div className="actionGroup">
          <button className="button" type="submit" disabled={pending}>
            Create project
          </button>
          <Link className="button secondary" href="/">
            Cancel
          </Link>
        </div>
        {error ? <p className="inlineError" role="alert">{error}</p> : null}
      </form>
    </section>
  );
}
