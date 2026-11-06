"""Obtain plotted samples from marksfuncs, without duplicating its formulas.

The library's pyplot API is captured on the caller's thread. Call this on the Qt
main thread: Matplotlib global state is not safe for concurrent calculations.
"""

import ast
from dataclasses import dataclass
import inspect
import keyword
import math
import operator
import re
import warnings as python_warnings
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
from matplotlib.container import StemContainer
import numpy as np

from .catalog import BY_KEY, FunctionSpec


class CalculationError(ValueError):
    """A validation error or an unchanged failure from the installed library."""


@dataclass(frozen=True)
class SeriesData:
    x: np.ndarray
    y: np.ndarray
    label: str
    scatter: bool = False
    colors: np.ndarray | None = None


@dataclass(frozen=True)
class CurveData:
    series: tuple[SeriesData, ...]
    class_name: str
    warnings: tuple[str, ...] = ()

    @property
    def x(self):
        return self.series[0].x

    @property
    def y(self):
        return self.series[0].y

    @property
    def label(self):
        return self.series[0].label

    @property
    def scatter(self):
        return self.series[0].scatter


_FUNCTIONS = {
    "sin", "cos", "tan", "arcsin", "arccos", "arctan", "arctan2", "sinh", "cosh",
    "tanh", "arcsinh", "arccosh", "arctanh", "exp", "expm1", "log", "log10",
    "log1p", "log2", "sqrt", "cbrt", "square", "abs", "fabs", "floor", "ceil",
    "trunc", "round", "sign", "heaviside", "maximum", "minimum", "clip", "power",
    "mod", "fmod", "deg2rad", "rad2deg", "erf", "erfc", "gamma", "gammaln",
    "beta", "betaln", "j0", "j1", "jn", "yn", "sinc",
}
_CONSTANTS = {"x", "pi", "e"}
_AST_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
    ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.UAdd, ast.USub,
)


def validate_expression(expression: str) -> str:
    """Restrict upstream eval to small numeric expressions with no object access."""
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 1000:
        raise CalculationError("Escribe una expresión matemática de 1 a 1000 caracteres.")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, RecursionError) as error:
        raise CalculationError("Expresión no válida. Usa ** para potencias, por ejemplo x**2.") from error
    nodes = list(ast.walk(tree))
    if len(nodes) > 160:
        raise CalculationError("La expresión es demasiado compleja; simplifica sus operaciones.")
    for node in nodes:
        if not isinstance(node, _AST_NODES):
            raise CalculationError("Solo se admiten números, x, constantes y funciones matemáticas.")
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float) or abs(node.value) > 1e12 or not math.isfinite(float(node.value)):
                raise CalculationError("Las constantes deben ser números finitos de magnitud ≤ 10¹².")
        if isinstance(node, ast.Name) and node.id not in _FUNCTIONS | _CONSTANTS:
            raise CalculationError(f"Nombre no permitido: {node.id}.")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS or node.keywords or not 1 <= len(node.args) <= 3:
                raise CalculationError("Utiliza una función matemática conocida con uno a tres argumentos.")
            if node.func.id == "power" and len(node.args) == 2:
                _validate_exponent(node.args[1])
            if node.func.id in {"jn", "yn"}:
                if not isinstance(node.args[0], ast.Constant) or abs(node.args[0].value) > 32:
                    raise CalculationError("El orden de Bessel debe ser una constante entre −32 y 32.")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            _validate_exponent(node.right)
        if isinstance(node, ast.BinOp):
            _bounded_scalar(node)
    return expression.strip()


_SCALAR_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: math.pow,
}


def _bounded_scalar(node):
    """Bound literal arithmetic before upstream eval can create giant integers.

    Floating point probes never evaluate names, calls or user-provided code.
    Every constant-only intermediate must stay finite and within 10**12.
    """
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        if abs(node.value) > 1e12:
            raise CalculationError("Las constantes deben tener magnitud ≤ 10¹².")
        return float(node.value)
    if isinstance(node, ast.UnaryOp):
        value = _bounded_scalar(node.operand)
        return None if value is None else (-value if isinstance(node.op, ast.USub) else value)
    if not isinstance(node, ast.BinOp):
        return None
    left, right = _bounded_scalar(node.left), _bounded_scalar(node.right)
    if left is None or right is None:
        return None
    try:
        result = _SCALAR_OPERATORS[type(node.op)](left, right)
    except (ArithmeticError, ValueError) as error:
        raise CalculationError("Hay una operación constante indefinida o demasiado grande.") from error
    if not math.isfinite(result) or abs(result) > 1e12:
        raise CalculationError("Cada operación constante debe producir un valor finito de magnitud ≤ 10¹².")
    return result


