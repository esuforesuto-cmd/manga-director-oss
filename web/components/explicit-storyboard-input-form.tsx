"use client";

import { useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, api } from "@/lib/api/client";
import type { PageDetail, StoryboardConfirmationPanel } from "@/lib/api/types";

type DraftPanel = Omit<StoryboardConfirmationPanel, "characters" | "continuity_bindings" | "constraints"> & {
  characters: string;
  continuity_bindings: string;
  constraints: string;
};

function emptyPanel(number: number): DraftPanel {
  return { number, narrative_intent: "", characters: "", continuity_bindings: "", action: "", background: "", composition: "", constraints: "" };
}

export function parseCharacterIds(value: string): string[] {
  return value.split(",").map((item) => item.trim());
}

export function parseLineItems(value: string): string[] {
  return value.split(/\r?\n/).map((item) => item.trim());
}

function freezeJson<T>(value: T): T {
  if (value && typeof value === "object") {
    Object.values(value as Record<string, unknown>).forEach(freezeJson);
    Object.freeze(value);
  }
  return value;
}

function validPanels(panels: DraftPanel[]): boolean {
  const abstract = new Set(["advance the page purpose", "character", "continue", "continuity", "protagonist", "same as above", "tbd"]);
  return panels.length >= 1 && panels.length <= 16 && panels.every((panel, index) => {
    if (panel.number !== index + 1) return false;
    if ([panel.narrative_intent, panel.action, panel.background, panel.composition].some((value) =>
      !value || value !== value.trim() || value.length > 4000 || abstract.has(value.toLowerCase())
        || value.startsWith("# Storyboard") || value.startsWith("```")
    )) return false;
    const characters = parseCharacterIds(panel.characters);
    const continuity = parseLineItems(panel.continuity_bindings);
    const constraints = parseLineItems(panel.constraints);
    const boundedList = (items: string[], max: number) => items.length >= 1 && items.length <= max
      && items.every((item) => Boolean(item) && item.length <= 512 && !abstract.has(item.toLowerCase()));
    return boundedList(characters, 32)
      && characters.every((id) => /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(id))
      && new Set(characters).size === characters.length
      && boundedList(continuity, 32)
      && boundedList(constraints, 64);
  });
}

export function ExplicitStoryboardInputForm({
  projectId,
  page,
  pageDesign,
  review,
  expectedSourceJson
}: Readonly<{
  projectId: string;
  page: PageDetail;
  pageDesign: Record<string, unknown>;
  review: Record<string, unknown>;
  expectedSourceJson?: string;
}>) {
  const router = useRouter();
  const [panels, setPanels] = useState<DraftPanel[]>([emptyPanel(1)]);
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const sent = useRef(false);
  const [message, setMessage] = useState("");
  const panelsValid = validPanels(panels);
  const expectedSource = useMemo(() => freezeJson(JSON.parse(JSON.stringify({
    state: "Reviewed", page_design: pageDesign, review
  }))) as { state: "Reviewed"; page_design: Record<string, unknown>; review: Record<string, unknown> }, [pageDesign, review]);

  function update(index: number, key: keyof DraftPanel, value: string) {
    setConfirmed(false);
    setPanels((current) => current.map((panel, position) => position === index ? { ...panel, [key]: value } : panel));
  }

  async function submit() {
    if (sent.current || submitting || !confirmed || !panelsValid) return;
    sent.current = true;
    setAttempted(true);
    setSubmitting(true);
    setMessage("");
    const explicitPanels = panels.map((panel) => ({
      ...panel,
      characters: parseCharacterIds(panel.characters),
      continuity_bindings: parseLineItems(panel.continuity_bindings),
      constraints: parseLineItems(panel.constraints)
    }));
    try {
      await api.pages.confirmStoryboard(projectId, page.pageNumber, {
        requestVersion: 1,
        expectedSource,
        confirmed: true,
        panels: explicitPanels
      }, expectedSourceJson);
      setMessage("Storyboard saved. Reload the page to inspect the result.");
      router.refresh();
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 409) {
        setMessage("The Page source changed. Reload it, review the current source, and confirm again deliberately.");
      } else if (error instanceof ApiClientError && error.status === 404) {
        setMessage("This Page could not be found. Reload the project and inspect its current state.");
      } else if (error instanceof ApiClientError && error.status === 422) {
        setMessage("The confirmation was rejected. Reload the Page, review the current source and input, then confirm again deliberately.");
      } else {
        setMessage("The result may be uncertain. Reload the Page and inspect its state before taking another action.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section aria-labelledby="explicit-storyboard-heading">
      <h2 id="explicit-storyboard-heading">Confirm storyboard input</h2>
      <p>Enter every panel detail yourself. These fields are saved exactly as entered after validation.</p>
      <details>
        <summary>Reviewed source captured for this confirmation</summary>
        <h3>Page design</h3><pre>{JSON.stringify(pageDesign, null, 2)}</pre>
        <h3>Review</h3><pre>{JSON.stringify(review, null, 2)}</pre>
        {expectedSourceJson ? <><h3>Exact captured source JSON</h3><pre>{expectedSourceJson}</pre></> : null}
      </details>
      <label>Panel count
        <select aria-label="Panel count" value={panels.length} disabled={submitting} onChange={(event) => {
          const count = Number(event.target.value);
          setConfirmed(false);
          setPanels((current) => Array.from({ length: count }, (_, index) => current[index] ?? emptyPanel(index + 1)).map((panel, index) => ({ ...panel, number: index + 1 })));
        }}>
          {Array.from({ length: 16 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}
        </select>
      </label>
      {panels.map((panel, index) => <fieldset key={panel.number}>
        <legend>Panel {panel.number}</legend>
        <label>Narrative intent<input value={panel.narrative_intent} disabled={submitting} onChange={(event) => update(index, "narrative_intent", event.target.value)} /></label>
        <label>Character IDs, comma separated<input value={panel.characters} disabled={submitting} onChange={(event) => update(index, "characters", event.target.value)} /></label>
        <label>Continuity bindings, one per line<textarea rows={3} value={panel.continuity_bindings} disabled={submitting} onChange={(event) => update(index, "continuity_bindings", event.target.value)} /></label>
        <label>Action<input value={panel.action} disabled={submitting} onChange={(event) => update(index, "action", event.target.value)} /></label>
        <label>Background<input value={panel.background} disabled={submitting} onChange={(event) => update(index, "background", event.target.value)} /></label>
        <label>Composition<input value={panel.composition} disabled={submitting} onChange={(event) => update(index, "composition", event.target.value)} /></label>
        <label>Constraints, one per line<textarea rows={3} value={panel.constraints} disabled={submitting} onChange={(event) => update(index, "constraints", event.target.value)} /></label>
      </fieldset>)}
      <label><input type="checkbox" checked={confirmed} disabled={submitting} onChange={(event) => setConfirmed(event.target.checked)} /> I reviewed these exact panel details and confirm them.</label>
      {!panelsValid ? <p role="alert">Complete every field with a concrete value. Use unique comma-separated character IDs, and enter continuity bindings and constraints one per line.</p> : null}
      <button type="button" disabled={submitting || attempted || !confirmed || !panelsValid} onClick={submit}>{submitting ? "Saving…" : attempted ? "Reload before trying again" : "Confirm storyboard"}</button>
      {message ? <p role="status">{message}</p> : null}
    </section>
  );
}
