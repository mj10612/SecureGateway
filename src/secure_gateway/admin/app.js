"use strict";
const $ = (id) => document.getElementById(id);
const providers = {claude: "Anthropic", codex: "OpenAI", xai: "xAI"};
const subscriptions = {claude_subscription: "Claude 구독", chatgpt_subscription: "ChatGPT 구독", api_key: "xAI API 키"};
const outcomes = {blocked: "전송 전 차단", completed: "완료", upstream_rejected: "제공자 거절", transport_error: "연결 오류", restore_error: "복원 오류", incomplete: "진행 중 / 미완료", interrupted: "프로세스 중단"};
let token = "", offset = 0, generation = 0, loading = false, pending = false, auditWriteErrors = 0;
let auditErrorCounts = null, completionRetries = {};
const limit = 50;
let exportEpoch = 0, exportCursor = "", exportFilters = null, exportNumber = 0, exporting = false;
let contentAuditStatus = null;
const contentAuditRequestsMap = new Map();
let activeAuditRequestId = null;
let activeAuditData = null;
let auditAutoLockTimer = null;
let auditCountdownSeconds = 0;
const AUDIT_INACTIVITY_TIMEOUT_SEC = 600;

function formatCountdown(seconds) {
  if (seconds == null || seconds < 0) return "00:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function determineAuditAction(row, auditEntry, auditStatus) {
  if (auditStatus && !auditStatus.enabled) {
    return { enabled: false, reason: "꺼짐", detail: "내용 감사가 비활성화되어 있습니다." };
  }
  if (auditStatus && auditStatus.paused) {
    return { enabled: false, reason: "일시 중지", detail: "내용 감사가 일시 중지된 상태입니다." };
  }

  const intent = auditEntry?.intent ?? row?.content_audit;
  const state = auditEntry?.state;

  if (state === "제외" || intent === "excluded") {
    return { enabled: false, reason: "제외", detail: "내용 감사 대상에서 제외된 요청입니다." };
  }
  if (state === "꺼짐" || intent === "off") {
    return { enabled: false, reason: "꺼짐", detail: "내용 감사가 꺼진 상태에서 처리된 요청입니다." };
  }
  if (state === "일시 중지" || intent === "paused") {
    return { enabled: false, reason: "일시 중지", detail: "내용 감사가 일시 중지된 상태에서 처리된 요청입니다." };
  }
  if (state === "삭제됨" || state === "만료됨") {
    return { enabled: false, reason: "삭제됨", detail: "보존 기간 만료 또는 관리자에 의해 삭제된 기록입니다." };
  }
  if (state === "과거 기록 없음" || (!auditEntry && !intent)) {
    return { enabled: false, reason: "과거 기록 없음", detail: "내용 감사 활성화 이전에 처리되었거나 기록이 없습니다." };
  }
  if (state === "기록 실패" || (!auditEntry?.created && intent === "capture")) {
    return { enabled: false, reason: "기록 실패", detail: "내용 감사 기록 중 오류가 발생하여 저장되지 않았습니다." };
  }

  if (auditStatus && auditStatus.locked) {
    return { enabled: false, reason: "저장소 잠김", detail: "내용 감사 저장소가 잠겨 있습니다. 잠금 해제 후 확인하세요." };
  }

  if (auditEntry?.created || (auditEntry && ["완료", "부분", "전송 여부 불확실"].includes(state))) {
    return { enabled: true, reason: null, detail: "치환·복원 감사 내역을 조회합니다." };
  }

  return { enabled: false, reason: "과거 기록 없음", detail: "내용 감사 기록을 찾을 수 없습니다." };
}
function resetExport() {
  exportEpoch++; exportCursor = ""; exportFilters = null; exportNumber = 0; exporting = false;
  $("export").disabled = false; $("export-next").disabled = true;
  $("export-status").textContent = "";
}
const num = (v) => Number(v || 0).toLocaleString("ko-KR");
const time = (v) => new Date(v).toLocaleString("ko-KR", {hour12: false});
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function detail(row) {
  const fields = {
    "요청 ID": row.request_id, "처리 일시": time(row.started_at), "에이전트": row.agent,
    "제공자": providers[row.provider] || row.provider, "구독 / 인증": subscriptions[row.subscription],
    "계정 ID": row.account_ref || "제공되지 않음", "자격 증명 ID": row.credential_ref || "없음",
    "구독 요금제": "확인 불가", "요청 모델": row.model || "미제공", "요청 경로": row.endpoint,
    "전송 목적지": row.destination || "비활성", "업스트림 전송 시도": row.upstream_attempted ? "있음" : "없음",
    "처리 결과": outcomes[row.outcome] || row.outcome, "HTTP 상태": row.status ?? "미완료",
    "소요 시간": row.duration_ms == null ? "미완료" : `${num(row.duration_ms)} ms`,
    "수신 요청 크기": `${num(row.input_bytes)} bytes`, "마스킹 요청 크기": `${num(row.masked_bytes)} bytes`,
    "로컬 응답 크기": `${num(row.output_bytes)} bytes`, "새로 생성한 별칭": num(row.new_aliases),
  };
  $("detail-fields").replaceChildren(...Object.entries(fields).flatMap(([key, value]) => [element("dt", key), element("dd", String(value))]));
  $("details").showModal();
  if (row.credential_ref) {
    const filterButton = element("button", "이 자격 증명의 요청 보기", "secondary");
    filterButton.addEventListener("click", () => {
      $("filters").elements.namedItem("credential_ref").value = row.credential_ref;
      offset = 0; resetExport(); $("details").close(); load();
    });
    const action = element("dd"); action.append(filterButton);
    $("detail-fields").append(element("dt", "요청 필터"), action);
  }
}
function restoreAuditWarning() {
  const messages = [];
  if (auditErrorCounts) {
    if (auditErrorCounts.admission) messages.push(`요청 시작 기록 실패 ${num(auditErrorCounts.admission)}건: 해당 요청은 전송 전에 차단됐습니다.`);
    if (auditErrorCounts.completion) messages.push(`완료 기록 실패 ${num(auditErrorCounts.completion)}건: 현재 재시도 대기 ${num(completionRetries.pending)}건, 누적 복구 ${num(completionRetries.recovered)}건, 포기 ${num(completionRetries.dropped)}건입니다.`);
  } else if (auditWriteErrors) {
    messages.push(`로그 저장 오류 ${num(auditWriteErrors)}건이 발생했습니다. 일부 요청은 미완료로 남거나 전송 전에 차단됐을 수 있습니다.`);
  }
  const maintenance = Math.max(Number(auditErrorCounts?.maintenance || 0), Number(completionRetries.maintenance_errors || 0));
  if (maintenance) messages.push(`보존 정리 지연 ${num(maintenance)}건: 완료 기록 저장 실패와 구분되는 유지보수 경고입니다. 다음 요청 처리에서 정리를 다시 시도합니다.`);
  $("banner").hidden = messages.length === 0;
  $("banner").textContent = messages.join(" ");
}
function render(data) {
  const policy = data.retention || {max_records: 100000, max_age_days: null};
  $("stat-total").textContent = num(data.summary.total);
  $("stat-success").textContent = num(data.summary.success);
  $("stat-errors").textContent = num(data.summary.errors);
  $("stat-latency").replaceChildren(document.createTextNode(num(Math.round(data.summary.average_ms)) + " "), element("em", "ms"));
  $("forwarded").textContent = `전송 시도 ${num(data.summary.forwarded)}건`;
  $("routes").replaceChildren(...data.routes.map((route) => {
    const node = element("div", undefined, "route-item"), info = element("div");
    info.append(element("strong", providers[route.provider] || route.provider), element("small", route.mode === "subscription" ? "기존 구독 OAuth" : "명시적 API 키"));
    node.append(element("span", (providers[route.provider] || route.provider)[0], "provider-icon"), info);
    return node;
  }));
  $("rows").replaceChildren(...data.rows.map((row) => {
    const tr = element("tr"), date = element("td", time(row.started_at));
    const agent = element("td", row.agent); agent.append(element("small", row.model || "모델 미제공"));
    const route = element("td", providers[row.provider] || row.provider); route.append(element("small", subscriptions[row.subscription]));
    const account = element("td"); account.append(element("code", row.account_ref || "계정 미제공"));
    const result = element("td");
    const kind = row.status == null ? "pending" : row.status >= 200 && row.status < 300 ? "success" : row.status >= 300 && row.status < 400 ? "redirect" : row.status >= 400 ? "error" : "other";
    const labels = {pending: "미완료", success: "성공", redirect: "리디렉션", error: "실패", other: "기타"};
    result.append(element("span", row.status == null ? labels.pending : `${row.status} ${labels[kind]}`, `status ${kind}`), element("small", outcomes[row.outcome] || row.outcome));
    const latency = element("td", row.duration_ms == null ? "—" : `${num(Math.round(row.duration_ms))} ms`);
    const action = element("td"), button = element("button", "상세 ↗", "quiet detail-button");
    button.addEventListener("click", () => detail(row)); action.append(button);
    const auditAction = determineAuditAction(row, contentAuditRequestsMap.get(row.request_id), contentAuditStatus);
    const auditBtn = element("button", undefined, "quiet audit-action-btn");
    if (auditAction.enabled) {
      auditBtn.textContent = "치환·복원 감사";
      auditBtn.title = auditAction.detail;
      auditBtn.addEventListener("click", () => openAuditForRequest(row.request_id));
    } else {
      auditBtn.disabled = true;
      auditBtn.textContent = `치환·복원 불가 (${auditAction.reason})`;
      auditBtn.title = auditAction.detail;
    }
    action.append(document.createTextNode(" "), auditBtn);
    tr.append(date, agent, route, account, result, latency, action); return tr;
  }));
  $("empty").hidden = data.rows.length !== 0;
  $("page-info").textContent = data.rows.length ? `${num(data.offset + 1)}–${num(data.offset + data.rows.length)} / ${num(data.summary.total)}건` : `${num(data.summary.total)}건 · 현재 페이지에 내역 없음`;
  $("previous").disabled = data.offset === 0;
  $("next").disabled = data.offset + limit >= data.summary.total;
  $("updated").textContent = `마지막 갱신 ${new Date().toLocaleTimeString("ko-KR", {hour12: false})} · 최근 ${num(policy.max_records)}건`;
  $("updated").textContent += policy.max_age_days == null ? " | age: unlimited" : ` | age: ${num(policy.max_age_days)} days`;
  auditWriteErrors = Number(data.audit_write_errors || 0);
  auditErrorCounts = data.audit_error_counts || null;
  completionRetries = data.audit_completion_retries || {};
  restoreAuditWarning();
}
function filterDate(value) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime()) || date.getUTCFullYear() < 1 || date.getUTCFullYear() > 9999) {
    throw new Error("Dates must be valid and within years 0001 through 9999.");
  }
  return date.toISOString();
}
async function load() {
  if (!token) return false;
  if (loading) { pending = true; return false; }
  loading = true;
  const current = generation, params = new URLSearchParams({limit, offset});
  try {
    for (const [key, value] of new FormData($("filters"))) {
      if (value) params.set(key, key === "since" || key === "until" ? filterDate(value) : value);
    }
    const response = await fetch(`/admin/api/logs?${params}`, {headers: {"X-SecureGateway-Token": token}, cache: "no-store"});
    if (current !== generation) return false;
    if (!response.ok) throw new Error(response.status === 401 ? "인증 토큰을 확인하세요." : response.status === 400 ? "필터 조건을 확인하세요." : "게이트웨이 또는 로그 저장소에 연결할 수 없습니다.");
    const data = await response.json();
    if (current !== generation) return false;
    try { await fetchAuditOverview(); } catch (_) {}
    if (current !== generation) return false;
    render(data);
    $("token").value = ""; $("login-error").textContent = "";
    $("login").hidden = true; $("dashboard").hidden = false;
    return true;
  } catch (error) {
    if (current !== generation) return false;
    $("login-error").textContent = error.message;
    $("banner").textContent = `${error.message} 표시된 내역은 마지막 갱신 결과입니다.`;
    $("banner").hidden = false; return false;
  } finally { loading = false; if (pending) { pending = false; setTimeout(load, 0); } }
}
$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault(); generation++; resetExport(); token = $("token").value.trim();
  if (await load()) { $("token").value = ""; $("login-error").textContent = ""; $("login").hidden = true; $("dashboard").hidden = false; await loadRules(); await loadDomainPolicy(); }
});
$("logout").addEventListener("click", () => {
  token = ""; generation++; resetExport(); offset = 0; $("rows").replaceChildren(); $("detail-fields").replaceChildren();
  $("mask-rules").value = ""; $("mask-rules-status").textContent = "";
  clearPreviewState();
  clearAuditState();
  stopAutoLockTimer();
  $("details").close(); $("dashboard").hidden = true; $("login").hidden = false; $("token").focus();
});
$("refresh").addEventListener("click", load);
async function loadRules() {
  const current = generation;
  try {
    const response = await fetch("/admin/api/mask-rules", {headers: {"X-SecureGateway-Token": token}, cache: "no-store"});
    if (!response.ok) throw new Error();
    const data = await response.json();
    if (current === generation) $("mask-rules").value = data.rules.join("\n");
  } catch (_) { if (current === generation) $("mask-rules-status").textContent = "규칙을 불러오지 못했습니다."; }
}
$("mask-rules-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const current = generation;
  const rules = $("mask-rules").value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  try {
    const response = await fetch("/admin/api/mask-rules", {method: "POST", headers: {"Content-Type": "application/json", "X-SecureGateway-Token": token}, body: JSON.stringify({rules}), cache: "no-store"});
    if (!response.ok) throw new Error();
    const data = await response.json();
    if (current === generation) { $("mask-rules").value = data.rules.join("\n"); $("mask-rules-status").textContent = "저장했습니다."; }
  } catch (_) { if (current === generation) $("mask-rules-status").textContent = "저장하지 못했습니다. 진행 중인 요청을 끝내고 규칙을 확인하세요."; }
});
async function exportLogs(next = false) {
  if (!token || exporting || (next && !exportCursor)) return;
  if (!next) resetExport();
  const current = generation, epoch = exportEpoch;
  const isCurrent = () => current === generation && epoch === exportEpoch;
  const params = next ? new URLSearchParams(exportFilters) : new URLSearchParams();
  exporting = true; $("export").disabled = true; $("export-next").disabled = true;
  try {
    if (!next) {
      for (const [key, value] of new FormData($("filters"))) {
        if (value) params.set(key, key === "since" || key === "until" ? filterDate(value) : value);
      }
    }
    if (!params.has("since") || !params.has("until")) throw new Error("시작·종료 일시를 모두 선택하세요.");
    if (next) params.set("cursor", exportCursor);
    const response = await fetch(`/admin/api/logs/export?${params}`, {headers: {"X-SecureGateway-Token": token}, cache: "no-store"});
    if (!isCurrent()) return;
    if (!response.ok) throw new Error(response.status === 400 ? "기간·필터 또는 페이지가 유효하지 않습니다. 내보내기를 다시 시작하세요." : "내보내기에 실패했습니다.");
    const blob = await response.blob();
    if (!isCurrent()) return;
    const data = JSON.parse(await blob.text());
    if (!isCurrent()) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a"); link.href = url; link.download = `secure-gateway-audit-${exportNumber + 1}.json`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 0);
    exportNumber++; exportCursor = data.next_cursor || "";
    params.delete("cursor"); exportFilters = params.toString();
    $("export-status").textContent = `파일 ${exportNumber} · ${num(data.count)}건 · ${exportCursor ? "다음 파일 있음" : "완료"}`;
    restoreAuditWarning();
  } catch (error) {
    if (!isCurrent()) return;
    $("banner").textContent = error.message; $("banner").hidden = false;
  } finally {
    if (isCurrent()) {
      exporting = false; $("export").disabled = false; $("export-next").disabled = !exportCursor;
    }
  }
}
$("export").addEventListener("click", () => exportLogs());
$("export-next").addEventListener("click", () => exportLogs(true));
$("filters").addEventListener("submit", (event) => event.preventDefault());
$("filters").addEventListener("change", () => { offset = 0; resetExport(); load(); });
$("filters").addEventListener("reset", () => { offset = 0; resetExport(); setTimeout(load, 0); });
$("previous").addEventListener("click", () => { offset = Math.max(0, offset - limit); load(); });
$("next").addEventListener("click", () => { offset += limit; load(); });
let domainOffset = 0;
const domainNames = {defense: "방산", automotive: "자동차", semiconductor: "반도체"};
async function domainRequest(path, options = {}) {
  const response = await fetch(path, {...options, headers: {"Content-Type": "application/json", "X-SecureGateway-Token": token}, cache: "no-store"});
  if (!response.ok) throw new Error("분야 사전 요청에 실패했습니다. 진행 중인 요청과 저장 상태를 확인하세요.");
  return response.json();
}
function renderDomainPolicy(data) {
  $("domain-toggles").replaceChildren(...data.domains.map((domain) => {
    const label = element("label"), input = element("input");
    input.type = "checkbox"; input.name = domain.id; input.checked = data.enabled[domain.id];
    label.append(input, document.createTextNode(`${domainNames[domain.id]} · v${domain.version} · 활성 보호 ${domain.active_concepts}개 / 전체 항목 ${domain.concept_count}개`));
    return label;
  }));
}
async function loadDomainPolicy() {
  const current = generation;
  try {
    const data = await domainRequest("/admin/api/domain-policy");
    if (current !== generation) return;
    renderDomainPolicy(data);
    $("domain-policy-status").textContent = "현재 적용 정책: " + data.policy_version.slice(0, 12) + (data.source === "defaults" ? " · 초기 기본값" : data.persistent ? " · 저장된 설정" : " · 메모리에만 적용");
    await searchDomain();
  } catch (error) { if (current === generation) $("domain-policy-status").textContent = error.message; }
}
$("domain-policy-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const current = generation;
  const enabled = Object.fromEntries(Object.keys(domainNames).map((id) => [id, $("domain-policy-form").elements.namedItem(id).checked]));
  try {
    const data = await domainRequest("/admin/api/domain-policy", {method: "POST", body: JSON.stringify({enabled})});
    if (current !== generation) return;
    renderDomainPolicy(data); $("domain-policy-status").textContent = "저장하고 적용했습니다. 기존 별칭은 유지됩니다.";
  } catch (error) { if (current === generation) $("domain-policy-status").textContent = error.message; }
});
async function searchDomain() {
  const current = generation;
  try {
    const params = new URLSearchParams({domain: $("domain-search").value, query: $("domain-query").value, offset: domainOffset, limit: 25});
    const data = await domainRequest("/admin/api/domain-terms?" + params);
    if (current !== generation) return;
    $("domain-results").replaceChildren(element("p", `${data.total}개 중 ${data.offset + 1}부터 · v${data.version}`), ...data.entries.map((entry) => {
      const item = element("p", entry.forms.map((form) => form.text).join(" / "));
      item.append(element("small", entry.activation_status === "active-editorial-core" ? " · 활성 전문/구성품 용어" : entry.activation_status === "active-source-label" ? " · 활성 공개 장비·사업·기술명" : " · 검수 대기: 보호 미적용"));
      return item;
    }));
    $("domain-previous").disabled = domainOffset === 0;
    $("domain-next").disabled = domainOffset + 25 >= data.total;
  } catch (error) { if (current === generation) $("domain-results").textContent = error.message; }
}
$("domain-search-form").addEventListener("submit", (event) => { event.preventDefault(); domainOffset = 0; searchDomain(); });
$("domain-previous").addEventListener("click", () => { domainOffset = Math.max(0, domainOffset - 25); searchDomain(); });
$("domain-next").addEventListener("click", () => { domainOffset += 25; searchDomain(); });
$("close-details").addEventListener("click", () => $("details").close());
setInterval(() => { if (token && $("auto-refresh").checked && !document.hidden && !$("dashboard").hidden) load(); }, 10000);

