import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");

test("includes each product workflow", () => {
  for (const expected of [
    "Customer profiles",
    "Transaction imports",
    "Run segmentation",
    "Create campaign audience",
    "Expected columns",
  ]) {
    assert.match(page, new RegExp(expected));
  }
  for (const endpoint of [
    "/health/live",
    "/api/v1/segments/summary",
    "/api/v1/customers?limit=200",
    "/api/v1/segments/run",
    "/api/v1/transactions/batch",
  ]) {
    assert.match(page, new RegExp(endpoint.replace(/[?]/g, "\\?")));
  }
});

test("includes responsive and reduced-motion styles", () => {
  assert.match(css, /@media\(max-width:760px\)/);
  assert.match(css, /@media\(max-width:480px\)/);
  assert.match(css, /prefers-reduced-motion:reduce/);
});
