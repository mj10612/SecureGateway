"use strict";
const $ = (id) => document.getElementById(id);
const providers = {claude: "Anthropic", codex: "OpenAI", xai: "xAI"};
const subscriptions = {claude_subscription: "Claude 구독", chatgpt_subscription: "ChatGPT 구독", api_key: "xAI API 키"};
const outcomes = {blocked: "전송 전 차단", completed: "완료", upstream_rejected: "제공자 거절", transport_error: "연결 오류", restore_error: "복원 오류", incomplete: "진행 중 / 미완료", interrupted: "프로세스 중단"};
let token = "", offset = 0, generation = 0, loading = false, pending = false, auditWriteErrors = 0;
let auditErrorCounts = null, completionRetries = {};
const limit = 50;
let exportEpoch = 0, exportCursor = "", exportFilters = null, exportNumber = 0, exporting = false;
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
