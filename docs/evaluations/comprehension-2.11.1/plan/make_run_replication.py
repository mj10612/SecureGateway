"""Create plan-scoped runner copies from the frozen base harness.

The base run_comprehension.py keeps its original path constants so earlier run
identities stay valid; this script produces a byte-controlled variant that reads
a named plan directory and writes a separate run directory.
"""
import pathlib, sys

src = pathlib.Path('docs/evaluations/comprehension-2.11.1/plan/run_comprehension.py')
dst = pathlib.Path('docs/evaluations/comprehension-2.11.1/plan/run_replication.py')
text = src.read_text(encoding='utf-8')

old_header = "ROOT=Path('docs/evaluations/comprehension-2.11.1');MODEL='gpt-6.1-sol'"
new_header = ("ROOT=Path('docs/evaluations/comprehension-2.11.1');PLAN='plan-replication';OUT='comprehension-replication';"
              "MODEL='gpt-6.1-sol'")
assert text.count(old_header) == 1
text = text.replace(old_header, new_header)

for old, new, expected in [
    ("ROOT/str(issue)/'plan/cases.json'", "ROOT/str(issue)/PLAN/'cases.json'", 1),
    ("ROOT/str(issue)/'plan/rubric.json'", "ROOT/str(issue)/PLAN/'rubric.json'", 1),
    ("ROOT/str(issue)/'plan').glob('*.json')", "ROOT/str(issue)/PLAN).glob('*.json')", 1),
    ("shutil.copyfile(ROOT/str(issue)/'plan'/name", "shutil.copyfile(ROOT/str(issue)/PLAN/name", 1),
    ("pf=json.loads((ROOT/str(m['issue'])/'plan'/pfname)", "pf=json.loads((ROOT/str(m['issue'])/PLAN/pfname)", 1),
]:
    assert text.count(old) == expected, (old, text.count(old))
    text = text.replace(old, new)

old_path = "def path_for(issue):return ROOT/str(issue)/('comprehension-policy' if issue==317 else 'comprehension')"
new_path = "def path_for(issue):return ROOT/str(issue)/OUT"
assert text.count(old_path) == 1
text = text.replace(old_path, new_path)

dst.write_text(text, encoding='utf-8')
print('wrote', dst)
