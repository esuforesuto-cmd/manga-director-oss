"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiClientError } from "@/lib/api/client";
import type { PanelRectangleInput, StoryboardPanelSummary } from "@/lib/api/types";

type RectangleDraft = { left: string; top: string; right: string; bottom: string };
const markerKey = (projectId: string, pageNumber: number) => `md-panel-generation-v1:${encodeURIComponent(projectId)}:${pageNumber}`;

export function PanelAwareGenerationForm({ projectId, pageNumber, panels }: Readonly<{
  projectId: string; pageNumber: number; panels: StoryboardPanelSummary[];
}>) {
  const router = useRouter();
  const storageKey = useMemo(() => markerKey(projectId, pageNumber), [projectId, pageNumber]);
  const [authorizedBy, setAuthorizedBy] = useState("");
  const [checkpointName, setCheckpointName] = useState("");
  const [rectangles, setRectangles] = useState<RectangleDraft[]>(panels.map(() => ({ left: "", top: "", right: "", bottom: "" })));
  const [markerExists, setMarkerExists] = useState(true);
  const [message, setMessage] = useState("Panel generation is available for this saved Storyboard.");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    try { setMarkerExists(window.localStorage.getItem(storageKey) !== null); }
    catch { setMarkerExists(true); setMessage("Local browser storage is unavailable. Generation is disabled for safety."); }
    const onStorage = (event: StorageEvent) => { if (event.key === storageKey && event.newValue !== null) setMarkerExists(true); };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [storageKey]);

  const rectangleValues: PanelRectangleInput[] | null = rectangles.every((draft) =>
    Object.values(draft).every((value) => /^(0|[1-9][0-9]{0,6})$/.test(value))
  ) ? rectangles.map((draft) => ({ left: Number(draft.left), top: Number(draft.top), right: Number(draft.right), bottom: Number(draft.bottom) })) : null;
  const geometryValid = rectangleValues !== null && rectangleValues.every((rect) =>
    Object.values(rect).every((value) => Number.isInteger(value) && value >= 0 && value <= 1_000_000)
    && rect.left < rect.right && rect.top < rect.bottom
  );
  const canSubmit = authorizedBy.trim().length > 0 && authorizedBy.length <= 128
    && checkpointName.trim().length > 0 && checkpointName.length <= 128 && geometryValid && !markerExists && !busy;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || !rectangleValues) return;
    if (!navigator.locks?.request) { setMessage("This browser cannot safely coordinate tabs. Generation is disabled."); return; }
    setBusy(true);
    try {
      await navigator.locks.request(`md-panel-generation-lock:${storageKey}`, { mode: "exclusive", ifAvailable: true }, async (lock) => {
        if (!lock) { setMessage("Another tab is handling this Page. Check its result before continuing."); return; }
        try {
          if (window.localStorage.getItem(storageKey) !== null) {
            setMarkerExists(true); setMessage("A previous attempt may have started. Check the Page status; do not resend from this screen."); return;
          }
          const marker = JSON.stringify({ createdAt: new Date().toISOString(), owner: crypto.randomUUID() });
          window.localStorage.setItem(storageKey, marker);
          setMarkerExists(true);
          setMessage("Generation started. Keep this Page open while the result is confirmed.");
          try {
            await api.pages.generatePanels(projectId, pageNumber, {
              requestVersion: 1, authorizedBy: authorizedBy.trim(), checkpointName: checkpointName.trim(),
              layoutProfileId: "md-page-compositor-v1", layoutProfileVersion: 1, rectangles: rectangleValues
            });
            setMessage("Generation completed. Refreshing the saved Page status.");
            router.refresh();
          } catch (error) {
            if (error instanceof ApiClientError
              && ((error.status === 422 && error.payload?.code === "invalid_input")
                || (error.status === 409 && error.payload?.code === "revision_conflict"))) {
              if (window.localStorage.getItem(storageKey) === marker) window.localStorage.removeItem(storageKey);
              setMarkerExists(window.localStorage.getItem(storageKey) !== null);
              setMessage(error.payload?.message ?? "The request was rejected before generation started.");
            } else {
              setMessage("The result is uncertain. Do not resend. Reload the Page and check the saved status or recovery state.");
            }
          }
        } catch {
          setMarkerExists(true); setMessage("The result may be uncertain. Do not resend; check the saved Page status.");
        }
      });
    } catch { setMessage("The browser could not safely coordinate this action. No automatic retry was made."); }
    finally { setBusy(false); }
  }

  return <section aria-labelledby="panel-generation-heading">
    <h2 id="panel-generation-heading">Generate panels</h2>
    <p>Enter one rectangle for each saved panel in its displayed order. Coordinates use the 0–1,000,000 scale. No layout is inferred.</p>
    <form onSubmit={submit}>
      <label>Authorized by<input value={authorizedBy} maxLength={128} onChange={(event) => setAuthorizedBy(event.target.value)} required /></label>
      <label>Checkpoint name<input value={checkpointName} maxLength={128} onChange={(event) => setCheckpointName(event.target.value)} required /></label>
      {panels.map((panel, index) => <fieldset key={panel.number}>
        <legend>Panel {panel.number} of {panels.length}</legend>
        <p>{panel.narrative_intent}</p>
        {(["left", "top", "right", "bottom"] as const).map((edge) => <label key={edge}>{edge}
          <input inputMode="numeric" value={rectangles[index]?.[edge] ?? ""} required
            onChange={(event) => setRectangles((current) => current.map((rect, at) => at === index ? { ...rect, [edge]: event.target.value } : rect))} />
        </label>)}
      </fieldset>)}
      <button type="submit" disabled={!canSubmit}>{busy ? "Generation in progress…" : "Generate panels"}</button>
    </form>
    <p role="status" aria-live="polite">{message}</p>
    {markerExists ? <p>Previous request marker found. This browser cannot establish whether the Provider started; automatic resubmission is blocked.</p> : null}
  </section>;
}
