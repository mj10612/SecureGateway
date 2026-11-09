"""Explicit commands for frozen #324 cohorts, never implicit provider calls."""
import json
from pathlib import Path

import click


@click.group('reliable')
def reliable():
    """Validate, freeze and measure independent multilingual privacy/task cohorts."""


@reliable.command('validate')
@click.option('--data-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def validate(data_dir):
    """Report schema/offset/family counts and hashes without revealing holdout text."""
    from secure_gateway.evaluation_reliable import load_bundle
    try:
        result = load_bundle(data_dir)
        click.echo(json.dumps({'hashes': result['hashes'], 'coverage': result['summaries']}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None


@reliable.command('prepare')
@click.option('--data-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--output-dir', required=True, type=click.Path(path_type=Path))
@click.option('--split', type=click.Choice(['development', 'holdout']), default='holdout', show_default=True)
@click.option('--model', default='gpt-6.1-sol', show_default=True)
@click.option('--repeats', type=click.IntRange(3, 10), default=3, show_default=True)
@click.option('--reasoning-effort', type=click.Choice(['low', 'medium', 'high', 'xhigh']), default='medium', show_default=True)
@click.option('--max-output-tokens', type=click.IntRange(64, 8192), default=2048, show_default=True)
@click.option('--baseline-dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--reference-audit-dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--holdout-ledger', type=click.Path(dir_okay=False, path_type=Path), help='Append-only record of holdout uses.')
@click.option('--holdout-reuse-reason', help='Record reuse for diagnosis; reused candidates remain ineligible for adoption review.')
@click.option('--max-seconds', type=click.FloatRange(min=1), default=1200, show_default=True)
def prepare(**options):
    """Capture loopback payloads and freeze blind jobs; makes no model calls."""
    from secure_gateway.evaluation_reliable import prepare_reliable
    try:
        result = prepare_reliable(**options)
        click.echo(json.dumps({'status': result['status'], 'output': str(options['output_dir'])}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None


@reliable.command('run')
@click.option('--output-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--execute', is_flag=True, help='Explicitly authorize real fresh model calls.')
@click.option('--max-calls', type=click.IntRange(1), default=306, show_default=True)
@click.option('--max-seconds', type=click.FloatRange(min=1), default=7200, show_default=True)
@click.option('--max-tokens', type=click.IntRange(1), default=12000000, show_default=True)
@click.option('--workers', type=click.IntRange(1, 3), default=3, show_default=True)
@click.pass_context
def run(ctx, **options):
    """Persist actual first answers, then independently grade them."""
    from secure_gateway.evaluation_reliable import execute_reliable
    try:
        result = execute_reliable(**options)
        click.echo(json.dumps({'status': result['status'], 'adoption': result['adoption']}, indent=2))
        if result['status'] != 'completed':
            ctx.exit(2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None


@reliable.command('report')
@click.option('--output-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def report(output_dir):
    """Join privacy, repeats, whole-task results and holdout review status."""
    from secure_gateway.evaluation_reliable import joint_report
    try:
        result = joint_report(output_dir)
        click.echo(json.dumps({'status': result['status'], 'adoption': result['adoption']}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None


@reliable.command('audit-references')
@click.option('--data-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--output-dir', required=True, type=click.Path(path_type=Path))
@click.option('--split', type=click.Choice(['development', 'holdout']), default='holdout', show_default=True)
@click.option('--model', default='gpt-6.1-sol', show_default=True)
@click.option('--reasoning-effort', type=click.Choice(['low', 'medium', 'high', 'xhigh']), default='medium', show_default=True)
@click.option('--execute', is_flag=True)
@click.option('--max-calls', type=click.IntRange(1), default=17, show_default=True)
@click.option('--max-seconds', type=click.FloatRange(min=1), default=900, show_default=True)
@click.option('--max-tokens', type=click.IntRange(1), default=600000, show_default=True)
@click.pass_context
def audit_references(ctx, **options):
    """Independently check whether owner references can attain all 68 rubric points."""
    from secure_gateway.evaluation_reliable import audit_references as run_audit
    try:
        result = run_audit(**options)
        click.echo(json.dumps(result, indent=2))
        if options['execute'] and result['status'] != 'passed':
            ctx.exit(2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None


from secure_gateway.evaluation_supplemental_cli import supplement_grades  # noqa: E402

reliable.add_command(supplement_grades)