// --- Admin Masking Preview Section (#342) ---
let loadedFileText = "";
let loadedFileName = "";
let hasActiveResult = false;

function decodeFileBuffer(buffer, fileName) {
  const bytes = new Uint8Array(buffer);
  if (bytes.length > 256 * 1024) {
    throw new Error("파일 크기가 256 KiB를 초과합니다.");
  }
  const ext = (fileName.split(".").pop() || "").toLowerCase();
  const unsupported = new Set([
    "pdf", "docx", "doc", "zip", "tar", "gz", "png", "jpg", "jpeg", "gif", "webp", "bin", "exe",
  ]);
  if (unsupported.has(ext)) {
    throw new Error("PDF, DOCX, 이미지, 압축파일, 바이너리는 지원하지 않습니다.");
  }
  for (let i = 0; i < bytes.length; i++) {
    if (bytes[i] === 0) {
      throw new Error("바이너리(NUL) 데이터가 감지되어 처리할 수 없습니다.");
    }
  }
  try {
    const decoder = new TextDecoder("utf-8", { fatal: true });
    return decoder.decode(buffer);
  } catch (_) {
    throw new Error("UTF-8 인코딩으로 해석할 수 없는 파일입니다.");
  }
}

if (typeof window !== "undefined") {
  window.PreviewDecoder = { decodeFileBuffer };
}

