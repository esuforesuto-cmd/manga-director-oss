import { notFound } from "next/navigation";

import { ProjectDetailView } from "@/components/project-detail";
import { ApiClientError, api } from "@/lib/api/client";

export default async function ProjectDetailPage({
  params
}: Readonly<{ params: Promise<{ projectId: string }> }>) {
  const { projectId } = await params;
  try {
    const project = await api.projects.get(projectId);
    return <ProjectDetailView project={project} />;
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) notFound();
    throw error;
  }
}
