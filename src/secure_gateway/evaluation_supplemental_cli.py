"""`evaluate reliable supplement-grades`: grade-only completion of a stopped run."""
import json
from pathlib import Path

import click


def _emit(ctx, report):
    click.echo(json.dumps({k: report[k] for k in ('primary_status', 'supplemental_status', 'combined_status',
                                                  'grade_sources', 'tokens', 'verification_problems')},
                          indent=2, ensure_ascii=False))
    if report['combined_status'] != 'completed_with_supplement' or report['verification_problems']:
        ctx.exit(2)


@click.group('supplement-grades')
def supplement_grades():
    """Freeze, run and report missing grades of saved first answers; never re-interprets."""


@supplement_grades.command('prepare')
@click.option('--parent-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--output-dir', required=True, type=click.Path(path_type=Path))
@click.option('--reattempt-job-id', 'reattempt_job_ids', multiple=True,
              help='Failed parent grade job to grade again; repeatable, requires --reattempt-reason.')
@click.option('--reattempt-reason', help='Recorded before any call; required with --reattempt-job-id.')
def prepare(parent_dir, output_dir, reattempt_job_ids, reattempt_reason):
    """Pin parent evidence and exact grade requests; makes no model calls."""
    from secure_gateway.evaluation_supplemental import prepare_supplemental
    try:
        frozen = prepare_supplemental(parent_dir, output_dir, reattempt_job_ids=reattempt_job_ids,
                                      reattempt_reason=reattempt_reason)
        click.echo(json.dumps({'status': 'prepared', 'scheduled': len(frozen['scheduled']),
                               'reattempt': frozen['reattempt'], 'output': str(output_dir)}, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None


@supplement_grades.command('run')
@click.option('--output-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--execute', is_flag=True, help='Explicitly authorize real fresh grading calls.')
@click.option('--max-calls', type=click.IntRange(1), default=124, show_default=True)
@click.option('--max-seconds', type=click.FloatRange(min=1), default=3600, show_default=True)
@click.option('--max-tokens', type=click.IntRange(1), default=4_000_000, show_default=True)
@click.option('--workers', type=click.IntRange(1, 3), default=3, show_default=True)
@click.pass_context
def run(ctx, **options):
    """Grade only the frozen schedule with an independent immutable budget."""
    from secure_gateway.evaluation_supplemental import execute_supplemental
    try:
        report = execute_supplemental(**options)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None
    _emit(ctx, report)


@supplement_grades.command('report')
@click.option('--output-dir', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def report(ctx, output_dir):
    """Combined report; the parent run remains incomplete."""
    from secure_gateway.evaluation_supplemental import supplemental_report
    try:
        result = supplemental_report(output_dir)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise click.ClickException(str(exc)) from None
    _emit(ctx, result)
