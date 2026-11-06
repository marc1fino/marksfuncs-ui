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
        raise SessionError(f"{context}: los campos no corresponden al formato de sesión.")
    return value


def _number(value, context: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SessionError(f"{context}: se necesita un número real.")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise SessionError(f"{context}: el número debe ser finito.")
    return value


def _function_key(key) -> str:
    if not isinstance(key, str) or key not in BY_KEY:
        raise SessionError("La sesión contiene una función desconocida.")
    return key


def _snapshot(key: str, value, *, comparison: bool = False) -> dict:
    fields = {"parameters", "x_range", "points"}
    if comparison:
        fields.add("key")
    snapshot = _fields(value, fields, BY_KEY[key].name)
    parameters = _fields(snapshot["parameters"], set(BY_KEY[key].defaults()), "Parámetros")
    normalized_parameters = {}
    for parameter in BY_KEY[key].parameters:
        assigned = parameters[parameter.key]
        if parameter.kind in ("text", "coefficients") or isinstance(parameter.default, str):
            if not isinstance(assigned, str) or not assigned.strip() or len(assigned) > MAX_TEXT_LENGTH:
                raise SessionError(f"{parameter.label}: el texto debe tener entre 1 y {MAX_TEXT_LENGTH} caracteres.")
        else:
            assigned = _number(assigned, parameter.label)
            if parameter.integer and not isinstance(assigned, int):
                raise SessionError(f"{parameter.label}: se necesita un número entero.")
            if not parameter.minimum <= assigned <= parameter.maximum:
                raise SessionError(f"{parameter.label}: el valor está fuera del intervalo permitido.")
        normalized_parameters[parameter.key] = assigned
    interval = snapshot["x_range"]
    if not isinstance(interval, (tuple, list)) or len(interval) != 2:
        raise SessionError("El intervalo debe contener dos límites.")
    lower, upper = (_number(bound, "Intervalo") for bound in interval)
    if not -1_000_000 <= lower < upper <= 1_000_000:
        raise SessionError("El intervalo debe ser creciente y estar entre −1000000 y 1000000.")
    points = snapshot["points"]
    if isinstance(points, bool) or not isinstance(points, int) or not 2 <= points <= 4000:
        raise SessionError("El muestreo debe ser un entero entre 2 y 4000.")
    result = {"parameters": normalized_parameters, "x_range": [lower, upper], "points": points}
    if comparison:
        result["key"] = key
    return result


def validate_session(state) -> dict:
    """Return a detached, normalized workspace; never evaluate stored text."""
    state = _fields(state, {"version", "selected", "functions", "comparisons"}, "Sesión")
    if type(state["version"]) is not int or state["version"] != 1:
        raise SessionError("Versión de sesión incompatible. Se necesita la versión 1.")
    selected = _function_key(state["selected"])
    functions = state["functions"]
    if not isinstance(functions, dict):
        raise SessionError("La colección de funciones no es válida.")
    normalized_functions = {
        _function_key(key): _snapshot(key, snapshot)
        for key, snapshot in functions.items()
    }
    comparisons = state["comparisons"]
    if not isinstance(comparisons, list) or len(comparisons) > MAX_COMPARISONS:
        raise SessionError(f"La sesión admite hasta {MAX_COMPARISONS} comparaciones.")
    normalized_comparisons = []
    for snapshot in comparisons:
        if not isinstance(snapshot, dict):
            raise SessionError("Una comparación no tiene el formato correcto.")
        key = _function_key(snapshot.get("key"))
        normalized_comparisons.append(_snapshot(key, snapshot, comparison=True))
    return {
        "version": 1,
        "selected": selected,
        "functions": normalized_functions,
        "comparisons": normalized_comparisons,
    }


def _reject_json_constant(value: str):
    raise SessionError(f"La sesión contiene un valor JSON no válido: {value}.")


def load_session(path: str | os.PathLike) -> dict:
    """Read a bounded UTF-8 JSON file and validate before the UI changes."""
    with Path(path).open("rb") as stream:
        payload = stream.read(MAX_FILE_BYTES + 1)
    if len(payload) > MAX_FILE_BYTES:
        raise SessionError("La sesión supera el tamaño máximo de 1 MiB.")
    try:
        state = json.loads(payload.decode("utf-8-sig"), parse_constant=_reject_json_constant)
    except SessionError:
        raise
    except (ValueError, RecursionError) as error:
        raise SessionError("El archivo no contiene una sesión JSON válida.") from error
    return validate_session(state)


def save_session(path: str | os.PathLike, state) -> None:
    """Replace the destination only after valid JSON has been safely written."""
    normalized = validate_session(state)
    payload = json.dumps(normalized, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(payload.encode("utf-8")) > MAX_FILE_BYTES:
        raise SessionError("La sesión supera el tamaño máximo de 1 MiB.")
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
