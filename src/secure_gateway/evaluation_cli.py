"""Evaluation commands are opt-in and do not touch installed gateway settings."""
import json
from pathlib import Path
import shutil
import sys

import click


@click.group(invoke_without_command=True)
@click.option('--suite', type=click.Choice(['privacy', 'comprehension']), default='privacy', show_default=True)
@click.option('--profile', type=click.Choice(['smoke', 'standard', 'release']), default='smoke', show_default=True)
@click.option('--output-dir', type=click.Path(path_type=Path))
@click.option('--corpus', 'corpus_path', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--real-llm', is_flag=True, help='Explicitly enable actual fresh LLM subagents; no provider fallback.')
@click.option('--provider', type=click.Choice(['codex', 'external']), default='codex', show_default=True)
@click.option('--model', help='Exact model setting or honest identity label for imported native subagents.')
@click.option('--baseline', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--candidate', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--prepare-only', is_flag=True, help='Export blind interpretation jobs without making LLM calls.')
@click.option('--responses', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--grades', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--worker-command', help='Explicit executable implementing the documented fresh-subagent JSON protocol.')
@click.option('--repeats', type=click.IntRange(1, 10), default=1, show_default=True)
@click.option('--max-calls', type=click.IntRange(0, 10000), default=64, show_default=True)
@click.option('--max-seconds', type=click.FloatRange(0, 86400), default=300, show_default=True)
@click.option('--max-output-tokens', type=click.IntRange(64, 8192), default=1024, show_default=True)
@click.option('--max-tokens', type=click.IntRange(1), default=65536, show_default=True,
              help='Stop subsequent calls at this reported total usage; unknown provider usage is disclosed.')
@click.pass_context
def evaluate(ctx, suite, profile, output_dir, corpus_path, real_llm, provider, model, baseline, candidate,
             prepare_only, responses, grades, worker_command, repeats, max_calls, max_seconds, max_output_tokens, max_tokens):
    """Measure privacy and actual LLM comprehension separately using synthetic tasks."""
    if ctx.invoked_subcommand:
        return
    if suite == 'comprehension' and not real_llm:
        raise click.UsageError('Comprehension requires explicit --real-llm, including native-subagent imports.')
    if output_dir is None:
        raise click.UsageError('--output-dir is required.')
    from secure_gateway.evaluation import load_corpus, run_privacy
    from secure_gateway.evaluation_comprehension import continue_comprehension, prepare_comprehension
    try:
        if suite == 'privacy':
            if real_llm or prepare_only or responses or grades or worker_command:
                raise click.UsageError('LLM options require --suite comprehension.')
            click.echo(f'Privacy profile={profile}; provider calls=0 (loopback fixture only).')
            report = run_privacy(load_corpus(corpus_path), output_dir=output_dir, profile=profile, max_seconds=max_seconds)
        else:
            manifest = output_dir / 'manifest.json'
            if manifest.exists():
                stored = json.loads(manifest.read_text(encoding='utf-8'))['metadata']
                for option, value in [('model', model), ('profile', profile), ('repeats', repeats),
                                      ('max_output_tokens', max_output_tokens)]:
                    if ctx.get_parameter_source(option) == click.core.ParameterSource.COMMANDLINE and stored[option] != value:
                        raise ValueError('Prepared run settings are immutable: ' + option)
                if baseline or candidate or corpus_path:
                    raise ValueError('Prepared run inputs are immutable; use a new output directory.')
            if not manifest.exists():
                if not model:
                    raise click.UsageError('--model is required for a new comprehension run.')
                data = load_corpus(corpus_path)
                if bool(baseline) != bool(candidate):
                    raise click.UsageError('Supply both --baseline and --candidate privacy reports.')
                if baseline:
                    base = json.loads(baseline.read_text(encoding='utf-8'))
                    cand = json.loads(candidate.read_text(encoding='utf-8'))
                else:
                    base = cand = run_privacy(data, output_dir=output_dir / 'privacy', profile=profile, max_seconds=max_seconds)
                state = prepare_comprehension(data, base, cand, output_dir=output_dir, model=model, profile=profile,
                                              repeats=repeats, max_output_tokens=max_output_tokens)
                click.echo(f"Prepared {len(state['jobs'])} blind tasks; at most {2 * len(state['jobs'])} interpretation/grading calls.")
            command = None
            if not prepare_only and not responses and not grades:
                if provider == 'codex' and not worker_command:
                    if not shutil.which('codex'):
                        raise click.ClickException('Codex CLI unavailable; no provider fallback. Use --prepare-only or an explicit worker.')
                    command = [sys.executable, '-m', 'secure_gateway.evaluation_codex_worker']
                elif worker_command:
                    executable = shutil.which(worker_command)
                    if not executable:
                        raise click.UsageError('--worker-command must resolve to an executable.')
                    command = [executable]
                else:
                    raise click.UsageError('External execution needs --worker-command, --prepare-only or saved responses/grades.')
            report = continue_comprehension(output_dir, responses_path=responses, grades_path=grades, command=command,
                                            max_calls=max_calls, max_seconds=max_seconds, max_tokens=max_tokens)
        click.echo(json.dumps({'status': report['status'], 'metrics': report['metrics'], 'report': str(output_dir / 'report.json')},
                              ensure_ascii=False, indent=2))
        if report['status'] != 'completed':
            ctx.exit(2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None


@evaluate.command('compare')
@click.option('--baseline', required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--candidate', required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--output-dir', type=click.Path(path_type=Path))
@click.pass_context
def compare(ctx, baseline, candidate, output_dir):
    """Reject incompatible reports and report new privacy/meaning regressions."""
    from secure_gateway.evaluation import compare_reports, write_json
    try:
        report = compare_reports(json.loads(baseline.read_text(encoding='utf-8')), json.loads(candidate.read_text(encoding='utf-8')))
        if output_dir:
            write_json(output_dir / 'comparison.json', report)
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        if report['regression']:
            ctx.exit(1)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None
