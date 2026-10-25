const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function node() {
  return {
    children: [],
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    addEventListener() {},
  };
}

const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, node());
    return elements.get(id);
  },
  createElement: node,
  createTextNode(text) { return {textContent: text}; },
};
const source = fs.readFileSync(path.join(__dirname, "../src/secure_gateway/admin/app.js"), "utf8");
const context = vm.createContext({document, setInterval() {}});
vm.runInContext(source, context);

const rows = [302, 200, 404, null, 101].map((status) => ({
  status, started_at: "2026-01-01T00:00:00Z", agent: "Codex", provider: "codex",
  subscription: "chatgpt_subscription", outcome: "completed", duration_ms: 1,
}));
context.data = {
  rows, summary: {total: 5, success: 1, errors: 1, average_ms: 1, forwarded: 0},
  routes: [], offset: 0, audit_write_errors: 0,
};
vm.runInContext("render(data)", context);
const results = elements.get("rows").children.map((tr) => tr.children[4].children[0]);
assert.deepEqual(results.map((span) => [span.textContent, span.className]), [
  ["302 리디렉션", "status redirect"],
  ["200 성공", "status success"],
  ["404 실패", "status error"],
  ["미완료", "status pending"],
  ["101 기타", "status other"],
]);
assert.equal(elements.get("stat-success").textContent, "1");
