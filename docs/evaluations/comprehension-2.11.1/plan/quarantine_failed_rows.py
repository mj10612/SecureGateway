"""Move non-completed rows out of first-responses.jsonl without touching completed rows.

Each failed row's stored status is re-verified before it is moved. Completed rows are
copied as their original raw JSONL lines so their bytes stay identical.
"""
import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path('docs/evaluations/comprehension-2.11.1')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    args = p.parse_args()
    run = ROOT / args.run_dir
    src = run / 'first-responses.jsonl'
    lines = [ln for ln in src.read_text(encoding='utf-8').splitlines() if ln.strip()]
    kept, moved = [], []
    for ln in lines:
        row = json.loads(ln)
        status = row.get('status')
        if status == 'completed':
            kept.append(ln)
        elif status in ('failed', 'ungraded'):
            moved.append(ln)
        else:
            raise ValueError('UnexpectedRowStatus')
    if not moved:
        print('no failed rows; nothing to quarantine')
        return 0
    before = len(lines)
    qpath = run / 'failed-responses-quarantined.jsonl'
    with qpath.open('a', encoding='utf-8', newline='\n') as f:
        for ln in moved:
            f.write(ln + '\n')
        f.flush()
        os.fsync(f.fileno())
    tmp = src.with_suffix('.jsonl.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        for ln in kept:
            f.write(ln + '\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, src)
    # Re-read to prove every remaining row is completed and counts add up.
    after = [json.loads(ln) for ln in src.read_text(encoding='utf-8').splitlines() if ln.strip()]
    if any(r.get('status') != 'completed' for r in after):
        raise ValueError('QuarantineIncomplete')
    if len(after) + len(moved) != before:
        raise ValueError('RowCountMismatch')
    print('quarantined', len(moved), 'rows; remaining', len(after), 'of', before,
          'at', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    for ln in moved:
        row = json.loads(ln)
        print('  moved', row['case_id'], row['arm'], row.get('error_category'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
