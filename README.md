# api-schema-drift-watch

[![CI](https://github.com/Waqas-Ai-Engineer/api-schema-drift-watch/actions/workflows/ci.yml/badge.svg)](https://github.com/Waqas-Ai-Engineer/api-schema-drift-watch/actions)
![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

**Catch breaking changes in third-party JSON APIs before your automations break.**

n8n workflows, Zapier zaps, ETL jobs and AI agents all quietly depend on the *shape* of API responses. When a vendor renames a field, turns an integer into a string or starts returning `null`, your pipeline fails at 3 a.m. `drift-watch` records a structural baseline of an endpoint and tells you, with severity levels and CI-friendly exit codes, exactly what changed.

- Zero dependencies, pure Python standard library
- Works on live URLs (with auth headers) or saved JSON files
- Merges multiple samples into one baseline so optional fields are not false alarms
- Classifies changes as `breaking`, `warning` or `info`
- Text, JSON and Markdown reports; exit code 1 for CI gating

## Quick start

```bash
git clone https://github.com/Waqas-Ai-Engineer/api-schema-drift-watch
cd api-schema-drift-watch

# 1. save a baseline (merge several samples for better optional-field detection)
python -m drift_watch snapshot examples/users_v1.json --name users

# 2. later, check the live endpoint or a new payload
python -m drift_watch check examples/users_v2.json --name users
```

Output:

```
[users] 3 breaking, 0 warning, 1 info
  BREAKING $.data[].email  removed: field no longer present
  BREAKING $.data[].id  type_changed: integer -> string
  BREAKING $.data[].plan  type_changed: string -> null
  INFO     $.data[].avatar_url  added: new field (string)
```

Install as a command with `pip install .` and use `drift-watch` instead of `python -m drift_watch`.

## Commands

| Command | Purpose |
|---|---|
| `snapshot SOURCE...` | Infer and store a baseline in `.drift-watch/` |
| `check SOURCE...` | Compare current response to the baseline |
| `list` | Show stored baselines |

Useful flags: `--name`, `--store DIR`, `--header "Authorization: Bearer TOKEN"`, `--format text|json|markdown`, `--fail-on breaking|warning|never`, `--update` (accept the new shape as the baseline).

Exit codes: `0` ok, `1` drift at or above `--fail-on`, `3` could not load source or baseline.

## Severity rules

| Change | Severity |
|---|---|
| Field removed | breaking (warning if it was already optional) |
| Type changed (e.g. integer to string) | breaking |
| Type widened to include `null` | warning |
| Field became optional | warning |
| New field added | info |

## Use it in CI or n8n

A nightly GitHub Actions example lives in `.github/workflows/drift-check.example.yml`. In n8n, run `drift-watch check URL --format json --fail-on never` from an Execute Command node and branch on `summary.breaking` to alert Slack or email.

## How it works

`drift_watch/schema.py` infers a compact schema tree (types, fields, array item shape). `merge_schemas` unions samples. `drift_watch/diff.py` walks two trees and emits typed `Change` records. Reports are rendered by `drift_watch/report.py`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Roadmap

- Format and enum detection (dates, UUIDs, closed value sets)
- Slack and webhook notifier
- OpenAPI export of the inferred schema

## License

MIT, see [LICENSE](LICENSE).