function clearPreviewState() {
  loadedFileText = "";
  loadedFileName = "";
  hasActiveResult = false;
  if ($("preview-text")) $("preview-text").value = "";
  if ($("preview-file-input")) $("preview-file-input").value = "";
  if ($("preview-file-info")) {
    $("preview-file-info").textContent = "";
    $("preview-file-info").hidden = true;
  }
  if ($("preview-status")) $("preview-status").textContent = "";
  if ($("preview-stale")) $("preview-stale").hidden = true;
  if ($("preview-summary-bar")) $("preview-summary-bar").hidden = true;
  if ($("preview-comparison-container")) $("preview-comparison-container").replaceChildren();
}

function markPreviewStale() {
  if (hasActiveResult && $("preview-stale")) {
    $("preview-stale").hidden = false;
  }
}

function updateLanguageOptions() {
  const mode = $("preview-mode") ? $("preview-mode").value : "prose";
  const select = $("preview-lang");
  if (!select) return;

  const proseOptions = [
    { value: "auto", text: "자동 감지 (auto)" },
    { value: "ko", text: "한국어 (ko)" },
    { value: "en", text: "영어 (en)" },
    { value: "ja", text: "일본어 (ja)" },
    { value: "zh", text: "중국어 (zh)" },
    { value: "de", text: "독일어 (de)" },
    { value: "fr", text: "프랑스어 (fr)" },
    { value: "es", text: "스페인어 (es)" },
  ];

  const codeOptions = [
    { value: "auto", text: "자동 감지 (auto)" },
    { value: "python", text: "Python" },
    { value: "javascript", text: "JavaScript" },
    { value: "typescript", text: "TypeScript" },
    { value: "go", text: "Go" },
    { value: "rust", text: "Rust" },
    { value: "c", text: "C" },
    { value: "cpp", text: "C++" },
    { value: "java", text: "Java" },
    { value: "sql", text: "SQL" },
    { value: "bash", text: "Bash" },
    { value: "powershell", text: "PowerShell" },
  ];

  const list = mode === "code" ? codeOptions : proseOptions;
  select.replaceChildren(
    ...list.map((opt) => {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.text;
      return option;
    })
  );
}

