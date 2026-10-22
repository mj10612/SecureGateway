"use strict";
const $ = (id) => document.getElementById(id);
const providers = {claude: "Anthropic", codex: "OpenAI", xai: "xAI"};
const subscriptions = {claude_subscription: "Claude 구독", chatgpt_subscription: "ChatGPT 구독", api_key: "xAI API 키"};
const outcomes = {blocked: "전송 전 차단", completed: "완료", upstream_rejected: "제공자 거절", transport_error: "연결 오류", restore_error: "복원 오류", incomplete: "진행 중 / 미완료", interrupted: "프로세스 중단"};
let token = "", offset = 0, generation = 0, loading = false, pending = false;
const limit = 50;
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
      offset = 0; $("details").close(); load();
    });
    const action = element("dd"); action.append(filterButton);
    $("detail-fields").append(element("dt", "요청 필터"), action);
  }
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
    const result = element("td"), kind = row.status == null ? "pending" : row.status < 400 ? "success" : "error";
    result.append(element("span", row.status == null ? "미완료" : `${row.status} ${kind === "success" ? "성공" : "실패"}`, `status ${kind}`), element("small", outcomes[row.outcome] || row.outcome));
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
  $("banner").hidden = data.audit_write_errors === 0;
  $("banner").textContent = `로그 저장 오류 ${num(data.audit_write_errors)}건이 발생했습니다. 일부 요청은 미완료로 남거나 전송 전에 차단됐을 수 있습니다.`;
}
async function load() {
  if (!token) return false;
  if (loading) { pending = true; return false; }
  loading = true;
  const current = generation, params = new URLSearchParams({limit, offset});
  for (const [key, value] of new FormData($("filters"))) {
    if (value) params.set(key, key === "since" ? new Date(value).toISOString() : value);
  }
  try {
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
  event.preventDefault(); generation++; token = $("token").value.trim();
  if (await load()) { $("token").value = ""; $("login-error").textContent = ""; $("login").hidden = true; $("dashboard").hidden = false; }
});
$("logout").addEventListener("click", () => {
  token = ""; generation++; offset = 0; $("rows").replaceChildren(); $("detail-fields").replaceChildren();
  $("details").close(); $("dashboard").hidden = true; $("login").hidden = false; $("token").focus();
});
$("refresh").addEventListener("click", load);
$("filters").addEventListener("submit", (event) => event.preventDefault());
$("filters").addEventListener("change", () => { offset = 0; load(); });
$("filters").addEventListener("reset", () => { offset = 0; setTimeout(load, 0); });
$("previous").addEventListener("click", () => { offset = Math.max(0, offset - limit); load(); });
$("next").addEventListener("click", () => { offset += limit; load(); });
$("close-details").addEventListener("click", () => $("details").close());
setInterval(() => { if (token && $("auto-refresh").checked && !document.hidden && !$("dashboard").hidden) load(); }, 10000);
