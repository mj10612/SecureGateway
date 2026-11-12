"""Independently author a #319 replication batch (confidential numeric operands only).

The author receives the issue title/body and a case-format specification, never
the candidate implementation, prior responses or earlier cases.
"""
import json, os, pathlib, shutil, subprocess, tempfile

BATCH = int(os.environ['BATCH'])
SOLVABLE = int(os.environ.get('SOLVABLE', 20))
NO_CALC = int(os.environ.get('NO_CALC', 7))
IMPOSSIBLE = int(os.environ.get('IMPOSSIBLE', 13))
TOTAL = SOLVABLE + NO_CALC + IMPOSSIBLE

issue = json.loads(subprocess.check_output(['gh', 'issue', 'view', '319', '--json', 'title,body'], encoding='utf8'))
spec = f"""Author exactly {TOTAL} original synthetic, self-contained holdout cases: {SOLVABLE} tool_solvable, {NO_CALC} no_calculation, {IMPOSSIBLE} impossible.
Use fictional scenarios only. Every confidential operand must be a plain standalone numeric token (digits, optional single decimal point) surrounded by spaces or punctuation, at most one decimal point, never inside a word, never repeated elsewhere in the text, and never adjacent to a unit, currency symbol or percent sign.
Return one JSON object with a cases array and no markdown.
Per case include: id (unique string), original (English task text), human_masked (replace exactly the confidential numeric operands with [PRIVATE_1], [PRIVATE_2], ... in order of appearance, preserving all other text), negative_control (true only for no_calculation, otherwise false), applicable (array chosen from intent, action, conditions, prohibition, order, clarification, scope), expected (specific correct behavior), label (tool_solvable, no_calculation or impossible), operation (add, subtract, multiply or divide for solvable; a short description otherwise), unit (USD, EUR or KRW for monetary tasks; another unit word otherwise), gold (exact correct result for solvable; the correct limitation or required question otherwise), sensitive_spans and public_spans arrays of {{start,end,text}} with zero-based Unicode code point offsets, end exclusive.
Public spans must be ordinary task words, never numeric values, never private identifiers, must not overlap sensitive spans, and every span text must occur exactly once in original.
tool_solvable cases must supply every operand needed for the arithmetic in the text, must require using the local arithmetic tool with the supplied aliases, and must ask for a protected result with no intermediate values exposed.
no_calculation cases must require no arithmetic and must forbid unnecessary tool use.
impossible cases must lack a required operand or explicitly prohibit the operation, and must require asking instead of computing.
Do not use tools, browsing, files, prior context or implementation code. Do not include real personal information."""
prompt = 'Issue text:\n' + json.dumps(issue, ensure_ascii=False) + '\n\nCase-format specification:\n' + spec
with tempfile.TemporaryDirectory(prefix=f'secure-case-author-319b{BATCH}-') as root:
    out = pathlib.Path(root) / 'out.json'
    ev = pathlib.Path(root) / 'events.jsonl'
    cmd = [shutil.which('codex'), 'exec', '--ephemeral', '--skip-git-repo-check', '--ignore-user-config', '--ignore-rules',
           '--sandbox', 'read-only', '--model', 'gpt-6.1-sol', '--json', '--output-last-message', str(out),
           '-c', 'forced_login_method="chatgpt"', '-c', 'project_doc_max_bytes=0', '-c', 'developer_instructions=""',
           '-c', 'web_search="disabled"', '-c', 'features.multi_agent=false', '-c', 'model_reasoning_effort="low"', '-']
    allowed = {'PATH', 'HOME', 'USERPROFILE', 'CODEX_HOME', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'LANG',
               'LC_ALL', 'LC_CTYPE', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'http_proxy',
               'https_proxy', 'all_proxy', 'no_proxy', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE',
               'NODE_EXTRA_CA_CERTS'}
    env = {k: v for k, v in os.environ.items() if k in allowed}
    with ev.open('wb') as f:
        p = subprocess.run(cmd, input=prompt.encode('utf8'), stdout=f, stderr=subprocess.DEVNULL, cwd=root, timeout=900, env=env)
    if p.returncode:
        raise SystemExit('AuthorProcessFailed')
    usage = None
    completed = False
    for line in ev.read_text(encoding='utf8').splitlines():
        event = json.loads(line)
        kind = event.get('type')
        if isinstance(kind, str) and kind.startswith('item.') and event.get('item', {}).get('type') not in ('agent_message', 'reasoning'):
            raise SystemExit('ToolEvent')
        if kind in ('error', 'turn.failed'):
            raise SystemExit('FailedTurn')
        if kind == 'turn.completed':
            completed = True
            usage = event.get('usage')
    if not completed or not usage:
        raise SystemExit('MissingUsage')
    data = json.loads(out.read_text(encoding='utf8'))
    assert isinstance(data['cases'], list) and len(data['cases']) == TOTAL

dest = pathlib.Path('docs/evaluations/comprehension-2.11.1/319/plan') / f'replication-batch{BATCH}-authored.json'
dest.write_text(json.dumps({'provenance': 'Fresh isolated author received issue title/body and case-format specification only.',
                            'batch': BATCH, 'format_specification': spec, 'reported_usage': usage, 'tool_events': 0,
                            'cases': data['cases']}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('319 batch', BATCH, 'authored', len(data['cases']), 'usage', usage)