function switchNav(hash) {
  const target = hash === "#audit" ? "audit" : hash === "#preview" ? "preview" : "overview";
  if (target !== "audit") {
    clearAuditState();
  }
  if ($("nav-overview")) $("nav-overview").classList.toggle("active", target === "overview");
  if ($("nav-preview")) $("nav-preview").classList.toggle("active", target === "preview");
  if ($("nav-audit")) $("nav-audit").classList.toggle("active", target === "audit");
  if ($("overview")) $("overview").hidden = target !== "overview";
  if ($("preview")) $("preview").hidden = target !== "preview";
  if ($("audit")) $("audit").hidden = target !== "audit";
  if (target === "audit") {
    loadAuditStatus();
    loadAuditSettings();
    populateAuditRequestSelect();
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("hashchange", () => switchNav(typeof location !== "undefined" ? location.hash : ""));
}
if ($("nav-overview")) {
  $("nav-overview").addEventListener("click", () => switchNav("#overview"));
}
if ($("nav-preview")) {
  $("nav-preview").addEventListener("click", () => switchNav("#preview"));
}
if ($("nav-audit")) {
  $("nav-audit").addEventListener("click", () => switchNav("#audit"));
}

if ($("tab-direct") && $("tab-file")) {
  $("tab-direct").addEventListener("click", () => {
    $("tab-direct").classList.add("active");
    $("tab-direct").setAttribute("aria-selected", "true");
    $("tab-file").classList.remove("active");
    $("tab-file").setAttribute("aria-selected", "false");
    $("pane-direct").hidden = false;
    $("pane-file").hidden = true;
    markPreviewStale();
  });
  $("tab-file").addEventListener("click", () => {
    $("tab-file").classList.add("active");
    $("tab-file").setAttribute("aria-selected", "true");
    $("tab-direct").classList.remove("active");
    $("tab-direct").setAttribute("aria-selected", "false");
    $("pane-file").hidden = false;
    $("pane-direct").hidden = true;
    markPreviewStale();
  });
}

if ($("preview-mode")) {
  $("preview-mode").addEventListener("change", () => {
    updateLanguageOptions();
    markPreviewStale();
  });
}

if ($("preview-lang")) {
  $("preview-lang").addEventListener("change", markPreviewStale);
}

if ($("preview-text")) {
  $("preview-text").addEventListener("input", markPreviewStale);
}

if ($("preview-file-input")) {
  $("preview-file-input").addEventListener("change", (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = decodeFileBuffer(reader.result, file.name);
        loadedFileText = text;
        loadedFileName = file.name;
        $("preview-file-info").textContent = `선택된 파일: ${file.name} (${num(file.size)} bytes, UTF-8 정상 검증)`;
        $("preview-file-info").hidden = false;
        $("preview-status").textContent = "";
        markPreviewStale();
      } catch (err) {
        loadedFileText = "";
        loadedFileName = "";
        $("preview-file-input").value = "";
        $("preview-file-info").textContent = err.message;
        $("preview-file-info").hidden = false;
        $("preview-status").textContent = err.message;
      }
    };
    reader.onerror = () => {
      $("preview-status").textContent = "파일을 읽을 수 없습니다.";
    };
    reader.readAsArrayBuffer(file);
  });
}

if ($("preview-clear")) {
  $("preview-clear").addEventListener("click", clearPreviewState);
}

if ($("preview-submit")) {
  $("preview-submit").addEventListener("click", async () => {
    if (!token) return;
    const isDirect = $("pane-direct") && !$("pane-direct").hidden;
    const text = isDirect ? $("preview-text").value : loadedFileText;
    if (!text) {
      $("preview-status").textContent = "원문을 입력하거나 텍스트 파일을 선택하세요.";
      return;
    }
    const mode = $("preview-mode") ? $("preview-mode").value : "prose";
    const lang = $("preview-lang") ? $("preview-lang").value : "auto";

    $("preview-submit").disabled = true;
    $("preview-status").textContent = "처리 중…";
    $("preview-status").setAttribute("aria-busy", "true");

    const payload = { text, mode, language: lang };
    if (mode === "code" && lang !== "auto") {
      payload.code_language = lang;
    }

    try {
      const response = await fetch("/admin/api/preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-SecureGateway-Token": token,
        },
        body: JSON.stringify(payload),
        cache: "no-store",
      });

      if (!response.ok) {
        if (response.status === 401) throw new Error("인증 토큰이 유효하지 않습니다.");
        if (response.status === 403) throw new Error("로컬 Origin에서만 접근할 수 있습니다.");
        if (response.status === 413) throw new Error("입력 크기가 256 KiB를 초과합니다.");
        if (response.status === 429) throw new Error("현재 다른 미리보기를 처리 중입니다. 잠시 후 다시 시도하세요.");
        if (response.status === 504) throw new Error("미리보기 처리 시간(10초)을 초과했습니다.");
        throw new Error("미리보기 처리에 실패했습니다.");
      }

      const data = await response.json();
      hasActiveResult = true;
      if ($("preview-stale")) $("preview-stale").hidden = true;

      // Update summary bar
      if ($("prev-stat-replacements")) $("prev-stat-replacements").textContent = `${num(data.stats.replacement_count)}건`;
      if ($("prev-stat-unique")) $("prev-stat-unique").textContent = `${num(data.stats.unique_alias_count)}개`;
      if ($("prev-stat-latency")) {
        $("prev-stat-latency").replaceChildren(
          document.createTextNode(`${num(data.stats.duration_ms)} `),
          element("em", "ms")
        );
      }
      if ($("prev-stat-policy")) {
        const modeLabel = data.stats.mode === "code" ? "코드" : "일반 문장";
        $("prev-stat-policy").textContent = `${modeLabel} · ${data.stats.selected_language}`;
      }
      if ($("prev-stat-policy-detail")) {
        const defenseOn = data.policy.domains && data.policy.domains.defense;
        $("prev-stat-policy-detail").replaceChildren(
          document.createTextNode(`강제 규칙 ${data.policy.forced_rule_count}건 · 방산 ${defenseOn ? "On" : "Off"} · `),
          element("a", "설정 화면 ↗", "quiet")
        );
        $("prev-stat-policy-detail").querySelector("a").href = "#overview";
      }
      if ($("preview-summary-bar")) $("preview-summary-bar").hidden = false;

      // Render Diff View
      if (globalThis.ComparisonView && $("preview-comparison-container")) {
        globalThis.ComparisonView.render($("preview-comparison-container"), {
          original: text,
          masked: data.masked,
          spans: data.spans,
          uncertain: data.uncertain,
        });
      }

      $("preview-status").textContent = data.uncertain
        ? "치환 완료 (구간 대응 불확실성 감지됨)"
        : "치환 결과를 정상적으로 불러왔습니다.";
    } catch (err) {
      $("preview-status").textContent = err.message || "오류가 발생했습니다.";
    } finally {
      $("preview-submit").disabled = false;
      $("preview-status").removeAttribute("aria-busy");
    }
  });
}

