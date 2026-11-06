"""Educational metadata for the 56 classes implemented by marksfuncs 1.1.

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


A = p("a", "Escala vertical", 1)
B = p("b", "Escala horizontal", 1)
C = p("c", "Desplazamiento", 0)
POS_B = p("b", "Escala horizontal", 1, 0.1, 10)
WIDTH = p("c", "Anchura", 1, 0.1, 10)
REAL = "Todos los números reales."


def spec(key, name, category, formula, description, domain=REAL, parameters=(),
         x_range=(-6, 6), points=401, note=""):
    return FunctionSpec(key, name, category, formula, description, domain,
                        tuple(parameters), x_range, points, note)


CATALOG = (
    spec("Linear", "Lineal", "Elementales", "f(x) = mx + b",
         "Una recta con pendiente constante. m controla la inclinación y b el punto donde corta el eje vertical.",
         parameters=(p("m", "Pendiente", 1), p("b", "Ordenada al origen", 0))),
    spec("Quadratic", "Cuadrática", "Elementales", "f(x) = ax² + bx + c",
         "Dibuja una parábola. a cambia su apertura y orientación; b y c desplazan el vértice y el corte vertical.",
         parameters=(A, p("b", "Coeficiente lineal", 0), p("c", "Término independiente", 0))),
    spec("Identity", "Identidad", "Elementales", "f(x) = x",
         "Devuelve el mismo valor que recibe. Su gráfica es la diagonal de pendiente uno."),
    spec("Polynomial", "Polinomio por texto", "Elementales", "f(x) = Σ aᵢxⁱ",
         "Construye un polinomio con la sintaxis clásica de marksfuncs: por ejemplo, 2x^3 - 3x + 1.",
         parameters=(text("polynomial_str", "Polinomio", "x^3 - 2x"),),
         x_range=(-3, 3), note="El analizador original añade términos constantes vacíos. Se muestra su resultado real; para coeficientes exactos usa Polinomio por coeficientes."),
    spec("PolynomialCoefficients", "Polinomio por coeficientes", "Elementales", "f(x) = Σ aᵢxⁱ",
         "Asigna cada coeficiente de forma explícita. Una lista [1, 2, 3] representa 1 + 2x + 3x²; también admite {0: 1, 2: 3}.",
         parameters=(text("coefficients", "Coeficientes (grado ascendente)", "[0, -2, 0, 1]", "coefficients"),), x_range=(-3, 3)),
    spec("Power", "Potencia", "Elementales", "f(x) = axᵇ",
         "El exponente b transforma la forma de la curva. Un exponente par crea simetría respecto al eje vertical.",
         "Con exponentes no enteros, usa x ≥ 0 para obtener valores reales.", (A, p("b", "Exponente", 2, -5, 10)), (0, 5)),
    spec("Radical", "Radical", "Elementales", "f(x) = a√max(bx, 0)",
         "Una raíz cuadrada escalada. La implementación de marksfuncs recorta bx negativo a cero.",
         REAL, (A, B), (-2, 8), note="El recorte a cero forma parte de la librería; no representa valores complejos."),
    spec("Absolute", "Valor absoluto", "Elementales", "f(x) = a|bx|",
         "La distancia al cero produce una curva en V. a y b modifican la inclinación de sus dos ramas.", parameters=(A, B)),
    spec("Rational", "Racional", "Elementales", "f(x) = a / (bx)",
         "Una hipérbola con dos ramas. La curva se aproxima a los ejes sin alcanzarlos cuando a y b no son cero.",
         "x ≠ 0 y b ≠ 0; en cero hay una asíntota.", (A, POS_B)),
    spec("Exponential", "Exponencial", "Exponenciales", "f(x) = a·exp(bx)",
         "Modela crecimiento o decaimiento continuo. b positivo hace crecer la curva y b negativo la hace disminuir.", parameters=(A, p("b", "Tasa de crecimiento", 0.5))),
    spec("Logarithmic", "Logarítmica", "Exponenciales", "f(x) = a·ln(bx)",
         "Crece con rapidez al principio y luego más lentamente. Es la transformación inversa de una exponencial.",
         "x > 0 y b > 0. marksfuncs deja x ≤ 0 sin valor.", (A, POS_B), (0.05, 10)),
    spec("GeneralizedExponential", "Exponencial generalizada", "Exponenciales", "f(x) = a·exp(−(x−b)²/(2c²))",
         "Una campana exponencial centrada en b. a controla la altura y c su anchura.",
         "c > 0.", (A, p("b", "Centro", 0), WIDTH)),
    spec("ComplexExponential", "Exponencial compleja", "Exponenciales", "f(x) = a·exp(jbx)",
         "Relaciona exponenciales y oscilaciones mediante la identidad de Euler. Se dibujan por separado las partes real e imaginaria.",
         REAL, (A, B), note="La gráfica conserva las dos series calculadas por marksfuncs: real e imaginaria."),
    spec("Trigonometric", "Seno", "Trigonométricas", "f(x) = a·sin(bx)",
         "Una oscilación periódica. a determina la amplitud y b la frecuencia angular; el período es 2π/|b|.",
         REAL, (p("a", "Amplitud", 2), p("b", "Frecuencia angular", 1))),
    spec("InverseTrigonometric", "Arcoseno", "Trigonométricas", "f(x) = a·arcsin(bx)",
         "Devuelve el ángulo cuyo seno es bx. La escala a multiplica el resultado en radianes.",
         "|bx| ≤ 1.", (A, POS_B), (-1, 1)),
    spec("Hyperbolic", "Seno hiperbólico", "Trigonométricas", "f(x) = a·sinh(bx)",
         "Una curva impar definida mediante exponenciales. Aparece en geometría hiperbólica y ecuaciones diferenciales.", parameters=(A, B), x_range=(-3, 3)),
    spec("HyperbolicTangent", "Tangente hiperbólica", "Trigonométricas", "f(x) = a·tanh(x)",
         "Una transición suave entre −a y a, utilizada como función de activación y modelo de saturación.", parameters=(A,)),
    spec("SincDirichlet", "Sinc", "Trigonométricas", "f(x) = sinc(ax)",
         "Una oscilación amortiguada alrededor del origen. NumPy utiliza sinc(t) = sin(πt)/(πt), con valor 1 en cero.", parameters=(p("a", "Frecuencia", 1),)),
    spec("Dirichlet", "Sinc desplazada", "Trigonométricas", "f(x) = sinc(ax − b)",
         "Desplaza y escala una sinc normalizada. El máximo aparece cuando ax − b es cero.", parameters=(p("a", "Frecuencia", 1), p("b", "Desplazamiento", 0))),
    spec("Sigmoid", "Sigmoide", "Activación y crecimiento", "f(x) = a / (1 + exp(−b(x−c)))",
         "Una transición en S. a fija el límite superior, b la pendiente y c el centro de la transición.", parameters=(A, p("b", "Pendiente", 1), p("c", "Centro", 0))),
    spec("Logistic", "Logística", "Activación y crecimiento", "f(x) = c / (1 + exp(−b(x−a)))",
         "Modela crecimiento con saturación. En esta clase a es el centro y c la capacidad máxima.", parameters=(p("a", "Centro", 0), p("b", "Tasa", 1), p("c", "Capacidad máxima", 1, 0.1, 10))),
    spec("GeneralizedLogistics", "Logística generalizada", "Activación y crecimiento", "f(x) = d/(1 + exp(−b(x−a))) + c",
         "Añade un desplazamiento vertical a la logística. La transición va de c a c + d cuando b es positivo.", parameters=(p("a", "Centro", 0), p("b", "Tasa", 1), p("c", "Nivel inicial", 0), p("d", "Amplitud", 1))),
    spec("Gompertz", "Gompertz", "Activación y crecimiento", "f(x) = a·exp(−b·exp(−cx))",
         "Una curva de crecimiento asimétrica que se aproxima a a. Se utiliza para describir crecimiento biológico.", parameters=(A, p("b", "Desplazamiento", 1, 0.1, 10), p("c", "Tasa", 1, 0.1, 10))),
    spec("Hill", "Hill", "Activación y crecimiento", "f(x) = vmax·xⁿ / (kⁿ + xⁿ)",
         "Describe una respuesta cooperativa y saturable. k fija la semisaturación y n la brusquedad de la transición.",
         "x ≥ 0, k > 0, n ≥ 1.", (p("vmax", "Respuesta máxima", 1, 0.1, 10), p("k", "Semisaturación", 1, 0.1, 10), p("n", "Cooperatividad", 2, 1, 10, integer=True)), (0, 6)),
    spec("MichaelisMenten", "Michaelis–Menten", "Activación y crecimiento", "f(x) = vmax·x / (km + x)",
         "Modela la velocidad de una reacción enzimática. Al aumentar el sustrato x, la velocidad se aproxima a vmax.",
         "x ≥ 0 y km > 0.", (p("vmax", "Velocidad máxima", 1, 0.1, 10), p("km", "Constante de Michaelis", 1, 0.1, 10)), (0, 10)),
    spec("Gaussian", "Normal (densidad)", "Distribuciones", "f(x) = exp(−(x−μ)²/(2σ²)) / (σ√(2π))",
         "La distribución normal tiene área total uno. μ sitúa su centro y σ mide la dispersión.",
         "σ > 0.", (p("mu", "Media μ", 0), p("sigma", "Desviación σ", 1, 0.1, 10))),
    spec("Gauss", "Campana de Gauss", "Distribuciones", "f(x) = a·exp(−(x−b)²/(2c²))",
         "Una campana con altura libre a, centro b y anchura c. A diferencia de la densidad normal, no tiene por qué integrar uno.",
         "c > 0.", (A, p("b", "Centro", 0), WIDTH)),
    spec("Weibull", "Weibull", "Distribuciones", "f(x) = Weibull.pdf(x; k, λ)",
         "Una densidad para tiempos de vida y fiabilidad. k modifica la forma y λ la escala temporal.",
         "x ≥ 0, k > 0 y λ > 0.", (p("k", "Forma k", 2, 0.1, 10), p("lambda_param", "Escala λ", 2, 0.1, 10)), (0, 8)),
    spec("Beta", "Beta", "Distribuciones", "f(x) = x^(α−1)(1−x)^(β−1) / B(α, β)",
         "Una densidad restringida al intervalo de cero a uno. α y β permiten formas simétricas o sesgadas.",
         "0 ≤ x ≤ 1; α > 0 y β > 0.", (p("alpha", "Forma α", 2, 0.1, 10), p("beta", "Forma β", 3, 0.1, 10)), (0, 1)),
    spec("Gamma", "Gamma (distribución)", "Distribuciones", "f(x) = Gamma.pdf(x; k, θ)",
         "Modela tiempos de espera positivos. k determina la forma y θ escala la distribución.",
         "x ≥ 0, k > 0 y θ > 0.", (p("k", "Forma k", 2, 0.1, 10), p("theta", "Escala θ", 1, 0.1, 10)), (0, 12)),
    spec("Poisson", "Poisson", "Distribuciones", "P(X = x) = exp(−λ)λˣ / x!",
         "La probabilidad de contar x eventos independientes con media λ. Solo los enteros no negativos tienen probabilidad distinta de cero.",
         "x entero ≥ 0 y λ > 0.", (p("lambda_param", "Media λ", 4, 0.1, 20),), (0, 15), 16,
         "La librería evalúa sobre linspace; usa límites enteros y puntos = fin − inicio + 1 para muestrear los enteros."),
    spec("ChiSquare", "Chi cuadrado", "Distribuciones", "f(x) = χ².pdf(x; df)",
         "La densidad de una suma de cuadrados de normales estándar. df indica los grados de libertad.",
         "x ≥ 0 y df > 0.", (p("df", "Grados de libertad", 4, 1, 30, integer=True),), (0, 20)),
    spec("BesselOrder0", "Bessel J₀", "Especiales", "f(x) = J₀(x)",
         "Una oscilación especial de amplitud decreciente que aparece en ondas con simetría cilíndrica."),
    spec("BesselOrder1", "Bessel J₁", "Especiales", "f(x) = J₁(x)",
         "La función de Bessel de primer orden describe modos radiales de vibración y propagación de ondas."),
    spec("Error", "Función de error", "Especiales", "f(x) = erf(x)",
         "Una integral de la campana gaussiana. Es impar, pasa por cero y se aproxima a −1 y 1."),
    spec("Airy", "Airy", "Especiales", "f(x) = Ai(x)",
         "La solución de Airy oscila para x negativo y decae para x positivo. Aparece en óptica y mecánica cuántica."),
    spec("SineFresnel", "Fresnel seno", "Especiales", "f(x) = S(x)",
         "Integra sin(πt²/2) desde cero hasta x. Describe fenómenos de difracción con frecuencia que aumenta.",
         note="marksfuncs 1.1 declara esta clase pero no implementa graph() ni image(). Su explicación está disponible; el cálculo requiere una versión que añada esos métodos."),
    spec("CosineFresnel", "Fresnel coseno", "Especiales", "f(x) = C(x)",
         "Integra cos(πt²/2) desde cero hasta x. Junto a S(x) forma la espiral de Cornu.",
         note="marksfuncs 1.1 declara esta clase pero no implementa graph() ni image(). Su explicación está disponible; el cálculo requiere una versión que añada esos métodos."),
    spec("LogGamma", "Logaritmo de Gamma", "Especiales", "f(x) = ln|Γ(x)|",
         "El logaritmo de la magnitud de Gamma evita valores enormes y prolonga la idea de factorial.",
         "Evita los enteros no positivos, donde Gamma tiene polos.", x_range=(0.1, 6)),
    spec("LogSineProduct", "Logaritmo del seno", "Especiales", "f(x) = ln|sin(x)|",
         "Una función periódica no positiva con caídas pronunciadas cerca de los ceros del seno.",
         "sin(x) ≠ 0; hay singularidades en los múltiplos de π."),
    spec("Legendre", "Polinomio de Legendre", "Especiales", "f(x) = Pₙ(x)",
         "Una familia de polinomios ortogonales en [−1, 1]. El grado n determina el número de oscilaciones.",
         REAL, (p("grade", "Grado n", 3, 0, 20, integer=True),), (-1, 1)),
    spec("Sign", "Signo", "Señales", "f(x) = sign(x)",
         "Devuelve −1 para negativos, cero en el origen y 1 para positivos."),
    spec("Floor", "Parte entera inferior", "Señales", "f(x) = ⌊x⌋",
         "Redondea hacia el entero inferior. La gráfica tiene escalones de altura uno."),
    spec("Ceil", "Parte entera superior", "Señales", "f(x) = ⌈x⌉",
         "Redondea hacia el entero superior. Cada escalón indica el menor entero mayor o igual que x."),
    spec("UnitStep", "Escalón unitario", "Señales", "f(x) = a·u(bx)",
         "Activa una señal de altura a al cruzar el origen. El signo de b decide la orientación.", parameters=(A, B)),
    spec("Heaviside", "Heaviside", "Señales", "f(x) = H(x)",
         "Un cambio instantáneo de cero a uno en el origen, usado para encender señales y condiciones."),
    spec("TopHat", "Pulso rectangular", "Señales", "f(x) = 1 si a ≤ x ≤ b; 0 fuera",
         "Una ventana rectangular con extremos configurables. Vale uno dentro del intervalo y cero fuera.",
         "a < b.", (p("a", "Inicio del pulso", -1), p("b", "Final del pulso", 1))),
    spec("Triangular", "Pulso triangular", "Señales", "f(x) = max(0, a − |x−b|/c)",
         "Un pulso con pico en b. a marca la altura y c escala la anchura de sus lados.",
         "c > 0.", (p("a", "Altura", 2, 0.1, 10), p("b", "Centro", 0), WIDTH)),
    spec("SawTooth", "Diente de sierra", "Señales", "f(x) = a(x − T⌊x/T⌋), T = 2π/b",
         "Una rampa que se reinicia periódicamente. b controla su período y a la pendiente de cada tramo.",
         "b > 0.", (A, POS_B), (-10, 10)),
    spec("SquareWave", "Onda cuadrada", "Señales", "f(x) = a(1 − 2(⌊x/T⌋ mod 2)), T = 2π/b",
         "Alterna entre a y −a. Cada nivel dura 2π/b en la implementación de marksfuncs.",
         "b > 0.", (p("a", "Amplitud", 1), POS_B), (-15, 15)),
    spec("DiracDelta", "Impulso discreto", "Señales", "f(xᵢ) = 1 en la muestra central; 0 en el resto",
         "marksfuncs dibuja un impulso de altura uno en la muestra central del intervalo elegido.",
         REAL, note="Es una ilustración discreta; no es una delta de Dirac normalizada ni se coloca necesariamente en x = 0."),
    spec("Fibonacci", "Fibonacci", "Sucesiones", "Fₙ = Fₙ₋₁ + Fₙ₋₂",
         "Cada término suma los dos anteriores, a partir de cero y uno. La gráfica muestra los términos de 0 a n.",
         "n entero de 0 a 20 en esta UI para limitar el algoritmo recursivo.", (p("n", "Último índice", 10, 0, 20, integer=True),), (0, 10),
         note="El intervalo x se ignora en esta clase: marksfuncs usa los índices de la sucesión."),
    spec("Ackermann", "Ackermann", "Sucesiones", "A(0,n)=n+1; A(m,n)=A(m−1,A(m,n−1))",
         "Una función recursiva de crecimiento muy rápido. marksfuncs representa una matriz de pares (m, n), coloreada con sus valores.",
         "m entero de 0 a 3 y n entero de 0 a 3 en esta UI.", (p("m", "Orden máximo m", 2, 0, 3, integer=True), p("n", "Índice máximo n", 3, 0, 3, integer=True)), (0, 3),
         note="Los ejes representan m y n; el intervalo x no interviene. marksfuncs aplana los colores en un orden distinto al de su malla, por lo que su asociación con cada par puede ser incorrecta. Se conservan los puntos y colores originales de la librería."),
    spec("ModifiedAckermann", "Ackermann modificada", "Sucesiones", "f(x) = A_mod(m, int(x))",
         "Utiliza expresiones cerradas para órdenes de cero a tres. La librería convierte cada x al entero más próximo hacia cero.",
         "m entero de 0 a 3 y 0 ≤ x ≤ 20 en esta UI.", (p("m", "Orden m", 2, 0, 3, integer=True), p("n", "n (no usado por graph)", 3, 0, 20, integer=True)), (0, 10),
         note="El constructor exige n, pero graph() calcula con x y no utiliza ese parámetro."),
    spec("Planck", "Planck (modelo reducido)", "Física", "f(x) = 1 / (exp(hc/(kTx)) − 1)",
         "El factor de ocupación de Planck. h, c, k y T controlan la relación entre energía y temperatura.",
         "x > 0; h, c, k y T positivos.", (p("h", "Constante h", 1, 0.1, 10), p("k", "Constante k", 1, 0.1, 10), p("c", "Velocidad c", 1, 0.1, 10), p("T", "Temperatura T", 1, 0.1, 10)), (0.1, 5),
         note="Se usan unidades normalizadas. La librería calcula este factor, sin el prefactor completo de radiancia de cuerpo negro."),
    spec("ExpressionFunction", "Expresión libre", "Expresión libre", "f(x) = tu expresión",
         "Combina funciones y operaciones: sin(x), cos(x), exp(x), log(x), sqrt(x), pi y e. Usa ** para potencias.",
         "Depende de la expresión. Solo se admiten operaciones matemáticas y funciones conocidas.",
         (text("expression", "Expresión matemática", "sin(x) + 0.2*x**2"),)),
)

BY_KEY = {item.key: item for item in CATALOG}
CATEGORIES = tuple(dict.fromkeys(item.category for item in CATALOG))
