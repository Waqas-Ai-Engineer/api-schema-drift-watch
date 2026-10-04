import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from drift_watch import diff_schemas, infer_schema, merge_schemas

ROOT = Path(__file__).resolve().parent.parent


class SchemaTests(unittest.TestCase):
    def test_infer_nested(self):
        s = infer_schema({"id": 1, "tags": ["a"], "owner": {"name": "x"}})
        self.assertEqual(s["fields"]["id"]["types"], ["integer"])
        self.assertEqual(s["fields"]["tags"]["items"]["types"], ["string"])
        self.assertEqual(s["fields"]["owner"]["fields"]["name"]["types"], ["string"])

    def test_merge_marks_optional(self):
        m = merge_schemas(infer_schema({"a": 1, "b": 2}), infer_schema({"a": 1}))
        self.assertTrue(m["fields"]["b"].get("optional"))
        self.assertFalse(m["fields"]["a"].get("optional"))

    def test_merge_unions_types(self):
        m = merge_schemas(infer_schema({"a": 1}), infer_schema({"a": None}))
        self.assertEqual(m["fields"]["a"]["types"], ["integer", "null"])


class DiffTests(unittest.TestCase):
    def kinds(self, old, new):
        return {(c.path, c.kind, c.severity) for c in diff_schemas(infer_schema(old), infer_schema(new))}

    def test_no_change(self):
        self.assertEqual(self.kinds({"a": 1}, {"a": 2}), set())

    def test_removed_is_breaking(self):
        self.assertIn(("$.a", "removed", "breaking"), self.kinds({"a": 1, "b": 1}, {"b": 1}))

    def test_added_is_info(self):
        self.assertIn(("$.c", "added", "info"), self.kinds({"a": 1}, {"a": 1, "c": 2}))

    def test_type_change_breaking(self):
        self.assertIn(("$.a", "type_changed", "breaking"), self.kinds({"a": 1}, {"a": "1"}))

    def test_null_widening_is_warning(self):
        old = infer_schema({"a": 1})
        new = merge_schemas(infer_schema({"a": 1}), infer_schema({"a": None}))
        self.assertIn(("$.a", "type_changed", "warning"),
                      {(c.path, c.kind, c.severity) for c in diff_schemas(old, new)})

    def test_array_items_nested(self):
        k = self.kinds({"rows": [{"id": 1, "x": 1}]}, {"rows": [{"id": 1}]})
        self.assertIn(("$.rows[].x", "removed", "breaking"), k)

    def test_removed_optional_is_warning(self):
        old = merge_schemas(infer_schema({"a": 1, "b": 1}), infer_schema({"a": 1}))
        new = infer_schema({"a": 1})
        self.assertIn(("$.b", "removed", "warning"),
                      {(c.path, c.kind, c.severity) for c in diff_schemas(old, new)})


class CliTests(unittest.TestCase):
    def run_cli(self, *a):
        return subprocess.run([sys.executable, "-m", "drift_watch", *a], cwd=ROOT,
                              capture_output=True, text=True)

    def test_snapshot_then_check_breaking_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            v1, v2 = Path(d, "v1.json"), Path(d, "v2.json")
            v1.write_text(json.dumps({"id": 1, "email": "a@b.c"}))
            v2.write_text(json.dumps({"id": "1"}))
            store = str(Path(d, "store"))
            self.assertEqual(self.run_cli("snapshot", str(v1), "--name", "t", "--store", store).returncode, 0)
            ok = self.run_cli("check", str(v1), "--name", "t", "--store", store)
            self.assertEqual(ok.returncode, 0)
            bad = self.run_cli("check", str(v2), "--name", "t", "--store", store)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("BREAKING", bad.stdout)
            never = self.run_cli("check", str(v2), "--name", "t", "--store", store, "--fail-on", "never")
            self.assertEqual(never.returncode, 0)

    def test_missing_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d, "x.json"); f.write_text("{}")
            self.assertEqual(self.run_cli("check", str(f), "--store", d).returncode, 3)


if __name__ == "__main__":
    unittest.main()
