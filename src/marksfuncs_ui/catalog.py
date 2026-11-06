"""Educational metadata for the 56 classes implemented by marksfuncs 1.2.

Formulas explain the upstream implementation; calculation belongs to marksfuncs.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    default: Any
    minimum: float = -10
    maximum: float = 10
    step: float = 0.1
    integer: bool = False
    help: str = ""
    kind: str = "number"


@dataclass(frozen=True)
class FunctionSpec:
    key: str
    name: str
    category: str
    formula: str
    description: str
    domain: str
    parameters: tuple[Parameter, ...] = ()
    x_range: tuple[float, float] = (-6, 6)
    points: int = 401
    note: str = ""

    def defaults(self) -> dict[str, Any]:
        return {parameter.key: parameter.default for parameter in self.parameters}


def p(key, label, default=1, minimum=-10, maximum=10, *, integer=False, help=""):
    return Parameter(key, label, default, minimum, maximum, 1 if integer else 0.1,
                     integer, help)


def text(key, label, default, kind="text"):
    return Parameter(key, label, default, kind=kind)


A = p("a", "Vertical scale", 1)
B = p("b", "Horizontal scale", 1)
C = p("c", "Offset", 0)
POS_B = p("b", "Horizontal scale", 1, 0.1, 10)
WIDTH = p("c", "Width", 1, 0.1, 10)
REAL = "All real numbers."


def spec(key, name, category, formula, description, domain=REAL, parameters=(),
         x_range=(-6, 6), points=401, note=""):
    return FunctionSpec(key, name, category, formula, description, domain,
                        tuple(parameters), x_range, points, note)


CATALOG = (
    spec("Linear", "Linear", "Elementary", "f(x) = mx + b",
         "A straight line. m sets the slope and b sets the vertical intercept.",
         parameters=(p("m", "Slope", 1), p("b", "Intercept", 0))),
    spec("Quadratic", "Quadratic", "Elementary", "f(x) = ax² + bx + c",
         "A parabola. a controls its opening and direction; b and c set the vertex and vertical intercept.",
         parameters=(A, p("b", "Linear coefficient", 0), p("c", "Constant term", 0))),
    spec("Identity", "Identity", "Elementary", "f(x) = x",
         "Returns its input unchanged: a diagonal line with slope one."),
    spec("Polynomial", "Polynomial by text", "Elementary", "f(x) = Σ aᵢxⁱ",
         "Parses a polynomial in marksfuncs syntax, such as 2x^3 - 3x + 1.",
         parameters=(text("polynomial_str", "Polynomial", "x^3 - 2x"),),
         x_range=(-3, 3), note="The upstream parser adds empty constant terms. Its output is preserved; use Polynomial by coefficients to specify coefficients exactly."),
    spec("PolynomialCoefficients", "Polynomial by coefficients", "Elementary", "f(x) = Σ aᵢxⁱ",
         "Sets coefficients explicitly. [1, 2, 3] means 1 + 2x + 3x²; {0: 1, 2: 3} is also accepted.",
         parameters=(text("coefficients", "Coefficients (ascending degree)", "[0, -2, 0, 1]", "coefficients"),), x_range=(-3, 3)),
    spec("Power", "Power", "Elementary", "f(x) = axᵇ",
         "b sets the exponent. Even integer powers are symmetric about the vertical axis.",
         "Use x ≥ 0 for real values with noninteger exponents.", (A, p("b", "Exponent", 2, -5, 10)), (0, 5)),
    spec("Radical", "Radical", "Elementary", "f(x) = a√max(bx, 0)",
         "A scaled square root. marksfuncs clips negative bx to zero.",
         REAL, (A, B), (-2, 8), note="Clipping is part of the library implementation; it does not return complex values."),
    spec("Absolute", "Absolute value", "Elementary", "f(x) = a|bx|",
         "Distance from zero forms a V-shaped curve. a and b scale the two branches.", parameters=(A, B)),
    spec("Rational", "Rational", "Elementary", "f(x) = a / (bx)",
         "A two-branch hyperbola with asymptotes along the axes when a and b are nonzero.",
         "x ≠ 0 and b ≠ 0; the origin is a vertical asymptote.", (A, POS_B)),
    spec("Exponential", "Exponential", "Exponential", "f(x) = a·exp(bx)",
         "Continuous growth or decay. Positive b produces growth; negative b produces decay.", parameters=(A, p("b", "Growth rate", 0.5))),
    spec("Logarithmic", "Logarithmic", "Exponential", "f(x) = a·ln(bx)",
         "The inverse shape of exponential growth: steep initially, then progressively flatter.",
         "x > 0 and b > 0. marksfuncs leaves x ≤ 0 undefined.", (A, POS_B), (0.05, 10)),
    spec("GeneralizedExponential", "Generalized exponential", "Exponential", "f(x) = a·exp(−(x−b)²/(2c²))",
         "A bell-shaped exponential centered at b, with height a and width c.",
         "c > 0.", (A, p("b", "Center", 0), WIDTH)),
    spec("ComplexExponential", "Complex exponential", "Exponential", "f(x) = a·exp(jbx)",
         "Euler's identity links exponentials and oscillations. Real and imaginary components are plotted separately.",
         REAL, (A, B), note="Both series come from marksfuncs: the real component and the imaginary component."),
    spec("Trigonometric", "Sine", "Trigonometric", "f(x) = a·sin(bx)",
         "A periodic oscillation. a sets the amplitude and b the angular frequency; the period is 2π/|b|.",
         REAL, (p("a", "Amplitude", 2), p("b", "Angular frequency", 1))),
    spec("InverseTrigonometric", "Arcsine", "Trigonometric", "f(x) = a·arcsin(bx)",
         "Returns the angle whose sine is bx. a scales the result in radians.",
         "|bx| ≤ 1.", (A, POS_B), (-1, 1)),
    spec("Hyperbolic", "Hyperbolic sine", "Trigonometric", "f(x) = a·sinh(bx)",
         "An odd function defined through exponentials, used in hyperbolic geometry and differential equations.", parameters=(A, B), x_range=(-3, 3)),
    spec("HyperbolicTangent", "Hyperbolic tangent", "Trigonometric", "f(x) = a·tanh(x)",
         "A smooth transition between −a and a, used in activation and saturation models.", parameters=(A,)),
    spec("SincDirichlet", "Sinc", "Trigonometric", "f(x) = sinc(ax)",
         "A decaying oscillation. NumPy defines sinc(t) = sin(πt)/(πt), with value 1 at zero.", parameters=(p("a", "Frequency", 1),)),
    spec("Dirichlet", "Shifted sinc", "Trigonometric", "f(x) = sinc(ax − b)",
         "A shifted, scaled normalized sinc. Its peak occurs where ax − b is zero.", parameters=(p("a", "Frequency", 1), p("b", "Offset", 0))),
    spec("Sigmoid", "Sigmoid", "Activation & growth", "f(x) = a / (1 + exp(−b(x−c)))",
         "An S-shaped transition. a sets the upper limit, b the steepness and c the center.", parameters=(A, p("b", "Steepness", 1), p("c", "Center", 0))),
    spec("Logistic", "Logistic", "Activation & growth", "f(x) = c / (1 + exp(−b(x−a)))",
         "Growth with saturation. This class uses a for the center and c for the capacity.", parameters=(p("a", "Center", 0), p("b", "Rate", 1), p("c", "Capacity", 1, 0.1, 10))),
    spec("GeneralizedLogistics", "Generalized logistic", "Activation & growth", "f(x) = d/(1 + exp(−b(x−a))) + c",
         "Adds a vertical offset to logistic growth. For positive b, the transition runs from c to c + d.", parameters=(p("a", "Center", 0), p("b", "Rate", 1), p("c", "Initial level", 0), p("d", "Amplitude", 1))),
    spec("Gompertz", "Gompertz", "Activation & growth", "f(x) = a·exp(−b·exp(−cx))",
         "An asymmetric growth curve approaching a, often used for biological growth.", parameters=(A, p("b", "Offset", 1, 0.1, 10), p("c", "Rate", 1, 0.1, 10))),
    spec("Hill", "Hill", "Activation & growth", "f(x) = vmax·xⁿ / (kⁿ + xⁿ)",
         "A cooperative, saturating response. k sets half-saturation and n controls the transition's steepness.",
         "x ≥ 0, k > 0, n ≥ 1.", (p("vmax", "Maximum response", 1, 0.1, 10), p("k", "Half-saturation", 1, 0.1, 10), p("n", "Cooperativity", 2, 1, 10, integer=True)), (0, 6)),
    spec("MichaelisMenten", "Michaelis–Menten", "Activation & growth", "f(x) = vmax·x / (km + x)",
         "Models an enzyme reaction rate. As substrate x increases, the rate approaches vmax.",
         "x ≥ 0 and km > 0.", (p("vmax", "Maximum rate", 1, 0.1, 10), p("km", "Michaelis constant", 1, 0.1, 10)), (0, 10)),
    spec("Gaussian", "Normal density", "Distributions", "f(x) = exp(−(x−μ)²/(2σ²)) / (σ√(2π))",
         "A normal probability density with total area one. μ sets the center and σ sets the spread.",
         "σ > 0.", (p("mu", "Mean μ", 0), p("sigma", "Deviation σ", 1, 0.1, 10))),
    spec("Gauss", "Gaussian bell", "Distributions", "f(x) = a·exp(−(x−b)²/(2c²))",
         "A bell curve with height a, center b and width c. Its area is not necessarily one.",
         "c > 0.", (A, p("b", "Center", 0), WIDTH)),
    spec("Weibull", "Weibull", "Distributions", "f(x) = Weibull.pdf(x; k, λ)",
         "A density for lifetimes and reliability. k sets the shape and λ sets the scale.",
         "x ≥ 0, k > 0 and λ > 0.", (p("k", "Shape k", 2, 0.1, 10), p("lambda_param", "Scale λ", 2, 0.1, 10)), (0, 8)),
    spec("Beta", "Beta", "Distributions", "f(x) = x^(α−1)(1−x)^(β−1) / B(α, β)",
         "A density on the interval from zero to one. α and β control symmetry and skew.",
         "0 ≤ x ≤ 1; α > 0 and β > 0.", (p("alpha", "Shape α", 2, 0.1, 10), p("beta", "Shape β", 3, 0.1, 10)), (0, 1)),
    spec("Gamma", "Gamma distribution", "Distributions", "f(x) = Gamma.pdf(x; k, θ)",
         "A density for positive waiting times. k sets the shape and θ sets the scale.",
         "x ≥ 0, k > 0 and θ > 0.", (p("k", "Shape k", 2, 0.1, 10), p("theta", "Scale θ", 1, 0.1, 10)), (0, 12)),
    spec("Poisson", "Poisson", "Distributions", "P(X = x) = exp(−λ)λˣ / x!",
         "The probability of x independent events with mean λ. Only nonnegative integers have nonzero probability.",
         "Integer x ≥ 0 and λ > 0.", (p("lambda_param", "Mean λ", 4, 0.1, 20),), (0, 15), 16,
         "The library samples with linspace. Use integer bounds and points = end − start + 1 to sample integers."),
    spec("ChiSquare", "Chi-square", "Distributions", "f(x) = χ².pdf(x; df)",
         "The density of a sum of squared standard normal variables. df sets the degrees of freedom.",
         "x ≥ 0 and df > 0.", (p("df", "Degrees of freedom", 4, 1, 30, integer=True),), (0, 20)),
    spec("BesselOrder0", "Bessel J₀", "Special", "f(x) = J₀(x)",
         "A decaying oscillation that appears in waves with cylindrical symmetry."),
    spec("BesselOrder1", "Bessel J₁", "Special", "f(x) = J₁(x)",
         "The first-order Bessel function describes radial vibration modes and wave propagation."),
    spec("Error", "Error function", "Special", "f(x) = erf(x)",
         "An integral of a Gaussian. It is odd, crosses zero and approaches −1 and 1."),
    spec("Airy", "Airy", "Special", "f(x) = Ai(x)",
         "Airy's solution oscillates for negative x and decays for positive x, with uses in optics and quantum mechanics."),
    spec("SineFresnel", "Fresnel sine", "Special", "f(x) = S(x)",
         "Integrates sin(πt²/2) from zero to x; used in diffraction with increasing oscillation frequency."),
    spec("CosineFresnel", "Fresnel cosine", "Special", "f(x) = C(x)",
         "Integrates cos(πt²/2) from zero to x. Together with S(x), it forms the Cornu spiral."),
    spec("LogGamma", "Log Gamma", "Special", "f(x) = ln|Γ(x)|",
         "The logarithm of Gamma's magnitude avoids large values and extends the factorial relationship.",
         "Avoid nonpositive integers, where Gamma has poles.", x_range=(0.1, 6)),
    spec("LogSineProduct", "Log sine", "Special", "f(x) = ln|sin(x)|",
         "A nonpositive periodic function with sharp drops near the sine's zeros.",
         "sin(x) ≠ 0; singularities occur at multiples of π."),
    spec("Legendre", "Legendre polynomial", "Special", "f(x) = Pₙ(x)",
         "A family of orthogonal polynomials on [−1, 1]. Degree n controls the number of oscillations.",
         REAL, (p("grade", "Degree n", 3, 0, 20, integer=True),), (-1, 1)),
    spec("Sign", "Sign", "Signals", "f(x) = sign(x)",
         "Returns −1 for negative inputs, zero at the origin and 1 for positive inputs."),
    spec("Floor", "Floor", "Signals", "f(x) = ⌊x⌋",
         "Rounds down to the nearest integer, producing unit-height steps."),
    spec("Ceil", "Ceiling", "Signals", "f(x) = ⌈x⌉",
         "Rounds up to the smallest integer greater than or equal to x."),
    spec("UnitStep", "Unit step", "Signals", "f(x) = a·u(bx)",
         "Switches a signal of height a at the origin. The sign of b sets its direction.", parameters=(A, B)),
    spec("Heaviside", "Heaviside", "Signals", "f(x) = H(x)",
         "An instantaneous change from zero to one at the origin."),
    spec("TopHat", "Rectangular pulse", "Signals", "f(x) = 1 for a ≤ x ≤ b; 0 otherwise",
         "A rectangular window with configurable endpoints: one inside the interval and zero outside.",
         "a < b.", (p("a", "Pulse start", -1), p("b", "Pulse end", 1))),
    spec("Triangular", "Triangular pulse", "Signals", "f(x) = max(0, a − |x−b|/c)",
         "A pulse peaking at b. a sets the height and c scales the width.",
         "c > 0.", (p("a", "Height", 2, 0.1, 10), p("b", "Center", 0), WIDTH)),
    spec("SawTooth", "Sawtooth", "Signals", "f(x) = a(x − T⌊x/T⌋), T = 2π/b",
         "A periodically resetting ramp. b controls the period and a the slope of each segment.",
         "b > 0.", (A, POS_B), (-10, 10)),
    spec("SquareWave", "Square wave", "Signals", "f(x) = a(1 − 2(⌊x/T⌋ mod 2)), T = 2π/b",
         "Alternates between a and −a. Each level lasts 2π/b in the marksfuncs implementation.",
         "b > 0.", (p("a", "Amplitude", 1), POS_B), (-15, 15)),
    spec("DiracDelta", "Discrete impulse", "Signals", "f(xᵢ) = 1 at the middle sample; 0 otherwise",
         "marksfuncs places an impulse of height one at the middle sample of the selected interval.",
         REAL, note="This is a discrete illustration, not a normalized Dirac delta. Its position is not necessarily x = 0."),
    spec("Fibonacci", "Fibonacci", "Sequences", "Fₙ = Fₙ₋₁ + Fₙ₋₂",
         "Each term adds the previous two, starting at zero and one. The plot shows terms from 0 to n.",
         "Integer n from 0 to 20; the UI bounds the recursive algorithm.", (p("n", "Last index", 10, 0, 20, integer=True),), (0, 10),
         note="This class ignores the x interval and uses sequence indices."),
    spec("Ackermann", "Ackermann", "Sequences", "A(0,n)=n+1; A(m,n)=A(m−1,A(m,n−1))",
         "A rapidly growing recursive function. marksfuncs plots a grid of (m, n) pairs colored by their values.",
         "Integers m and n from 0 to 3 in this UI.", (p("m", "Maximum order m", 2, 0, 3, integer=True), p("n", "Maximum index n", 3, 0, 3, integer=True)), (0, 3),
         note="The axes are m and n; the x interval is ignored. marksfuncs flattens colors in a different order from its grid, so their association with coordinates may be wrong. Original points and colors are preserved."),
    spec("ModifiedAckermann", "Modified Ackermann", "Sequences", "f(x) = A_mod(m, int(x))",
         "Uses closed forms for orders zero through three. The library truncates each x toward zero.",
         "Integer m from 0 to 3 and 0 ≤ x ≤ 20 in this UI.", (p("m", "Order m", 2, 0, 3, integer=True), p("n", "n (unused by graph)", 3, 0, 20, integer=True)), (0, 10),
         note="The constructor requires n, but graph() uses x and ignores that parameter."),
    spec("Planck", "Planck (reduced model)", "Physics", "f(x) = 1 / (exp(hc/(kTx)) − 1)",
         "The Planck occupation factor. h, c, k and T set the relationship between energy and temperature.",
         "x > 0; h, c, k and T must be positive.", (p("h", "Constant h", 1, 0.1, 10), p("k", "Constant k", 1, 0.1, 10), p("c", "Speed c", 1, 0.1, 10), p("T", "Temperature T", 1, 0.1, 10)), (0.1, 5),
         note="Uses normalized units. The library computes this factor without the full blackbody radiance prefactor."),
    spec("ExpressionFunction", "Expression", "Expression", "f(x) = expression",
         "Combine functions and operators: sin(x), cos(x), exp(x), log(x), sqrt(x), pi and e. Use ** or ^ for powers; 6x and 2(x+1) are accepted.",
         "Depends on the expression. Only supported mathematical operations and function names are accepted.",
         (text("expression", "Expression", "sin(x) + 0.2*x**2"),)),
)

BY_KEY = {item.key: item for item in CATALOG}
CATEGORIES = tuple(dict.fromkeys(item.category for item in CATALOG))