// --- Content Audit Screen & Logic (#343) ---

function setLiveStatus(msg) {
  if ($("audit-live-status")) {
    $("audit-live-status").textContent = msg;
  }
}

function clearAuditState() {
  activeAuditRequestId = null;
  activeAuditData = null;
  if ($("audit-request-view")) $("audit-request-view").hidden = true;
  if ($("audit-meta-id")) $("audit-meta-id").textContent = "—";
  if ($("audit-meta-time")) $("audit-meta-time").textContent = "—";
  if ($("audit-meta-agent-provider")) $("audit-meta-agent-provider").textContent = "—";
  if ($("audit-meta-status")) $("audit-meta-status").textContent = "—";
  if ($("audit-meta-duration")) $("audit-meta-duration").textContent = "—";
  if ($("audit-meta-mode")) $("audit-meta-mode").textContent = "—";
  if ($("audit-meta-policy")) $("audit-meta-policy").textContent = "—";
  if ($("audit-meta-state-badge")) {
    $("audit-meta-state-badge").textContent = "—";
    $("audit-meta-state-badge").className = "badge";
  }
  if ($("audit-stages-list")) $("audit-stages-list").replaceChildren();
  if ($("audit-review-memo")) $("audit-review-memo").value = "";
  if ($("audit-review-feedback")) $("audit-review-feedback").textContent = "";
  if ($("audit-review-display")) $("audit-review-display").hidden = true;
  if ($("audit-review-prev-memo")) $("audit-review-prev-memo").textContent = "—";
  if ($("audit-passphrase")) $("audit-passphrase").value = "";
  if ($("audit-exp-passphrase")) $("audit-exp-passphrase").value = "";
}

function resetAutoLockTimer() {
  if (!contentAuditStatus || contentAuditStatus.locked) {
    stopAutoLockTimer();
    return;
  }
  auditCountdownSeconds = AUDIT_INACTIVITY_TIMEOUT_SEC;
  updateCountdownDisplay();
  if (!auditAutoLockTimer) {
    auditAutoLockTimer = setInterval(() => {
      auditCountdownSeconds--;
      updateCountdownDisplay();
      if (auditCountdownSeconds <= 0) {
        stopAutoLockTimer();
        autoLockStore();
      }
    }, 1000);
  }
}

function stopAutoLockTimer() {
  if (auditAutoLockTimer) {
    clearInterval(auditAutoLockTimer);
    auditAutoLockTimer = null;
  }
  auditCountdownSeconds = 0;
  updateCountdownDisplay();
}

function updateCountdownDisplay() {
  if ($("audit-autolock-timer")) {
    if (contentAuditStatus && !contentAuditStatus.locked) {
      $("audit-autolock-timer").hidden = false;
      $("audit-autolock-timer").textContent = `자동 잠금까지: ${formatCountdown(auditCountdownSeconds)}`;
    } else {
      $("audit-autolock-timer").hidden = true;
    }
  }
}

async function autoLockStore() {
  if (!token) return;
  try {
    await fetch("/admin/api/content-audit/lock", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-SecureGateway-Token": token },
      body: JSON.stringify({}),
      cache: "no-store",
    });
  } catch (_) {}
  clearAuditState();
  if (contentAuditStatus) contentAuditStatus.locked = true;
  updateAuditStatusUI();
  setLiveStatus("일정 시간 동안 활동이 없어 내용 감사 저장소가 자동으로 잠겼습니다.");
}

async function fetchAuditOverview() {
  if (!token) return;
  try {
    const [statusRes, listRes] = await Promise.all([
      fetch("/admin/api/content-audit/status", { headers: { "X-SecureGateway-Token": token }, cache: "no-store" }),
      fetch("/admin/api/content-audit/list", { headers: { "X-SecureGateway-Token": token }, cache: "no-store" }),
    ]);
    if (statusRes.ok) {
      contentAuditStatus = await statusRes.json();
    }
    if (listRes.ok) {
      const listData = await listRes.json();
      contentAuditRequestsMap.clear();
      if (Array.isArray(listData.requests)) {
        for (const req of listData.requests) {
          contentAuditRequestsMap.set(req.request_id, req);
        }
      }
    }
  } catch (_) {}
}

async function loadAuditStatus() {
  await fetchAuditOverview();
  updateAuditStatusUI();
}

function updateAuditStatusUI() {
  if (!contentAuditStatus) return;
  const pill = $("audit-pill");
  const lockBtn = $("audit-lock-btn");
  const unlockBox = $("audit-unlock-box");
  const initLabel = $("audit-init-label");

  if (contentAuditStatus.locked) {
    if (pill) {
      pill.textContent = "저장소 잠김";
      pill.className = "pill warning";
    }
    if (lockBtn) lockBtn.hidden = true;
    if (unlockBox) unlockBox.hidden = false;
    if (initLabel) initLabel.hidden = Boolean(contentAuditStatus.initialized);
    stopAutoLockTimer();
  } else {
    if (pill) {
      if (!contentAuditStatus.enabled) {
        pill.textContent = "수집 꺼짐";
        pill.className = "pill";
      } else if (contentAuditStatus.paused) {
        pill.textContent = "일시 중지";
        pill.className = "pill warning";
      } else {
        pill.textContent = "감사 활성";
        pill.className = "pill success";
      }
    }
    if (lockBtn) lockBtn.hidden = false;
    if (unlockBox) unlockBox.hidden = true;
    resetAutoLockTimer();
  }

  if ($("audit-state-summary")) {
    const statusText = !contentAuditStatus.enabled ? "비활성 (수집 안 함)"
      : contentAuditStatus.paused ? "일시 중지됨"
      : "활성화됨 (정상 수집 중)";
    const lockText = contentAuditStatus.locked ? "저장소 잠김" : "잠금 해제됨 (열림)";
    $("audit-state-summary").textContent = `현재 상태: ${statusText} · ${lockText}`;
  }
}

async function loadAuditSettings() {
  if (!token) return;
  try {
    const res = await fetch("/admin/api/content-audit/settings", {
      headers: { "X-SecureGateway-Token": token },
      cache: "no-store",
    });
    if (!res.ok) throw new Error();
    const data = await res.json();
    populateAuditSettings(data);
  } catch (_) {
    if ($("audit-settings-status")) {
      $("audit-settings-status").textContent = "설정을 불러오지 못했습니다.";
    }
  }
}

