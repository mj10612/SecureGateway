const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../src/secure_gateway/admin/app.js"), "utf8");
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
function setup() {
  const elements = new Map(), requests = [], downloads = [], urls = [];
  let filters = [["since", "2026-01-01T00:00"], ["until", "2026-01-02T00:00"], ["provider", "codex"]];
  function node(tag) {
    return {tag, events: {}, textContent: "", hidden: false,
      addEventListener(name, fn) { this.events[name] = fn; },
      replaceChildren() {}, append() {}, close() {}, focus() {},
      click() { downloads.push(this.download); },
    };
  }
  const document = {hidden: false, getElementById(id) {
    if (!elements.has(id)) elements.set(id, node(id)); return elements.get(id);
  }, createElement: node};
  const context = vm.createContext({document, URLSearchParams, Date, JSON,
    FormData: class { [Symbol.iterator]() { return filters[Symbol.iterator](); } },
    URL: {createObjectURL(blob) { urls.push(blob); return "blob:fixture"; }, revokeObjectURL() {}},
    setTimeout(fn) { fn(); }, setInterval() {},
    fetch(url, options) { const pending = deferred(); requests.push({url, options, ...pending}); return pending.promise; },
  });
  vm.runInContext(source, context);
  document.getElementById("banner");
  vm.runInContext('token = "synthetic"; load = async () => false;', context);
  const click = id => elements.get(id).events.click();
  const response = (data) => ({ok: true, blob: async () => new Blob([JSON.stringify(data)])});
  return {elements, context, requests, downloads, urls, click, response,
    filterChange() { filters = [["since", "2026-01-01T00:00"], ["until", "2026-01-02T00:00"], ["provider", "claude"]]; elements.get("filters").events.change(); }};
}
const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };

async function staleExport(stage, relogin = false, fail = false) {
  const h = setup(), body = deferred(), text = deferred();
  const pending = h.click("export");
  if (stage !== "fetch") {
    h.requests[0].resolve({ok: true, blob: () => body.promise}); await tick();
  }
  if (stage === "text") {
    body.resolve({text: () => text.promise}); await tick();
  }
  h.click("logout");
  if (relogin) {
    h.elements.get("token").value = "new-token";
    await h.elements.get("login-form").events.submit({preventDefault() {}});
  }
  h.elements.get("banner").textContent = "new-state";
  h.elements.get("banner").hidden = true;
  if (stage === "fetch") {
    if (fail) h.requests[0].reject(new Error("old failure"));
    else h.requests[0].resolve(h.response({count: 1, next_cursor: null}));
  } else if (stage === "blob") {
    if (fail) body.reject(new Error("old blob failure"));
    else body.resolve(new Blob(['{"count":1}']));
  } else if (fail) text.reject(new Error("old text failure"));
  else text.resolve('{"count":1}');
  await pending;
  assert.equal(h.downloads.length, 0);
  assert.equal(h.urls.length, 0);
  assert.equal(h.elements.get("banner").textContent, "new-state");
  assert.equal(h.elements.get("banner").hidden, true);
}

async function run() {
  for (const stage of ["fetch", "blob", "text"]) {
    await staleExport(stage); await staleExport(stage, true);
    await staleExport(stage, false, true);
  }
  const h = setup();
  const first = h.click("export");
  h.click("export"); assert.equal(h.requests.length, 1);
  h.requests[0].resolve(h.response({count: 1000, next_cursor: "signed-cursor"})); await first;
  assert.equal(h.elements.get("export-next").disabled, false);
  assert.match(h.elements.get("export-status").textContent, /1000|1,000/);
  const second = h.click("export-next");
  const params = new URLSearchParams(h.requests[1].url.split("?")[1]);
  assert.equal(params.get("cursor"), "signed-cursor"); assert.equal(params.get("provider"), "codex");
  h.requests[1].resolve(h.response({count: 1, next_cursor: null})); await second;
  assert.equal(h.elements.get("export-next").disabled, true);
  assert.deepEqual(h.downloads, ["secure-gateway-audit-1.json", "secure-gateway-audit-2.json"]);
  const pending = h.click("export");
  h.filterChange();
  h.requests[2].resolve(h.response({count: 1, next_cursor: "stale"})); await pending;
  assert.equal(h.downloads.length, 2); assert.equal(h.elements.get("export-next").disabled, true);
  const changed = h.click("export");
  assert.equal(new URLSearchParams(h.requests[3].url.split("?")[1]).get("provider"), "claude");
  h.requests[3].resolve(h.response({count: 0, next_cursor: null})); await changed;
  console.log("Dashboard export generation and bounded continuation passed");
}
run().catch(error => { console.error(error); process.exitCode = 1; });