def _validate_exponent(node):
    # Constant power towers create giant Python integers before NumPy sees them.
    if any(isinstance(child, ast.Name) and child.id == "x" for child in ast.walk(node)):
        return
    literal = node
    if isinstance(literal, ast.UnaryOp) and isinstance(literal.op, (ast.USub, ast.UAdd)):
        literal = literal.operand
    if not isinstance(literal, ast.Constant) or type(literal.value) not in (int, float) or abs(literal.value) > 32:
        raise CalculationError("Usa exponentes constantes entre −32 y 32, o una expresión que dependa de x.")


def _coefficients(value):
    if isinstance(value, str):
        if len(value) > 2000:
            raise CalculationError("La lista de coeficientes es demasiado larga.")
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError, RecursionError) as error:
            raise CalculationError("Usa una lista [1, 2, 3] o un diccionario {0: 1, 2: 3}.") from error
    if not isinstance(value, (list, dict)) or not value or len(value) > 21:
        raise CalculationError("Introduce entre 1 y 21 coeficientes.")
    items = enumerate(value) if isinstance(value, list) else value.items()
    for degree, coefficient in items:
        if type(degree) is not int or not 0 <= degree <= 20:
            raise CalculationError("Los grados deben ser enteros de 0 a 20.")
        if type(coefficient) not in (int, float) or abs(coefficient) > 1e9 or not math.isfinite(coefficient):
            raise CalculationError("Cada coeficiente debe ser finito y de magnitud ≤ 10⁹.")
    return value


def resolve_spec(spec_or_key: FunctionSpec | str) -> FunctionSpec:
    try:
        return BY_KEY[spec_or_key] if isinstance(spec_or_key, str) else BY_KEY[spec_or_key.key]
    except KeyError as error:
        raise CalculationError("Esta función no está en el catálogo.") from error


def constructor_arguments(spec_or_key, parameters=None, x_range=None, points=None):
    """Validate input and return exactly the arguments supplied to marksfuncs."""
    spec = resolve_spec(spec_or_key)
    values = spec.defaults()
    if parameters:
        if set(parameters) - set(values):
            raise CalculationError("Se han recibido parámetros desconocidos.")
        values.update(parameters)
    for parameter in spec.parameters:
        value = values[parameter.key]
        if parameter.kind == "coefficients":
            values[parameter.key] = _coefficients(value)
        elif parameter.kind == "text":
            if parameter.key == "expression":
                values[parameter.key] = validate_expression(value)
            else:
                if not isinstance(value, str) or not value.strip() or len(value) > 300 or not re.fullmatch(r"[\s+\-0-9x^]+", value):
                    raise CalculationError("Usa términos enteros como 2x^3 - x + 1.")
                degrees = re.findall(r"\^(\d+)", value)
                if any(int(degree) > 20 for degree in degrees):
                    raise CalculationError("El grado máximo permitido es 20.")
        else:
            if type(value) not in (int, float):
                raise CalculationError(f"{parameter.label} debe ser un número finito.")
            if not parameter.minimum <= value <= parameter.maximum or not math.isfinite(value):
                raise CalculationError(f"{parameter.label}: usa un valor entre {parameter.minimum:g} y {parameter.maximum:g}.")
            if parameter.integer:
                if int(value) != value:
                    raise CalculationError(f"{parameter.label} debe ser entero.")
                values[parameter.key] = int(value)
    bounds = spec.x_range if x_range is None else x_range
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise CalculationError("El intervalo debe contener inicio y final.")
    if any(type(value) not in (int, float) or abs(value) > 1e6 or not math.isfinite(value) for value in bounds) or bounds[0] >= bounds[1]:
        raise CalculationError("El inicio debe ser menor que el final; los límites deben ser finitos y de magnitud ≤ 10⁶.")
    count = spec.points if points is None else points
    if type(count) not in (int, float) or not 2 <= count <= 4000 or not math.isfinite(count) or int(count) != count:
        raise CalculationError("El número de muestras debe ser un entero de 2 a 4000.")
    if spec.key == "TopHat" and values["a"] >= values["b"]:
        raise CalculationError("El inicio del pulso debe ser menor que su final.")
    if spec.key == "ModifiedAckermann" and not (0 <= bounds[0] < bounds[1] <= 20):
        raise CalculationError("Ackermann modificada requiere un intervalo x entre 0 y 20 para limitar su crecimiento.")
    values["x_values_list"] = [bounds[0], bounds[1], int(count)]
    return values


