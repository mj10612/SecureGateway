const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function node() {
  return {children: [], append(...children) {this.children.push(...children);},
    replaceChildren(...children) {this.children = children;}, addEventListener() {}};
}
const elements = new Map();
const document = {getElementById(id) {
  if (!elements.has(id)) elements.set(id, node());
  return elements.get(id);
}, createElement: node, createTextNode(text) {return {textContent: text};}};
const context = vm.createContext({document, setInterval() {}});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../src/secure_gateway/admin/app.js"), "utf8"), context);

function render(errors, retries = {}, legacy = 0) {
  context.data = {rows: [], routes: [], offset: 0,
    summary: {total: 0, success: 0, errors: 0, average_ms: 0, forwarded: 0},
    audit_write_errors: legacy, audit_error_counts: errors, audit_completion_retries: retries};
  vm.runInContext("render(data)", context);
  return elements.get("banner");
}
let banner = render({admission: 0, completion: 0, maintenance: 1}, {maintenance_errors: 1}, 1);
assert.equal(banner.hidden, false);
assert.match(banner.textContent, /보존 정리 지연 1건/);
assert.doesNotMatch(banner.textContent, /로그 저장 오류|미완료|차단/);

banner = render({admission: 2, completion: 0, maintenance: 0}, {}, 2);
assert.match(banner.textContent, /요청 시작 기록 실패 2건/);
assert.match(banner.textContent, /전송 전에 차단/);

banner = render({admission: 0, completion: 1, maintenance: 0}, {pending: 3, recovered: 2, dropped: 1}, 1);
assert.match(banner.textContent, /완료 기록 실패 1건/);
assert.match(banner.textContent, /재시도 대기 3건/);
assert.match(banner.textContent, /누적 복구 2건/);
assert.match(banner.textContent, /포기 1건/);

// Background maintenance is not part of the legacy counter: never subtract it.
banner = render({admission: 1, completion: 1, maintenance: 1}, {maintenance_errors: 4}, 3);
assert.match(banner.textContent, /요청 시작 기록 실패/);
assert.match(banner.textContent, /완료 기록 실패/);
assert.match(banner.textContent, /보존 정리 지연 4건/);

banner = render(undefined, {}, 2);
assert.match(banner.textContent, /로그 저장 오류 2건/);
assert.equal(render({admission: 0, completion: 0, maintenance: 0}).hidden, true);
