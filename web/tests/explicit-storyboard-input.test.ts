import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

import { isValidTrimmedText, parseCharacterIds, parseLineItems } from "../components/explicit-storyboard-input-form";

describe("explicit storyboard input form", () => {
  const source = readFileSync(new URL("../components/explicit-storyboard-input-form.tsx", import.meta.url), "utf8");

  it("requires explicit panel fields, bounded lists, and unique logical character IDs", () => {
    expect(source).toContain("function validPanels");
    expect(source).toContain("new Set(characters).size === characters.length");
    expect(source).toContain("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$");
    expect(source).toContain("Complete every field with a concrete value");
    expect(source).toContain("isValidTrimmedText(item, 512)");
    expect(source).toContain('value.startsWith("# Storyboard")');
    expect(source).toContain('value.startsWith("```")');
  });

  it("captures displayed source and does not retry after a submission attempt", () => {
    expect(source).toContain("freezeJson(JSON.parse(JSON.stringify");
    expect(source).toContain("sent.current = true");
    expect(source).toContain("setAttempted(true)");
    expect(source).toContain("Reload the Page and inspect its state");
    expect(source).toContain("This Page could not be found");
    expect(source).toContain("The confirmation was rejected");
    expect(source).toContain("Reload before trying again");
  });

  it("checks the one serialized request body before locking or posting and preserves oversized input", () => {
    const serialize = source.indexOf("serializeStoryboardConfirmationRequestBody(confirmationBody, expectedSourceJson)");
    const check = source.indexOf("isStoryboardConfirmationBodyWithinLimit(serializedBody)");
    const rejectMessage = source.indexOf("exceeds the 32 KiB request limit");
    const lock = source.indexOf("sent.current = true;");
    const post = source.indexOf("serializedBody);");

    expect(serialize).toBeGreaterThan(-1);
    expect(check).toBeGreaterThan(serialize);
    expect(rejectMessage).toBeGreaterThan(check);
    expect(lock).toBeGreaterThan(rejectMessage);
    expect(post).toBeGreaterThan(lock);
    expect(source).toContain("return;");
  });

  it("requires fresh confirmation after panel edits or panel-count changes", () => {
    expect(source).toContain("function update(index: number, key: keyof DraftPanel, value: string) {\n    setConfirmed(false);");
    expect(source).toContain("const count = Number(event.target.value);\n          setConfirmed(false);");
  });

  it("preserves commas in newline-separated fields and keeps character IDs comma-separated", () => {
    expect(parseLineItems("red scarf, visible in every panel\nmap, folded at the corner")).toEqual([
      "red scarf, visible in every panel",
      "map, folded at the corner"
    ]);
    expect(parseLineItems("Keep the note, even if hidden\r\nDo not crop the border")).toEqual([
      "Keep the note, even if hidden",
      "Do not crop the border"
    ]);
    expect(parseCharacterIds("courier, guard")).toEqual(["courier", "guard"]);
  });

  it("preserves line-item whitespace for validation and matches Python code-point length", () => {
    expect(parseLineItems(" Keep the scarf \n\tFold the map\t")).toEqual([
      " Keep the scarf ",
      "\tFold the map\t"
    ]);
    expect(isValidTrimmedText("Keep the scarf", 512)).toBe(true);
    expect(isValidTrimmedText(" Keep the scarf", 512)).toBe(false);
    expect(isValidTrimmedText("Keep the scarf ", 512)).toBe(false);
    expect(isValidTrimmedText("😀".repeat(512), 512)).toBe(true);
    expect(isValidTrimmedText("😀".repeat(513), 512)).toBe(false);
    expect(isValidTrimmedText("\u0085Keep the scarf", 512)).toBe(false);
    expect(isValidTrimmedText("\u001cKeep the scarf", 512)).toBe(false);
    expect(isValidTrimmedText("\uFEFFKeep the scarf", 512)).toBe(true);
  });
});
