import { notFound } from "next/navigation";

import { ChapterDetailView } from "@/components/chapter-detail";
import { ApiClientError, api } from "@/lib/api/client";

export default async function ChapterDetailPage({
  params
}: Readonly<{ params: Promise<{ projectId: string; chapterId: string }> }>) {
  const { chapterId, projectId } = await params;
  try {
    const chapter = await api.chapters.get(projectId, chapterId);
    return <ChapterDetailView projectId={projectId} chapter={chapter} />;
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) notFound();
    throw error;
  }
}
