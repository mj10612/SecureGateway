# Dependency management

`pyproject.toml` publishes compatible ranges for consumers. Upper bounds include
versions already used by the repository; they are not a claim that every version
in a range has been tested. `wordfreq==3.1.1` and
`tree-sitter-language-pack==1.22.1` are intentional pins because frequency and
grammar changes can affect masking or validation.

`uv.lock` records the repository's resolved versions and artifact hashes for
Python 3.10 through 3.14. CI checks it with `uv lock --check` and installs with
`uv sync --locked --all-extras` on the Python/OS test matrix. The grammar job
also installs the separately pinned `lupa==2.8` without dependencies; it is an
independent validator, not part of the project lock. Distribution and native
artifact smoke jobs test independently installed artifacts and their consumer
resolution, not a locked deployment.

## Updating and release review

1. Review the upstream changelog and security advisories for the proposed change,
   including changes to behavioral pins. Change published bounds only as needed.
2. Run `uv lock --upgrade-package PACKAGE`, review the complete lock diff, and
   run `uv lock --check`. Use `uv lock` after changing project constraints.
3. Run `uv sync --locked --all-extras`, the relevant tests, Ruff and mypy. CI
   exercises Ubuntu, Windows and macOS on Python 3.10?3.14, including the `dev`,
   `context`, `context-eval`, and `native-validation` extras. Check the existing
   grammar, offline evaluation and distribution/native artifact jobs before release.
4. Audit the locked dependencies in each target platform/Python environment.
   For example, with `pip-audit` installed separately, export and audit all extras:

   ```sh
   uv export --locked --all-extras --no-emit-project --no-hashes -o /tmp/sg-audit.txt
   pip-audit --no-deps -r /tmp/sg-audit.txt
   ```

   The audit requires access to its advisory service. Investigate every finding,
   including transitive dependencies; upgrade where possible, or document the
   affected use, exposure, mitigation and disposition. Do not suppress findings
   silently. Audit output is specific to the target environment's markers; repeat
   on supported targets. A failed or unavailable scan is not a clean scan.
5. Update the package version, local lock entry, and current-version documentation
   together as required by AGENTS.md. Verify CLI, MCP and package metadata versions,
   and run the existing distribution smoke before tagging.

## Network and offline use

A fresh locked sync needs network access unless all artifacts and build requirements
are already cached. To prepare a wheelhouse on a matching target platform and Python,
export the lock and use pip's download command (the local project is built separately):

```sh
uv export --locked --all-extras --no-emit-project -o /tmp/sg-requirements.txt
python -m pip download -r /tmp/sg-requirements.txt -d /tmp/sg-wheels
uv build --wheel --out-dir /tmp/sg-wheels
```

Transfer the wheelhouse and exported requirements securely. In a fresh environment,
install with `python -m pip install --no-index --find-links=/path/to/sg-wheels -r
/path/to/sg-requirements.txt`, then install the project wheel with `--no-deps`.
Exported hashes verify the locked dependency artifacts. Build dependencies for source
archives, platform-specific wheels, model files and external grammar tools may need
separate preparation; test the complete offline procedure on each target. This does
not guarantee offline availability of optional model downloads.

## Drift detection

`uv lock --check` rejects project metadata changes requiring lock regeneration.
The lock-contract test copies the project metadata and lock to a temporary directory,
changes a constraint there, and checks that drift is rejected without touching the
tracked lock. A clean sync test uses a separate `UV_PROJECT_ENVIRONMENT` and checks
that the package and extras are installed into that environment.
