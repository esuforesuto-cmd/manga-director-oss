import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("explicit storyboard input form", () => {
  const source = readFileSync(new URL("../components/explicit-storyboard-input-form.tsx", import.meta.url), "utf8");

  it("requires explicit panel fields, bounded lists, and unique logical character IDs", () => {
    expect(source).toContain("function validPanels");
    expect(source).toContain("new Set(characters).size === characters.length");
    expect(source).toContain("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$");
    expect(source).toContain("Complete every field with a concrete value");
    expect(source).toContain("Boolean(item)");
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

  it("requires fresh confirmation after panel edits or panel-count changes", () => {
    expect(source).toContain("function update(index: number, key: keyof DraftPanel, value: string) {\n    setConfirmed(false);");
    expect(source).toContain("const count = Number(event.target.value);\n          setConfirmed(false);");
  });
});