function populateAuditSettings(data) {
  if ($("audit-enable-toggle")) {
    $("audit-enable-toggle").checked = Boolean(data.enabled);
  }
  if ($("audit-prov-claude")) $("audit-prov-claude").checked = Boolean(data.providers?.claude);
  if ($("audit-prov-codex")) $("audit-prov-codex").checked = Boolean(data.providers?.codex);
  if ($("audit-prov-xai")) $("audit-prov-xai").checked = Boolean(data.providers?.xai);

  if ($("audit-kind-input")) $("audit-kind-input").checked = Boolean(data.kinds?.input);
  if ($("audit-kind-sent")) $("audit-kind-sent").checked = Boolean(data.kinds?.sent);
  if ($("audit-kind-response")) $("audit-kind-response").checked = Boolean(data.kinds?.response);
  if ($("audit-kind-tool-args")) $("audit-kind-tool-args").checked = Boolean(data.kinds?.tool_args);
  if ($("audit-kind-tool-result")) $("audit-kind-tool-result").checked = Boolean(data.kinds?.tool_result);

  if ($("audit-failure-policy")) $("audit-failure-policy").value = data.failure_policy || "continue";
  if ($("audit-max-age")) $("audit-max-age").value = data.retention?.max_age_days ?? 7;
  if ($("audit-max-requests")) $("audit-max-requests").value = data.retention?.max_records ?? 1000;
  if ($("audit-max-mib")) $("audit-max-mib").value = Math.round((data.retention?.max_bytes || 268435456) / (1024 * 1024));

  if ($("audit-warning-box")) $("audit-warning-box").hidden = true;
  if ($("audit-confirm-warning")) $("audit-confirm-warning").checked = false;
}

function populateAuditRequestSelect() {
  const select = $("audit-request-select");
  if (!select) return;
  const options = [];
  for (const [id, req] of contentAuditRequestsMap) {
    if (req.created) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = `${id} (${req.state || "완료"})`;
      options.push(opt);
    }
  }
  select.replaceChildren(...options);
  if (activeAuditRequestId) {
    select.value = activeAuditRequestId;
  }
}

async function openAuditForRequest(requestId) {
  switchNav("#audit");
  await loadAuditRequest(requestId);
}

async function loadAuditRequest(requestId) {
  if (!token || !requestId) return;
  clearAuditState();
  activeAuditRequestId = requestId;

  if ($("audit-request-view")) $("audit-request-view").hidden = false;
  if ($("audit-meta-id")) $("audit-meta-id").textContent = requestId;
  if ($("audit-meta-status")) $("audit-meta-status").textContent = "복호화 및 분석 중...";

  try {
    const res = await fetch("/admin/api/content-audit/get", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-SecureGateway-Token": token,
      },
      body: JSON.stringify({ request_id: requestId }),
      cache: "no-store",
    });

    if (!res.ok) {
      if (res.status === 423) {
        throw new Error("저장소가 잠겨 있습니다. 상단에서 잠금 해제 후 확인하세요.");
      }
      if (res.status === 404) {
        throw new Error("해당 요청에 대한 내용 감사 기록이 없거나 이미 삭제되었습니다.");
      }
      throw new Error("내용 감사 기록을 불러오지 못했습니다.");
    }

    const data = await res.json();
    activeAuditData = data;
    renderAuditRequest(data);
    populateAuditRequestSelect();
    setLiveStatus(`${requestId} 요청의 치환·복원 감사 내역을 불러왔습니다.`);
  } catch (err) {
    if ($("audit-meta-status")) $("audit-meta-status").textContent = err.message;
    setLiveStatus(`오류: ${err.message}`);
  }
}

function renderAuditRequest(data) {
  const meta = data.metadata || {};
  const vState = data.verified_state || "부분";

  if ($("audit-meta-id")) $("audit-meta-id").textContent = meta.request_id || activeAuditRequestId;
  if ($("audit-meta-time")) $("audit-meta-time").textContent = meta.started_at ? time(meta.started_at) : "—";
  if ($("audit-meta-agent-provider")) {
    const p = providers[meta.provider] || meta.provider || "—";
    const a = meta.agent || "—";
    $("audit-meta-agent-provider").textContent = `${a} / ${p}`;
  }
  if ($("audit-meta-status")) {
    const s = meta.status != null ? `${meta.status} (${outcomes[meta.outcome] || meta.outcome || "완료"})` : "미완료";
    $("audit-meta-status").textContent = s;
  }
  if ($("audit-meta-duration")) {
    $("audit-meta-duration").textContent = meta.duration_ms != null ? `${num(Math.round(meta.duration_ms))} ms` : "—";
  }
  if ($("audit-meta-mode")) {
    const pol = meta.policy || {};
    const modeLabel = pol.mode === "code" ? "소스 코드" : "일반 문장";
    $("audit-meta-mode").textContent = `${modeLabel} · ${pol.language || "auto"}`;
  }
  if ($("audit-meta-policy")) {
    const pol = meta.policy || {};
    const domains = pol.domains ? Object.entries(pol.domains).filter(([, v]) => v).map(([k]) => domainNames[k] || k).join(", ") : "";
    const polDesc = `강제 규칙 ${pol.forced_rule_count || 0}건${domains ? ` · 사전: ${domains}` : ""}`;
    $("audit-meta-policy").textContent = polDesc;
  }
  if ($("audit-meta-state-badge")) {
    $("audit-meta-state-badge").textContent = vState;
    const badgeClass = vState === "완료" ? "badge badge-success"
      : vState === "부분" ? "badge badge-warning"
      : vState === "전송 여부 불확실" ? "badge badge-uncertain"
      : "badge badge-error";
    $("audit-meta-state-badge").className = badgeClass;
  }

  // Render Stages
  const stagesList = $("audit-stages-list");
  if (stagesList) {
    stagesList.replaceChildren();

    const stageEntries = Object.entries(data.stages || {});
    if (stageEntries.length === 0) {
      stagesList.append(element("p", "기록된 단계(Stage)가 없습니다.", "muted"));
    } else {
      for (const [key, stage] of stageEntries) {
        const stageCard = element("article", undefined, "audit-stage-card");

        // Header
        const stageHeader = element("div", undefined, "audit-stage-header");
        const titleDiv = element("div");
        const title = element("h3", stage.name || key);
        titleDiv.append(title);
        if (stage.phase) {
          const phaseBadge = element("span", ` [단계: ${stage.phase}]`, "fine muted");
          titleDiv.append(phaseBadge);
        }

        const badgesDiv = element("div", undefined, "stage-badges");
        if (stage.uncertain) {
          const uncBadge = element("span", "대응 관계 불확실", "badge badge-uncertain");
          badgesDiv.append(uncBadge);
        }
        stageHeader.append(titleDiv, badgesDiv);
        stageCard.append(stageHeader);

        // Diff Container
        const diffContainer = element("div", undefined, "stage-diff-wrapper");
        stageCard.append(diffContainer);

        if (globalThis.ComparisonView) {
          let origLabel = "원문";
          let maskedLabel = "마스킹";
          if (key === "input_sent") {
            origLabel = "입력 원문 (input)";
            maskedLabel = stage.phase === "prepared" ? "준비된 마스킹 (prepared)" : "실제 전송된 마스킹 (sent)";
          } else if (key === "response") {
            origLabel = "로컬 복원 표시 (displayed)";
            maskedLabel = "모델 수신 마스킹 (received)";
          } else if (key === "tool_args") {
            origLabel = "도구 복원 인자 (restored)";
            maskedLabel = "모델 수신 마스킹 (masked)";
          } else if (key === "tool_result") {
            origLabel = "도구 원본 결과 (original)";
            maskedLabel = "재마스킹 결과 (re-masked)";
          }

          globalThis.ComparisonView.render(diffContainer, {
            original: stage.original || "",
            masked: stage.masked || "",
            spans: stage.uncertain ? [] : (stage.spans || []),
            uncertain: stage.uncertain,
            originalLabel: origLabel,
            maskedLabel: maskedLabel,
            uncertainNotice: stage.notice || (stage.uncertain ? "대응 관계를 확인할 수 없음" : undefined),
          });
        }

        // Unrestored aliases notice
        if (stage.unrestored_aliases && stage.unrestored_aliases.length > 0) {
          const unrestoredBox = element("div", undefined, "audit-unrestored-box");
          unrestoredBox.append(
            element("span", "⚠️ 미복원 별칭 감지: ", "error-text"),
            document.createTextNode(stage.unrestored_aliases.join(", ") + " (복원되지 않은 채 화면에 표시됨)")
          );
          stageCard.append(unrestoredBox);
        }

        stagesList.append(stageCard);
      }
    }
  }

  // Review section
  if (data.review) {
    if ($("audit-review-current-badge")) {
      $("audit-review-current-badge").textContent = data.review.status || "미검토";
      $("audit-review-current-badge").className = data.review.status === "정상" ? "badge badge-success" : "badge badge-warning";
    }
    if ($("audit-review-prev-memo")) {
      $("audit-review-prev-memo").textContent = data.review.memo || "메모 없음";
    }
    if ($("audit-review-display")) $("audit-review-display").hidden = false;
    if ($("audit-review-status-select")) $("audit-review-status-select").value = data.review.status || "정상";
    if ($("audit-review-memo")) $("audit-review-memo").value = data.review.memo || "";
  } else {
    if ($("audit-review-current-badge")) {
      $("audit-review-current-badge").textContent = "미검토";
      $("audit-review-current-badge").className = "badge";
    }
    if ($("audit-review-display")) $("audit-review-display").hidden = true;
    if ($("audit-review-memo")) $("audit-review-memo").value = "";
  }
}

