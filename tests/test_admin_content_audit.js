"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function node() {
  return {
    children: [],
    attributes: {},
    className: "",
    textContent: "",
    hidden: false,
    disabled: false,
    value: "",
    checked: false,
    append(...children) { this.children.push(...children); },
    prepend(...children) { this.children.unshift(...children); },
    appendChild(child) { this.children.push(child); return child; },
    replaceChildren(...children) { this.children = children; },
    setAttribute(name, value) { this.attributes[name] = value; },
    getAttribute(name) { return this.attributes[name]; },
    removeAttribute(name) { delete this.attributes[name]; },
    classList: {
      toggle(cls, force) {
        if (force === undefined) force = !this.contains(cls);
        if (force) this.add(cls); else this.remove(cls);
      },
      add(cls) { this.classes = this.classes || new Set(); this.classes.add(cls); },
      remove(cls) { if (this.classes) this.classes.delete(cls); },
      contains(cls) { return Boolean(this.classes && this.classes.has(cls)); },
    },
    addEventListener() {},
    showModal() {},
    close() {},
    focus() {},
    querySelectorAll() { return []; },
  };
}

const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, node());
    return elements.get(id);
  },
  createElement: node,
  createTextNode(text) { return { textContent: text }; },
};

const window = {
  addEventListener() {},
  location: { hash: "" },
};

const source = fs.readFileSync(path.join(__dirname, "../src/secure_gateway/admin/app.js"), "utf8");
const context = vm.createContext({
  document,
  window,
  globalThis: {},
  setInterval() {},
  clearInterval() {},
  setTimeout(fn) { fn(); },
  clearTimeout() {},
  URL: { createObjectURL() { return "blob:dummy"; }, revokeObjectURL() {} },
  fetch: async () => ({ ok: true, json: async () => ({}) }),
});

vm.runInContext(source, context);

const AuditUI = context.window.AuditUI;
assert.ok(AuditUI, "AuditUI should be exported on window");

// 1. Test formatCountdown
assert.equal(AuditUI.formatCountdown(600), "10:00");
assert.equal(AuditUI.formatCountdown(65), "01:05");
assert.equal(AuditUI.formatCountdown(9), "00:09");
assert.equal(AuditUI.formatCountdown(0), "00:00");
assert.equal(AuditUI.formatCountdown(-5), "00:00");
assert.equal(AuditUI.formatCountdown(null), "00:00");

// 2. Test determineAuditAction across all reasons

// 2.1 Content audit off
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-1", content_audit: "off" },
    null,
    { enabled: false, locked: false, paused: false }
  );
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "꺼짐");
}

// 2.2 Content audit paused
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-2", content_audit: "paused" },
    null,
    { enabled: true, locked: false, paused: true }
  );
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "일시 중지");
}

// 2.3 Excluded per request
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-3", content_audit: "excluded" },
    { request_id: "req-3", state: "제외", intent: "excluded", created: null },
    { enabled: true, locked: false, paused: false }
  );
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "제외");
}

// 2.4 Recorded before enabled
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-4", content_audit: null },
    { request_id: "req-4", state: "과거 기록 없음", intent: null, created: null },
    { enabled: true, locked: false, paused: false }
  );
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "과거 기록 없음");
}

// 2.5 Record failed
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-5", content_audit: "capture" },
    { request_id: "req-5", state: "기록 실패", intent: "capture", created: null },
    { enabled: true, locked: false, paused: false }
  );
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "기록 실패");
}

// 2.6 Expired or deleted
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-6", content_audit: "capture" },
    { request_id: "req-6", state: "삭제됨", intent: "capture", created: null },
    { enabled: true, locked: false, paused: false }
  );
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "삭제됨");
}

// 2.7 Store locked (when record exists but store is locked)
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-7", content_audit: "capture" },
    { request_id: "req-7", state: "완료", intent: "capture", created: 1700000000 },
    { enabled: true, locked: true, paused: false }
  );
  assert.equal(res.enabled, false);
  assert.equal(res.reason, "저장소 잠김");
}

