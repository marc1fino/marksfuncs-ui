"""Versioned JSON workspaces with validation and atomic, explicit saves."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import tempfile

from .catalog import BY_KEY


MAX_FILE_BYTES = 1024 * 1024
MAX_TEXT_LENGTH = 2048
MAX_COMPARISONS = 4


class SessionError(ValueError):
    """The selected workspace is malformed or incompatible."""


def _fields(value, expected: set[str], context: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise SessionError(f"{context}: fields do not match the session format.")
    return value


def _number(value, context: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SessionError(f"{context}: a real number is required.")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise SessionError(f"{context}: the number must be finite.")
    return value


def _function_key(key) -> str:
    if not isinstance(key, str) or key not in BY_KEY:
        raise SessionError("The session contains an unknown function.")
    return key


def _snapshot(key: str, value, *, comparison: bool = False) -> dict:
    fields = {"parameters", "x_range", "points"}
    if comparison:
        fields.add("key")
    snapshot = _fields(value, fields, BY_KEY[key].name)
    parameters = _fields(snapshot["parameters"], set(BY_KEY[key].defaults()), "Parameters")
    normalized_parameters = {}
    for parameter in BY_KEY[key].parameters:
        assigned = parameters[parameter.key]
        if parameter.kind in ("text", "coefficients") or isinstance(parameter.default, str):
            if not isinstance(assigned, str) or not assigned.strip() or len(assigned) > MAX_TEXT_LENGTH:
                raise SessionError(f"{parameter.label}: text must contain 1 to {MAX_TEXT_LENGTH} characters.")
        else:
            assigned = _number(assigned, parameter.label)
            if parameter.integer and not isinstance(assigned, int):
                raise SessionError(f"{parameter.label}: an integer is required.")
            if not parameter.minimum <= assigned <= parameter.maximum:
                raise SessionError(f"{parameter.label}: the value is outside the allowed interval.")
        normalized_parameters[parameter.key] = assigned
    interval = snapshot["x_range"]
    if not isinstance(interval, (tuple, list)) or len(interval) != 2:
        raise SessionError("The interval must contain two bounds.")
    lower, upper = (_number(bound, "Interval") for bound in interval)
    if not -1_000_000 <= lower < upper <= 1_000_000:
        raise SessionError("The interval must be increasing and lie between −1000000 and 1000000.")
    points = snapshot["points"]
    if isinstance(points, bool) or not isinstance(points, int) or not 2 <= points <= 4000:
        raise SessionError("The sample count must be an integer between 2 and 4000.")
    result = {"parameters": normalized_parameters, "x_range": [lower, upper], "points": points}
    if comparison:
        result["key"] = key
    return result


def validate_session(state) -> dict:
    """Return a detached, normalized workspace; never evaluate stored text."""
    state = _fields(state, {"version", "selected", "functions", "comparisons"}, "Session")
    if type(state["version"]) is not int or state["version"] != 1:
        raise SessionError("Incompatible session version. Version 1 is required.")
    selected = _function_key(state["selected"])
    functions = state["functions"]
    if not isinstance(functions, dict):
        raise SessionError("The function collection is invalid.")
    normalized_functions = {
        _function_key(key): _snapshot(key, snapshot)
        for key, snapshot in functions.items()
    }
    comparisons = state["comparisons"]
    if not isinstance(comparisons, list) or len(comparisons) > MAX_COMPARISONS:
        raise SessionError(f"The session supports up to {MAX_COMPARISONS} comparisons.")
    normalized_comparisons = []
    for snapshot in comparisons:
        if not isinstance(snapshot, dict):
            raise SessionError("A comparison has an invalid format.")
        key = _function_key(snapshot.get("key"))
        normalized_comparisons.append(_snapshot(key, snapshot, comparison=True))
    return {
        "version": 1,
        "selected": selected,
        "functions": normalized_functions,
        "comparisons": normalized_comparisons,
    }


def _reject_json_constant(value: str):
    raise SessionError(f"The session contains an invalid JSON value: {value}.")


def load_session(path: str | os.PathLike) -> dict:
    """Read a bounded UTF-8 JSON file and validate before the UI changes."""
    with Path(path).open("rb") as stream:
        payload = stream.read(MAX_FILE_BYTES + 1)
    if len(payload) > MAX_FILE_BYTES:
        raise SessionError("The session exceeds the maximum size of 1 MiB.")
    try:
        state = json.loads(payload.decode("utf-8-sig"), parse_constant=_reject_json_constant)
    except SessionError:
        raise
    except (ValueError, RecursionError) as error:
        raise SessionError("The file does not contain a valid JSON session.") from error
    return validate_session(state)


def save_session(path: str | os.PathLike, state) -> None:
    """Replace the destination only after valid JSON has been safely written."""
    normalized = validate_session(state)
    payload = json.dumps(normalized, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(payload.encode("utf-8")) > MAX_FILE_BYTES:
        raise SessionError("The session exceeds the maximum size of 1 MiB.")
    destination = Path(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", delete=False,
            dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp",
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