// Event Listeners for Content Audit
if ($("audit-enable-toggle")) {
  $("audit-enable-toggle").addEventListener("change", (e) => {
    const isEnabling = e.target.checked;
    if ($("audit-warning-box")) {
      $("audit-warning-box").hidden = !isEnabling;
    }
    if (!isEnabling && $("audit-confirm-warning")) {
      $("audit-confirm-warning").checked = false;
    }
  });
}

if ($("audit-settings-form")) {
  $("audit-settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!token) return;

    const enabled = $("audit-enable-toggle") ? $("audit-enable-toggle").checked : false;
    const confirmSensitive = $("audit-confirm-warning") ? $("audit-confirm-warning").checked : false;

    if (enabled && !confirmSensitive && (contentAuditStatus && !contentAuditStatus.enabled)) {
      if ($("audit-settings-status")) {
        $("audit-settings-status").textContent = "내용 감사를 활성화하려면 주의사항 확인 체크가 필요합니다.";
      }
      if ($("audit-warning-box")) $("audit-warning-box").hidden = false;
      return;
    }

    const maxMib = Number($("audit-max-mib")?.value || 256);
    const settings = {
      enabled,
      paused: contentAuditStatus?.paused || false,
      failure_policy: $("audit-failure-policy")?.value || "continue",
      providers: {
        claude: Boolean($("audit-prov-claude")?.checked),
        codex: Boolean($("audit-prov-codex")?.checked),
        xai: Boolean($("audit-prov-xai")?.checked),
      },
      agents: {
        all: true,
      },
      kinds: {
        input: Boolean($("audit-kind-input")?.checked),
        sent: Boolean($("audit-kind-sent")?.checked),
        response: Boolean($("audit-kind-response")?.checked),
        tool_args: Boolean($("audit-kind-tool-args")?.checked),
        tool_result: Boolean($("audit-kind-tool-result")?.checked),
      },
      retention: {
        max_age_days: Number($("audit-max-age")?.value || 7),
        max_records: Number($("audit-max-requests")?.value || 1000),
        max_bytes: maxMib * 1024 * 1024,
      },
    };

    if ($("audit-save-settings")) $("audit-save-settings").disabled = true;
    if ($("audit-settings-status")) $("audit-settings-status").textContent = "저장 중...";

    try {
      const res = await fetch("/admin/api/content-audit/settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-SecureGateway-Token": token,
        },
        body: JSON.stringify({
          settings,
          confirm_sensitive_content: confirmSensitive,
        }),
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 409) throw new Error("메타데이터 감사가 켜져 있어야 내용 감사를 사용할 수 있습니다.");
        throw new Error("설정 저장에 실패했습니다.");
      }

      const saved = await res.json();
      populateAuditSettings(saved);
      if ($("audit-settings-status")) $("audit-settings-status").textContent = "설정이 저장되었습니다.";
      await fetchAuditOverview();
      updateAuditStatusUI();
      setLiveStatus("내용 감사 설정이 저장되었습니다.");
    } catch (err) {
      if ($("audit-settings-status")) $("audit-settings-status").textContent = err.message || "설정 저장 실패";
    } finally {
      if ($("audit-save-settings")) $("audit-save-settings").disabled = false;
    }
  });
}

if ($("audit-unlock-form")) {
  $("audit-unlock-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!token) return;

    const passphraseInput = $("audit-passphrase");
    const passphrase = passphraseInput ? passphraseInput.value : "";
    const initCheckbox = $("audit-init-checkbox");
    const initialize = initCheckbox ? initCheckbox.checked : false;

    if (!passphrase) return;

    const statusEl = $("audit-unlock-status");
    if (statusEl) statusEl.textContent = "잠금 해제 확인 중...";

    try {
      const res = await fetch("/admin/api/content-audit/unlock", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-SecureGateway-Token": token,
        },
        body: JSON.stringify({ passphrase, initialize }),
        cache: "no-store",
      });

      // Clear passphrase immediately
      if (passphraseInput) passphraseInput.value = "";

      if (!res.ok) {
        if (res.status === 429) {
          throw new Error("연속 실패로 인해 잠금 해제가 일시 차단되었습니다 (1분 후 재시도).");
        }
        if (res.status === 401) {
          throw new Error("암호문구가 일치하지 않습니다.");
        }
        throw new Error("저장소 잠금 해제에 실패했습니다.");
      }

      if (statusEl) statusEl.textContent = "";
      await fetchAuditOverview();
      updateAuditStatusUI();
      setLiveStatus("저장소 잠금이 해제되었습니다.");
      if (activeAuditRequestId) {
        loadAuditRequest(activeAuditRequestId);
      }
    } catch (err) {
      if (passphraseInput) passphraseInput.value = "";
      if (statusEl) statusEl.textContent = err.message || "잠금 해제 실패";
    }
  });
}

if ($("audit-lock-btn")) {
  $("audit-lock-btn").addEventListener("click", async () => {
    if (!token) return;
    try {
      await fetch("/admin/api/content-audit/lock", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-SecureGateway-Token": token,
        },
        body: JSON.stringify({}),
        cache: "no-store",
      });
    } catch (_) {}
    clearAuditState();
    stopAutoLockTimer();
    if (contentAuditStatus) contentAuditStatus.locked = true;
    updateAuditStatusUI();
    setLiveStatus("저장소가 잠겼습니다.");
  });
}

if ($("audit-refresh")) {
  $("audit-refresh").addEventListener("click", async () => {
    await fetchAuditOverview();
    updateAuditStatusUI();
    populateAuditRequestSelect();
    if (activeAuditRequestId) {
      loadAuditRequest(activeAuditRequestId);
    }
  });
}

if ($("audit-request-select")) {
  $("audit-request-select").addEventListener("change", (e) => {
    const selected = e.target.value;
    if (selected) {
      loadAuditRequest(selected);
    }
  });
}