// 2.8 Content audit holds data and store unlocked -> Enabled!
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-8", content_audit: "capture" },
    { request_id: "req-8", state: "완료", intent: "capture", created: 1700000000 },
    { enabled: true, locked: false, paused: false }
  );
  assert.equal(res.enabled, true);
  assert.equal(res.reason, null);
  assert.match(res.detail, /치환·복원 감사/);
}

// 2.9 Partial record with data -> Enabled!
{
  const res = AuditUI.determineAuditAction(
    { request_id: "req-9", content_audit: "capture" },
    { request_id: "req-9", state: "부분", intent: "capture", created: 1700000000 },
    { enabled: true, locked: false, paused: false }
  );
  assert.equal(res.enabled, true);
  assert.equal(res.reason, null);
}

// 3. Test memory wiping & clearAuditState
{
  assert.equal(AuditUI.hasDecryptedState(), false);
  AuditUI.clearAuditState();
  assert.equal(AuditUI.hasDecryptedState(), false);

  // Set passphrase input value
  const passEl = document.getElementById("audit-passphrase");
  passEl.value = "secret1234";
  AuditUI.clearAuditState();
  assert.equal(passEl.value, "", "Passphrase must be cleared on clearAuditState");
}

// 4. Test ComparisonView with content audit options and unrestored aliases
const compSource = fs.readFileSync(path.join(__dirname, "../src/secure_gateway/admin/comparison.js"), "utf8");
vm.runInContext(compSource, context);
const ComparisonView = context.window.ComparisonView;
assert.ok(ComparisonView, "ComparisonView should be exported on window");

// 4.1 Custom labels and normal spans
{
  const container = node();
  ComparisonView.render(container, {
    original: "이순신은 장군이다",
    masked: "고길동은 장군이다",
    spans: [
      { original_start: 0, original_end: 3, masked_start: 0, masked_end: 3, alias: "고길동", kind: "person" }
    ],
    uncertain: false,
    originalLabel: "로컬 복원 표시",
    maskedLabel: "모델 수신 마스킹",
  });
  assert.equal(container.children.length, 1);
  const diffBox = container.children[0];
  const split = diffBox.children[1]; // children[0] is toolbar, children[1] is split
  const origPane = split.children[0];
  const maskPane = split.children[1];
  const origHeaderH3 = origPane.children[0].children[0];
  const maskHeaderH3 = maskPane.children[0].children[0];
  assert.equal(origHeaderH3.textContent, "로컬 복원 표시");
  assert.equal(maskHeaderH3.textContent, "모델 수신 마스킹");
}

// 4.2 Unrestored aliases
{
  const container = node();
  ComparisonView.render(container, {
    original: "결과는 고길동입니다",
    masked: "결과는 고길동입니다",
    spans: [
      { original_start: 4, original_end: 7, masked_start: 4, masked_end: 7, alias: "고길동", unrestored: true }
    ],
    uncertain: false,
  });
  const diffBox = container.children[0];
  const split = diffBox.children[1];
  const origPre = split.children[0].children[1];
  const highlightedSpan = origPre.children[1];
  assert.equal(highlightedSpan.className, "diff-span diff-span-unrestored");
  assert.match(highlightedSpan.attributes["aria-label"], /미복원 별칭: 고길동/);
  const badge = highlightedSpan.children[0];
  assert.equal(badge.textContent, "[미복원]");
}

// 4.3 Uncertain notice
{
  const container = node();
  ComparisonView.render(container, {
    original: "원문 텍스트",
    masked: "마스킹 텍스트",
    spans: [],
    uncertain: true,
    uncertainNotice: "대응 관계를 확인할 수 없음 (비밀 패턴 제거됨)",
  });
  const diffBox = container.children[0];
  // With uncertain: true, children[0] is toolbar, children[1] is banner, children[2] is split
  const noticeBanner = diffBox.children[1];
  assert.equal(noticeBanner.className, "diff-uncertain-banner");
  assert.match(noticeBanner.textContent, /대응 관계를 확인할 수 없음 \(비밀 패턴 제거됨\)/);
}

console.log("Admin content audit UI tests passed cleanly (all 7 reasons & ComparisonView verified).");
