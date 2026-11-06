# Historial organizado

Cada bloque se revisó con `rtk git diff --cached` y verificaciones adecuadas a su contenido. No se ha configurado ni enviado a un remoto.

| Commit | Cambio |
| --- | --- |
| `chore: bootstrap marksfuncs desktop application` | Paquete Python, dependencias e instrucciones iniciales. |
| `feat(core): integrate the full marksfuncs function catalog` | Catálogo, validación, ejecución de marksfuncs y código reproducible. |
| `feat(sessions): preserve visual workspaces with atomic JSON saves` | Sesiones versionadas y protección de archivos existentes. |
| `feat(plot): add animated interactive curves and comparisons` | Gráfica, cámara, animaciones, escalas científicas y colores originales. |
| `feat(ui): add visual variable assignment and studio styling` | Deslizadores, campos precisos, fuentes y estilo visual. |
| `feat(ui): explain functions and expose Python and sampled data` | Explicaciones, vista Python y tabla de muestras. |
| `feat(app): assemble the interactive desktop function laboratory` | Aplicación integrada, comparación, sesiones, exportaciones y pruebas. |
| `build: add reproducible dependencies and a desktop launcher` | Versiones verificadas, lanzador y configuración del wheel. |
| `docs: add usage guide and verified desktop screenshots` | Guía, capturas y particularidades de la librería original. |

Se prepararon archivos concretos con `rtk git add <archivos>`; las revisiones usaron `rtk git diff --cached` y `rtk proxy git diff --cached --check`.

Verificación final:

```powershell
rtk proxy .\.venv\Scripts\python -X utf8 -m unittest discover -s tests -v
rtk proxy .\.venv\Scripts\python -m compileall -q src tests
rtk proxy .\.venv\Scripts\python -m pip check
rtk proxy .\.venv\Scripts\python -m pip wheel --no-deps . --wheel-dir dist
```

Resultado: 59 pruebas, sin fallos. Wheel construido, revisado para comprobar código, fuentes y licencias, e instalado en un directorio aislado para verificar el arranque de la aplicación empaquetada. Capturas renderizadas con Qt offscreen a 1480 × 920 y 1080 × 720. Control de ventanas nativas pendiente por indisponibilidad del puente de Computer Use.