def _library_class(key):
    import marksfuncs.functions as library
    candidate = getattr(library, key, None)
    if not inspect.isclass(candidate):
        raise CalculationError(f"La instalación de marksfuncs no incluye {key}. Actualiza marksfuncs y reinicia la aplicación.")
    if not callable(getattr(candidate, "graph", None)):
        raise CalculationError(f"marksfuncs declara {key}, pero esta versión no implementa graph(). La explicación está disponible; el cálculo necesita una implementación en la librería.")
    return candidate


def unavailable_reason(spec_or_key):
    """Return a useful explanation when the installed upstream class is incomplete."""
    try:
        _library_class(resolve_spec(spec_or_key).key)
    except CalculationError as error:
        return str(error)
    return ""


def compute_curve(spec_or_key, parameters=None, x_range=None, points=None):
    """Run the original graph() and copy its Matplotlib artists into plain arrays."""
    spec = resolve_spec(spec_or_key)
    arguments = constructor_arguments(spec, parameters, x_range, points)
    library_class = _library_class(spec.key)
    captured_figures = []
    original_figure = plt.figure

    def new_figure(*args, **kwargs):
        # Ignore the library's window title to avoid reusing someone else's figure.
        figure = original_figure()
        captured_figures.append(figure)
        return figure

    series = []
    messages = []
    try:
        with python_warnings.catch_warnings(record=True) as caught:
            python_warnings.simplefilter("always", RuntimeWarning)
            with patch.object(plt, "figure", new_figure), patch.object(plt, "show"):
                library_class(**arguments).graph()
            for figure in captured_figures:
                # A colorbar creates its own axes; the first axes is the actual plot.
                for axes in figure.axes[:1]:
                    stem_markers = {id(container.markerline) for container in axes.containers if isinstance(container, StemContainer)}
                    for line in axes.lines:
                        if stem_markers and id(line) not in stem_markers:
                            continue
                        x = np.asarray(line.get_xdata(), dtype=float).copy()
                        y = np.asarray(line.get_ydata(), dtype=float).copy()
                        label = line.get_label()
                        if label.startswith("_"):
                            label = spec.name
                        series.append(SeriesData(x, y, label, bool(stem_markers) or spec.key in {"Poisson", "Fibonacci"}))
                    for collection in axes.collections:
                        if isinstance(collection, PathCollection):
                            offsets = np.asarray(collection.get_offsets(), dtype=float)
                            colors = collection.get_array()
                            series.append(SeriesData(offsets[:, 0].copy(), offsets[:, 1].copy(), spec.name, True,
                                                     None if colors is None else np.asarray(colors).copy()))
            if caught:
                messages.append("La librería ha encontrado valores fuera de dominio o desbordamientos; se conservan como huecos en la gráfica.")
    except Exception as error:
        raise CalculationError(f"marksfuncs.{spec.key}: {error}") from error
    finally:
        for figure in captured_figures:
            plt.close(figure)
    if not series or not any(np.any(np.isfinite(item.x) & np.isfinite(item.y)) for item in series):
        raise CalculationError("marksfuncs no ha producido valores finitos. Revisa el dominio, los parámetros y la expresión.")
    if any(np.any(~np.isfinite(item.y)) for item in series) and not messages:
        messages.append("Hay muestras fuera de dominio; se muestran como huecos.")
    return CurveData(tuple(series), spec.key, tuple(messages))


def generate_code(spec_or_key, parameters=None, x_range=None, points=None, variable_name="f"):
    """Export a runnable script using variables and the same upstream constructor."""
    spec = resolve_spec(spec_or_key)
    _library_class(spec.key)
    arguments = constructor_arguments(spec, parameters, x_range, points)
    if not isinstance(variable_name, str) or not variable_name.isidentifier() or keyword.iskeyword(variable_name) or variable_name in set(arguments) | {spec.key}:
        raise CalculationError("El nombre de la función debe ser un identificador Python distinto de sus parámetros.")
    assignments = "\n".join(f"{key} = {value!r}" for key, value in arguments.items())
    references = ",\n".join(f"    {key}={key}" for key in arguments)
    return (f"from marksfuncs.functions import {spec.key}\n\n"
            f"{assignments}\n\n{variable_name} = {spec.key}(\n{references},\n)\n"
            f"{variable_name}.graph()\n")
