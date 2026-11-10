"""Content-free failure observation for an unchanged, frozen native adapter.

This wrapper never changes prompts, CLI arguments or successful results. It only
observes exceptions from the legacy adapter, preserving that adapter's byte hash
and the validity of already saved answers/reference audits. Old lost diagnostics
cannot be reconstructed by this prospective observer.
"""
from __future__ import annotations

from secure_gateway.exceptions import ProcessError

from hashlib import sha256
import time

from secure_gateway import evaluation_codex_worker as native
from secure_gateway.evaluation import digest


_CODES = {
    'Codex CLI is not installed.': ('setup', 'cli_missing'),
    'Codex CLI returned an invalid version.': ('cli_version', 'invalid_version'),
    'Worker executable could not be started.': ('process_start', 'start_failed'),
    'Worker executable failed.': ('process_exit', 'nonzero_exit'),
    'Worker execution timed out.': ('timeout', 'process_timeout'),
    'Worker output limit exceeded.': ('capture', 'capture_limit'),
    'Worker output could not be captured.': ('capture', 'capture_failed'),
    'Codex inference failed.': ('events', 'provider_failed'),
    'Codex used a tool during a semantic task.': ('events', 'tool_event'),
    'Codex did not complete a turn.': ('events', 'no_completed_turn'),
    'Codex returned an unsupported event.': ('events', 'unsupported_event'),
    'Codex returned invalid events.': ('events', 'invalid_event'),
    'Codex returned multiple turns.': ('events', 'multiple_turns'),
    'Codex returned invalid usage.': ('events', 'invalid_usage'),
    'Codex final output limit exceeded.': ('final_message', 'final_limit'),
    'Codex did not return a valid final message.': ('final_message', 'invalid_final'),
    'Codex returned invalid grading JSON.': ('grade_json', 'invalid_grade_shape'),
    'Worker returned invalid JSON.': ('json', 'invalid_json'),
    'Worker returned invalid grades.': ('result_validation', 'invalid_grades'),
    'Worker returned invalid or excessive token usage.': ('result_validation', 'invalid_or_excessive_usage'),
    'Worker response output limit exceeded.': ('result_validation', 'response_limit'),
}


class ObservedWorkerFailure(ProcessError, ValueError):
    """A fixed safe error code and optional validated usage, never model text."""

    def __init__(self, diagnostics, usage=None):
        super().__init__('Native evaluation failed: ' + diagnostics['code'])
        self.diagnostics = diagnostics
        self.usage = usage


def diagnostic_worker(request):
    """Call the original adapter verbatim; inspect only allowlisted error evidence."""
    started = time.monotonic()
    try:
        return native.run_codex_worker(request)
    except (ValueError, OSError) as exc:
        stage, code = _CODES.get(str(exc), ('unknown', 'unclassified_failure'))
        evidence = {'job_id': request.get('job_id'), 'request_sha256': digest(request),
                    'stage': stage, 'code': code, 'exception_type': type(exc).__name__,
                    'elapsed_seconds': time.monotonic() - started}
        usage = None
        trace = exc.__traceback__
        while trace is not None:
            # Never dump locals, args, environment, stderr, prompts or full
            # tracebacks. These named values are best-effort legacy evidence.
            if trace.tb_frame.f_code is native.run_codex_worker.__code__:
                values = trace.tb_frame.f_locals
                evidence['adapter_line'] = trace.tb_lineno
                candidate = values.get('usage')
                if (isinstance(candidate, dict) and type(candidate.get('total_tokens')) is int
                        and all(type(v) is int and v >= 0 for v in candidate.values())):
                    usage = dict(candidate)
                final = values.get('final')
                if isinstance(final, str):
                    raw = final.encode('utf8', errors='replace')
                    evidence['final_message_sha256'] = sha256(raw).hexdigest()
                    evidence['final_message_bytes'] = len(raw)
            trace = trace.tb_next
        raise ObservedWorkerFailure(evidence, usage=usage) from None
