const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const elements = new Map();
let filters = [["since", "10000-01-01T00:00"]], requests = 0;
const document = {hidden: false, getElementById(id) {
  if (!elements.has(id)) elements.set(id, {events: {}, value: "", textContent: "", hidden: false,
    addEventListener(event, fn) { this.events[event] = fn; }, replaceChildren() {}, close() {}, focus() {}});
  return elements.get(id);
}};
const context = vm.createContext({document, Date, Number, URLSearchParams,
  FormData: class { [Symbol.iterator]() { return filters[Symbol.iterator](); } },
  fetch: async () => { requests++; return {ok: false, status: 400}; }, setInterval() {}, setTimeout(fn) { fn(); }
});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/secure_gateway/admin/app.js"), "utf8"), context);
async function run() {
  vm.runInContext('token = "fixture";', context);
  assert.equal(await vm.runInContext("load()", context), false);
  assert.equal(vm.runInContext("loading", context), false);
  assert.equal(requests, 0);
  assert.match(elements.get("banner").textContent, /Dates/);
  filters = [["since", "2026-01-01T00:00"]];
  await vm.runInContext("load()", context);
  assert.equal(requests, 1);
  elements.get("logout").events.click();
  elements.get("token").value = "new-token";
  await elements.get("login-form").events.submit({preventDefault() {}});
  assert.equal(requests, 2);
  assert.equal(vm.runInContext("loading", context), false);
  assert.throws(() => vm.runInContext('filterDate("0000-01-01T00:00")', context));
}
run().catch(error => { console.error(error); process.exitCode = 1; });
