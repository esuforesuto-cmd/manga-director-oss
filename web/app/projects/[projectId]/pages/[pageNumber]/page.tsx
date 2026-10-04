import { notFound } from "next/navigation";

import { PageWorkflowView } from "@/components/page-workflow";
import { ApiClientError, api } from "@/lib/api/client";

export default async function PageWorkflowPage({
  params
}: Readonly<{ params: Promise<{ projectId: string; pageNumber: string }> }>) {
  const { pageNumber: pageNumberParam, projectId } = await params;
  const pageNumber = Number(pageNumberParam);
  if (!Number.isSafeInteger(pageNumber) || pageNumber < 1) notFound();
  try {
    const page = await api.pages.get(projectId, pageNumber);
    return <PageWorkflowView projectId={projectId} page={page} />;
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) notFound();
    throw error;
  }
}
