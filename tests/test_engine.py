"""Exercise installed marksfuncs, including its incomplete and unusual classes."""

import inspect
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import marksfuncs.functions as library
import numpy as np

from marksfuncs_ui.catalog import BY_KEY, CATALOG
from marksfuncs_ui.engine import (
    CalculationError, compute_curve, constructor_arguments, generate_code,
    unavailable_reason, validate_expression,
)


class LibraryIntegrationTests(unittest.TestCase):
    def test_catalog_covers_all_library_classes(self):
        implemented = {name for name, value in vars(library).items()
                       if inspect.isclass(value) and value.__module__ == library.__name__}
        self.assertEqual(implemented, set(BY_KEY))
        self.assertEqual(len(CATALOG), 56)
        for spec in CATALOG:
            self.assertTrue(spec.description and spec.domain and spec.formula)

    def test_every_available_default_runs_real_library(self):
        for spec in CATALOG:
            with self.subTest(function=spec.key):
                if unavailable_reason(spec):
                    self.assertIn(spec.key, {"SineFresnel", "CosineFresnel"})
                    with self.assertRaisesRegex(CalculationError, "does not implement graph"):
                        compute_curve(spec)
                    continue
                result = compute_curve(spec)
                self.assertEqual(result.class_name, spec.key)
                for series in result.series:
                    self.assertEqual(series.x.shape, series.y.shape)
                    self.assertTrue(np.any(np.isfinite(series.x) & np.isfinite(series.y)))

    def test_data_is_copied_from_library_graph_not_recalculated(self):
        def unusual_graph(instance):
            plt.figure("upstream fixture")
            plt.plot([12, 13], [987, 654], label="unchanged upstream data")
            plt.show()

        with patch.object(library.Linear, "graph", unusual_graph):
            curve = compute_curve("Linear", {"m": 2, "b": 3})
        np.testing.assert_array_equal(curve.x, [12, 13])
        np.testing.assert_array_equal(curve.y, [987, 654])
        self.assertEqual(curve.label, "unchanged upstream data")

    def test_upstream_errors_are_reported_without_fallback(self):
        with patch.object(library.Linear, "graph", side_effect=RuntimeError("library failed")):
            with self.assertRaisesRegex(CalculationError, "library failed") as raised:
                compute_curve("Linear")
        self.assertEqual(raised.exception.source, "marksfuncs")

    def test_every_available_class_uses_its_original_graph_samples(self):
        for spec in CATALOG:
            if unavailable_reason(spec):
                continue
            with self.subTest(function=spec.key):
                calls = []

                def sentinel_graph(instance):
                    calls.append(instance)
                    plt.figure()
                    plt.plot([11, 19], [1234, 5678], label="original library samples")
                    plt.show()

                library_class = getattr(library, spec.key)
                with patch.object(library_class, "graph", sentinel_graph):
                    result = compute_curve(spec)
                self.assertEqual(len(calls), 1)
                self.assertIsInstance(calls[0], library_class)
                np.testing.assert_array_equal(result.x, [11, 19])
                np.testing.assert_array_equal(result.y, [1234, 5678])

    def test_expression_notation_is_normalized_before_real_library_evaluation(self):
        expression = "ln(x) + x^2"
        normalized = "log(x) + x**2"
        graph = library.ExpressionFunction.graph
        received = []

        def record_original_graph(instance):
            received.append(instance.expression)
            graph(instance)

        with patch.object(library.ExpressionFunction, "graph", record_original_graph):
            result = compute_curve("ExpressionFunction", {"expression": expression}, (0.1, 3), 31)
        direct = compute_curve("ExpressionFunction", {"expression": normalized}, (0.1, 3), 31)
        self.assertEqual(received, [normalized])
        np.testing.assert_array_equal(result.x, direct.x)
        np.testing.assert_array_equal(result.y, direct.y)

    def test_default_expression_runs_without_adapter_fallback(self):
        graph = library.ExpressionFunction.graph
        with patch.object(library.ExpressionFunction, "graph", autospec=True, side_effect=graph) as called:
            result = compute_curve("ExpressionFunction")
        called.assert_called_once()
        self.assertEqual(called.call_args.args[0].expression, BY_KEY["ExpressionFunction"].defaults()["expression"])
        self.assertEqual(np.isfinite(result.y).sum(), len(result.x))

    def test_figures_are_cleaned_and_existing_figures_preserved(self):
        figure = plt.figure("Existing external figure")
        try:
            initial = set(plt.get_fignums())
            compute_curve("Linear")
            self.assertEqual(initial, set(plt.get_fignums()))
            with patch.object(library.Linear, "graph", side_effect=RuntimeError("failure")):
                with self.assertRaises(CalculationError):
                    compute_curve("Linear")
            self.assertEqual(initial, set(plt.get_fignums()))
        finally:
            plt.close(figure)

    def test_complex_exponential_preserves_both_library_series(self):
        curve = compute_curve("ComplexExponential")
        self.assertEqual(len(curve.series), 2)
        np.testing.assert_allclose(curve.series[0].y, np.cos(curve.x))
        np.testing.assert_allclose(curve.series[1].y, np.sin(curve.x))

    def test_ackermann_preserves_scatter_values(self):
        curve = compute_curve("Ackermann", {"m": 1, "n": 1})
        self.assertTrue(curve.scatter)
        np.testing.assert_array_equal(curve.series[0].colors, [1, 2, 2, 3])
        self.assertEqual(len(curve.x), 4)

    def test_dirac_copies_impulse_and_omits_baseline(self):
        curve = compute_curve("DiracDelta")
        self.assertEqual(len(curve.series), 1)
        self.assertEqual(np.count_nonzero(curve.y), 1)
        self.assertEqual(curve.y[len(curve.y) // 2], 1)

    def test_domain_holes_are_not_filled(self):
        curve = compute_curve("Logarithmic", x_range=(-1, 1), points=101)
        self.assertTrue(np.isnan(curve.y[curve.x <= 0]).all())
        self.assertTrue(curve.warnings)

    def test_entirely_invalid_expression_has_actionable_error(self):
        with self.assertRaisesRegex(CalculationError, "no finite real samples") as raised:
            compute_curve("ExpressionFunction", {"expression": "sqrt(-1)"})
        self.assertEqual(raised.exception.source, "marksfuncs")


class ValidationTests(unittest.TestCase):
    def test_expression_input_errors_identify_the_boundary_before_graph_is_called(self):
        with patch.object(library.ExpressionFunction, "graph") as graph:
            with self.assertRaisesRegex(CalculationError, "Use \\* for multiplication") as raised:
                compute_curve("ExpressionFunction", {"expression": "2x + 1"})
        self.assertEqual(raised.exception.source, "input")
        graph.assert_not_called()

    def test_normalized_expression_export_reproduces_the_upstream_constructor(self):
        source = generate_code("ExpressionFunction", {"expression": "ln(x) + x^2"}, (0.1, 3), 31)
        with patch.object(library.ExpressionFunction, "graph", autospec=True) as graph:
            namespace = {}
            exec(compile(source, "normalized_expression.py", "exec"), namespace)
        self.assertEqual(namespace["expression"], "log(x) + x**2")
        graph.assert_called_once_with(namespace["f"])
        self.assertEqual(namespace["f"].expression, namespace["expression"])

    def test_bad_inputs_are_rejected_before_library_execution(self):
        cases = [
            ("Linear", {"m": float("nan")}, None, None),
            ("Linear", {"m": float("inf")}, None, None),
            ("Linear", {"m": 99}, None, None),
            ("Linear", {"m": 10**1000}, None, None),
            ("Linear", {"unknown": 1}, None, None),
            ("Linear", None, (2, 1), None),
            ("Linear", None, (-float("inf"), 1), None),
            ("Linear", None, (-1, 1), 1),
            ("Linear", None, (-1, 1), 4001),
            ("Linear", None, (-1, 1), 40.5),
            ("Fibonacci", {"n": 21}, None, None),
            ("Fibonacci", {"n": 3.5}, None, None),
            ("Ackermann", {"m": 4}, None, None),
            ("ModifiedAckermann", None, (-1, 2), None),
            ("ModifiedAckermann", {"m": 3}, (0, 1000000), 4000),
            ("TopHat", {"a": 2, "b": 1}, None, None),
            ("PolynomialCoefficients", {"coefficients": "{22: 1}"}, None, None),
            ("PolynomialCoefficients", {"coefficients": "[float('nan')]"}, None, None),
            ("Polynomial", {"polynomial_str": "x^1000"}, None, None),
            ("Polynomial", {"polynomial_str": "print('oops')"}, None, None),
        ]
        with patch.object(library.Linear, "graph") as graph:
            for key, parameters, bounds, points in cases:
                with self.subTest(key=key, parameters=parameters, bounds=bounds, points=points):
                    with self.assertRaises(CalculationError):
                        compute_curve(key, parameters, bounds, points)
            graph.assert_not_called()

    def test_expression_rejects_object_access_and_resource_abuse(self):
        for expression in [
            "__import__('os')", "x.__class__", "(1).__class__.__mro__",
            "[x for x in (1,2)]", "sin.__globals__", "sin(x)[0]",
            "'string'", "True", "unknown(x)", "lambda: 1", "[1]*10000000",
            "1&2", "1<<2", "1//2",
            "2**1000000000", "2**(2**20)", "power(2, 1000000000)",
            "(((9**32)**32)**32)", "(10**12)**32", "(10**12)*(10**12)",
            "9" * 500,
            "jn(1000000000, x)", "sin(x, out=x)",
        ]:
            with self.subTest(expression=expression):
                with self.assertRaises(CalculationError):
                    validate_expression(expression)

    def test_valid_expressions_still_use_library_evaluation(self):
        for expression in ["sin(x) + x**2", "exp(-x)*cos(x)", "maximum(x, 0)", "x**-2", "sin(pi*x)"]:
            with self.subTest(expression=expression):
                self.assertEqual(validate_expression(expression), expression)
                self.assertTrue(compute_curve("ExpressionFunction", {"expression": expression}).series)

    def test_coefficient_input_has_exact_constructor_values(self):
        arguments = constructor_arguments("PolynomialCoefficients", {"coefficients": "{0: -1, 2: 2.5}"})
        self.assertEqual(arguments["coefficients"], {0: -1, 2: 2.5})

    def test_code_exports_same_variables_and_constructor_for_every_available_class(self):
        for spec in CATALOG:
            if unavailable_reason(spec):
                continue
            with self.subTest(function=spec.key):
                source = generate_code(spec, variable_name="my_function")
                self.assertIn(f"from marksfuncs.functions import {spec.key}", source)
                with patch.object(getattr(library, spec.key), "graph", autospec=True) as graph:
                    namespace = {}
                    exec(compile(source, "exported.py", "exec"), namespace)
                    graph.assert_called_once_with(namespace["my_function"])
                    arguments = constructor_arguments(spec)
                    for key, value in arguments.items():
                        self.assertEqual(namespace[key], value)

    def test_invalid_variable_names_cannot_inject_source(self):
        for name in ["f; print(1)", "class", "m", "Linear", "x_values_list", ""]:
            with self.subTest(name=name):
                with self.assertRaises(CalculationError):
                    generate_code("Linear", variable_name=name)


if __name__ == "__main__":
    unittest.main()
