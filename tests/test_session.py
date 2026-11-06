"""Workspace compatibility, validation, and existing-file protection."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from marksfuncs_ui.catalog import BY_KEY
from marksfuncs_ui.session import (
    MAX_FILE_BYTES, SessionError, load_session, save_session, validate_session,
)


def workspace():
    spec = BY_KEY["Quadratic"]
    values = spec.defaults()
    values["a"] = 1.23456789
    snapshot = {"parameters": values, "x_range": [-4.5, 7.25], "points": 801}
    return {
        "version": 1, "selected": spec.key,
        "functions": {spec.key: snapshot},
        "comparisons": [{"key": spec.key, **deepcopy(snapshot)}],
    }


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "workspace.json"

    def test_roundtrip_preserves_values_and_comparisons(self):
        state = workspace()
        save_session(self.path, state)
        self.assertEqual(load_session(self.path), state)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.path])

    def test_validation_does_not_share_mutable_data(self):
        state = workspace()
        validated = validate_session(state)
        validated["functions"]["Quadratic"]["parameters"]["a"] = 2
        self.assertEqual(state["functions"]["Quadratic"]["parameters"]["a"], 1.23456789)

    def test_invalid_save_keeps_existing_workspace(self):
        save_session(self.path, workspace())
        original = self.path.read_bytes()
        invalid = workspace()
        invalid["version"] = 99
        with self.assertRaises(SessionError):
            save_session(self.path, invalid)
        self.assertEqual(self.path.read_bytes(), original)

    def test_failed_replacement_keeps_file_and_removes_temporary(self):
        save_session(self.path, workspace())
        original = self.path.read_bytes()
        with patch("marksfuncs_ui.session.os.replace", side_effect=PermissionError("busy")):
            with self.assertRaises(PermissionError):
                save_session(self.path, workspace())
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.path])

    def test_rejects_unknown_version_and_functions(self):
        for field, value in (("version", True), ("version", 2), ("selected", "__import__")):
            with self.subTest(field=field, value=value):
                state = workspace()
                state[field] = value
                with self.assertRaises(SessionError):
                    validate_session(state)
        state = workspace()
        state["functions"]["unknown"] = state["functions"].pop("Quadratic")
        with self.assertRaises(SessionError):
            validate_session(state)

    def test_rejects_invalid_or_nonfinite_numeric_parameters(self):
        for value in (True, float("nan"), float("inf"), "1", [], 100, 10**1000):
            with self.subTest(value=repr(value)[:30]):
                state = workspace()
                state["functions"]["Quadratic"]["parameters"]["a"] = value
                with self.assertRaises(SessionError):
                    validate_session(state)

    def test_rejects_missing_parameters_and_unknown_fields(self):
        state = workspace()
        del state["functions"]["Quadratic"]["parameters"]["a"]
        with self.assertRaises(SessionError):
            validate_session(state)
        state = workspace()
        state["execute"] = "print('unsafe')"
        with self.assertRaises(SessionError):
            validate_session(state)

    def test_validates_interval_points_and_comparison_limit(self):
        for field, value in (("x_range", [5, 2]), ("x_range", [False, 5]),
                             ("x_range", [0, float("inf")]), ("points", True),
                             ("points", 4001), ("points", 20.5)):
            with self.subTest(field=field, value=value):
                state = workspace()
                state["functions"]["Quadratic"][field] = value
                with self.assertRaises(SessionError):
                    validate_session(state)
        state = workspace()
        state["comparisons"] *= 5
        with self.assertRaises(SessionError):
            validate_session(state)

    def test_supports_discrete_sampling_and_text_without_evaluation(self):
        state = {"version": 1, "selected": "Poisson", "functions": {}, "comparisons": []}
        for key in ("Poisson", "ExpressionFunction"):
            spec = BY_KEY[key]
            state["functions"][key] = {
                "parameters": spec.defaults(), "x_range": spec.x_range, "points": spec.points,
            }
        state["functions"]["ExpressionFunction"]["parameters"]["expression"] = "sin(x) + cos(2*x)"
        save_session(self.path, state)
        loaded = load_session(self.path)
        self.assertEqual(loaded["functions"]["Poisson"]["points"], 16)
        self.assertEqual(loaded["functions"]["ExpressionFunction"]["parameters"]["expression"], "sin(x) + cos(2*x)")

    def test_rejects_oversize_invalid_json_and_nan_json(self):
        for payload in (b"x" * (MAX_FILE_BYTES + 1), b"not json", b'{"version": NaN}',
                        b'{"version":' + b"9" * 5000 + b"}"):
            self.path.write_bytes(payload)
            with self.assertRaises(SessionError):
                load_session(self.path)

    def test_integer_parameters_and_text_lengths_are_checked(self):
        state = {"version": 1, "selected": "Legendre", "functions": {}, "comparisons": []}
        for key in ("Legendre", "ExpressionFunction"):
            spec = BY_KEY[key]
            state["functions"][key] = {
                "parameters": spec.defaults(), "x_range": spec.x_range, "points": spec.points,
            }
        state["functions"]["Legendre"]["parameters"]["grade"] = 2.5
        with self.assertRaises(SessionError):
            validate_session(state)
        state["functions"]["Legendre"]["parameters"]["grade"] = 2
        state["functions"]["ExpressionFunction"]["parameters"]["expression"] = "x" * 2049
        with self.assertRaises(SessionError):
            validate_session(state)


if __name__ == "__main__":
    unittest.main()