if ($("audit-review-form")) {
  $("audit-review-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!token || !activeAuditRequestId) return;

    const status = $("audit-review-status-select")?.value || "정상";
    const memo = $("audit-review-memo")?.value || "";
    const feedback = $("audit-review-feedback");
    if (feedback) feedback.textContent = "저장 중...";

    try {
      const res = await fetch("/admin/api/content-audit/review", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-SecureGateway-Token": token,
        },
        body: JSON.stringify({
          request_id: activeAuditRequestId,
          status,
          memo,
        }),
        cache: "no-store",
      });

      if (!res.ok) throw new Error("검토 저장에 실패했습니다.");
      if (feedback) feedback.textContent = "검토 결과가 암호화되어 안전하게 저장되었습니다.";
      if ($("audit-review-current-badge")) {
        $("audit-review-current-badge").textContent = status;
        $("audit-review-current-badge").className = status === "정상" ? "badge badge-success" : "badge badge-warning";
      }
      if ($("audit-review-prev-memo")) $("audit-review-prev-memo").textContent = memo;
      if ($("audit-review-display")) $("audit-review-display").hidden = false;
      setLiveStatus("검토 결과가 저장되었습니다.");
    } catch (err) {
      if (feedback) feedback.textContent = err.message || "저장 실패";
    }
  });
}

if ($("audit-btn-delete")) {
  $("audit-btn-delete").addEventListener("click", () => {
    if (!activeAuditRequestId) return;
    if ($("audit-delete-target-text")) {
      $("audit-delete-target-text").textContent = `삭제 대상: 요청 ID ${activeAuditRequestId}`;
    }
    if ($("audit-delete-status")) $("audit-delete-status").textContent = "";
    if ($("audit-delete-dialog")) $("audit-delete-dialog").showModal();
  });
}
if ($("close-audit-delete")) {
  $("close-audit-delete").addEventListener("click", () => $("audit-delete-dialog")?.close());
}
if ($("audit-delete-cancel-btn")) {
  $("audit-delete-cancel-btn").addEventListener("click", () => $("audit-delete-dialog")?.close());
}
if ($("audit-delete-confirm-btn")) {
  $("audit-delete-confirm-btn").addEventListener("click", async () => {
    if (!token || !activeAuditRequestId) return;
    const statusEl = $("audit-delete-status");
    if (statusEl) statusEl.textContent = "삭제 진행 중...";

    try {
      const res = await fetch("/admin/api/content-audit/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-SecureGateway-Token": token,
        },
        body: JSON.stringify({ request_ids: [activeAuditRequestId] }),
        cache: "no-store",
      });

      if (!res.ok) throw new Error("삭제에 실패했습니다.");
      $("audit-delete-dialog")?.close();
      clearAuditState();
      await fetchAuditOverview();
      populateAuditRequestSelect();
      setLiveStatus("요청 감사 기록이 영구 삭제되었습니다.");
    } catch (err) {
      if (statusEl) statusEl.textContent = err.message || "삭제 실패";
    }
  });
}

if ($("audit-btn-export")) {
  $("audit-btn-export").addEventListener("click", () => {
    if (!activeAuditRequestId) return;
    if ($("audit-export-status")) $("audit-export-status").textContent = "";
    if ($("audit-exp-passphrase")) $("audit-exp-passphrase").value = "";
    if ($("audit-exp-confirm-plain")) $("audit-exp-confirm-plain").checked = false;
    if ($("audit-export-dialog")) $("audit-export-dialog").showModal();
  });
}
if ($("close-audit-export")) {
  $("close-audit-export").addEventListener("click", () => $("audit-export-dialog")?.close());
}
if ($("audit-export-cancel-btn")) {
  $("audit-export-cancel-btn").addEventListener("click", () => $("audit-export-dialog")?.close());
}

if ($("audit-exp-fmt-enc") && $("audit-exp-fmt-plain")) {
  const toggleFmt = () => {
    const isPlain = $("audit-exp-fmt-plain").checked;
    if ($("audit-exp-plain-warning")) $("audit-exp-plain-warning").hidden = !isPlain;
    if ($("audit-exp-pass-box")) $("audit-exp-pass-box").hidden = isPlain;
  };
  $("audit-exp-fmt-enc").addEventListener("change", toggleFmt);
  $("audit-exp-fmt-plain").addEventListener("change", toggleFmt);
}

if ($("audit-export-form")) {
  $("audit-export-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!token || !activeAuditRequestId) return;

    const statusEl = $("audit-export-status");
    const isPlain = $("audit-exp-fmt-plain") ? $("audit-exp-fmt-plain").checked : false;
    const passphraseInput = $("audit-exp-passphrase");
    const passphrase = passphraseInput ? passphraseInput.value : "";
    const confirmPlain = $("audit-exp-confirm-plain") ? $("audit-exp-confirm-plain").checked : false;

    if (isPlain && !confirmPlain) {
      if (statusEl) statusEl.textContent = "평문 내보내기 승인 체크박스를 확인하세요.";
      return;
    }
    if (!isPlain && !passphrase) {
      if (statusEl) statusEl.textContent = "내보내기 보호용 암호문구를 입력하세요.";
      return;
    }

    const form = $("audit-export-form");
    const kinds = [];
    if (form) {
      for (const input of form.querySelectorAll("input[name='exp_kind']")) {
        if (input.checked) kinds.push(input.value);
      }
    }
    if (kinds.length === 0) {
      if (statusEl) statusEl.textContent = "최소 하나 이상의 종류를 선택하세요.";
      return;
    }

    const payload = {
      request_ids: [activeAuditRequestId],
      kinds,
      plaintext: isPlain,
      confirm_plaintext: confirmPlain,
    };
    if (!isPlain) {
      payload.passphrase = passphrase;
    }

    if (statusEl) statusEl.textContent = "내보내기 생성 중...";

    try {
      const res = await fetch("/admin/api/content-audit/export", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-SecureGateway-Token": token,
        },
        body: JSON.stringify(payload),
        cache: "no-store",
      });

      if (passphraseInput) passphraseInput.value = "";

      if (!res.ok) throw new Error("내보내기에 실패했습니다.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `content-audit-${activeAuditRequestId}.${isPlain ? "json" : "enc"}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 100);

      $("audit-export-dialog")?.close();
      setLiveStatus("감사 데이터 파일이 다운로드되었습니다.");
    } catch (err) {
      if (passphraseInput) passphraseInput.value = "";
      if (statusEl) statusEl.textContent = err.message || "내보내기 실패";
    }
  });
}

if (typeof window !== "undefined") {
  ["mousemove", "keydown", "click", "scroll"].forEach((evt) => {
    window.addEventListener(evt, () => {
      if (contentAuditStatus && !contentAuditStatus.locked) {
        resetAutoLockTimer();
      }
    }, { passive: true });
  });
  window.addEventListener("beforeunload", () => {
    clearAuditState();
  });

  window.AuditUI = {
    determineAuditAction,
    formatCountdown,
    clearAuditState,
    hasDecryptedState: () => activeAuditData !== null,
    resetAutoLockTimer,
    stopAutoLockTimer,
    loadAuditRequest,
    autoLockStore,
  };
}

if (typeof globalThis !== "undefined") {
  globalThis.AuditUI = globalThis.AuditUI || {
    determineAuditAction,
    formatCountdown,
    clearAuditState,
    hasDecryptedState: () => activeAuditData !== null,
  };
}

