import assert from "node:assert/strict";
import test from "node:test";

async function renderHome() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("renders the branded analytics dashboard", async () => {
  const response = await renderHome();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>CustomWear Analytics Dashboard<\/title>/);
  assert.match(html, /Good morning, Anthony/);
  assert.match(html, /Customer segments/);
  assert.match(html, /Run segmentation/);
  assert.match(html, /property="og:image"/);
  assert.match(html, /Customer intelligence for modern apparel brands/);
  assert.doesNotMatch(html, /Starter Project|codex-preview/);
});

test("renders accessible dashboard landmarks", async () => {
  const html = await (await renderHome()).text();
  assert.match(html, /aria-label="Dashboard navigation"/);
  assert.match(html, /aria-label="Key performance indicators"/);
  assert.match(html, /aria-label="Weekly revenue trend"/);
  assert.match(html, /aria-label="Notifications"/);
});
