# INDUSIM 3D · Simulador integral de producción industrial
[![INDUSIM 3D checks](https://github.com/carlos-optimizacion/simulador-produccion-industrial-3d/actions/workflows/ci.yml/badge.svg)](https://github.com/carlos-optimizacion/simulador-produccion-industrial-3d/actions/workflows/ci.yml)

**v0.5 · Prototipo funcional en desarrollo (no sistema industrial certificado).**

Herramienta para comparar distribuciones de planta, analizar flujos SLP y visualizar **simulaciones de producción en un entorno tridimensional con Three.js / React Three Fiber**. La configuración de recursos se realiza antes del análisis y de la simulación.

## Funcionalidades implementadas
- Planificación agregada (APP), MPS con capacidad y MRP multinivel en v0.4; desde v0.5, política de backlog APP y seis escenarios, setups binarios en MPS con ATP preliminar y auditoría de inventario final en MRP.
- Comparación de lotificación de MPS (L4L, una sola corrida, Silver-Meal, LUC, Wagner-Whitin) en v0.4.1, basada en el caso docente Queenstown.
- Configuración de dimensiones de planta, áreas rectangulares, separación y flujos From-To.
- Matriz de relaciones **REL** A/E/I/O/U/X con motivos.
- **Plano cartesiano métrico** X,Y (X,Z en Three.js), centros geométricos y trazos From-To.
- Comparación **AS-IS vs. TO-BE** con línea base fija y validación de las mismas áreas, demanda, costos y restricciones.
- Priorización de CORELAP por **TCR** (orden relacional; colocación completa pendiente).
- **Recocido simulado** (semilla reproducible, restricciones geométricas, alternativas TO-BE y costo mínimo encontrado).
- Cálculo SLP preliminar: distancias Manhattan entre centroides y costo de manejo por turno.
- Validación geométrica: límites de planta y separaciones entre áreas.
- Optimización **local por traslaciones** que acepta únicamente mejoras factibles; **no** es CRAFT ni garantiza óptimo global.
- Escena 3D Three.js: selección y **arrastre de áreas** con ajuste a rejilla (0.25/0.5/1 m), rechazo de colisiones y distancias mínimas; máquinas por instancia y flujos visuales.
- Simulación discreta determinista: colas FIFO, **operaciones simultáneas**, máquinas individuales identificadas, movimientos y finalización de órdenes.
- Controles de reproducción, pausa, reloj virtual y resumen de productividad y utilización.
- Importación y exportación de escenarios JSON independientes (v2 conserva AS-IS y TO-BE; se aceptan v1) con validación en FastAPI.
- Pruebas automatizadas Python (incluyen simultaneidad, identidad de máquinas e importación) y compilación TypeScript/Vite en GitHub Actions.

## Limitaciones
- El APP todavía no incorpora backlog y políticas comparables tipo Dire Wolf; MPS no incluye setup binario en el MILP multi-SKU; MRP sigue sin programación simultánea de compras/producción.
- Las distancias son rectilíneas **entre centroides**, no rutas reales por pasillos.
- El arrastre y el rechazo geométrico simplificado están implementados; faltan rotación, puertas, pasillos navegables y validaciones normativas de seguridad o evacuación.
- Las relaciones REL son preferencias cualitativas; **X no sustituye una restricción legal**.
- El motor aún no usa SimPy ni modela fallas, mantenimiento, turnos, incertidumbre o rutas de productos diferenciadas.
- CRAFT, la **colocación geométrica completa de CORELAP**, ALDEP, PL/MILP, MPS/MRP y Job/Flow Shop están **planificados**, no implementados.
- El render 3D utiliza representaciones geométricas simplificadas; faltan modelos industriales GLTF y logística física.
- Los resultados son demostrativos y no sustentan decisiones de inversión sin contrastarlos con datos de operación.

## Estructura
```text
backend/app/          Contratos Pydantic, motor SLP y simulación
backend/tests/        Pruebas unitarias y de integración de API
frontend/src/         React, TypeScript y escena 3D Three.js
docs/                 Modelos, criterios de validación y roadmap
.github/workflows/    GitHub Actions: pruebas y compilación
render.yaml           Blueprint de despliegue sugerido (no desplegado)
```

## Ejecutar localmente
**Requisitos:** Python 3.11+, Node.js 22 y npm.

Terminal 1:
```bash
cd backend
python -m venv .venv
# Linux / macOS: source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API en http://localhost:8000/docs

Terminal 2:
```bash
cd frontend
npm install
npm run dev
```
Abre http://localhost:5173.

Para una API no local, copia `frontend/.env.example` a `frontend/.env` y cambia `VITE_API_URL`.

## Pruebas
```bash
cd backend
python -m pytest -q
cd ../frontend
npm install
npm run build
```

## API
| Método | Ruta | Función |
|---|---|---|
| GET | /api/health | Estado del servicio |
| GET | /api/demo | Datos del escenario demostrativo |
| POST | /api/slp/analyze | Análisis de layout (objeto Plant) |
| POST | /api/slp/optimize | Búsqueda local de distribución factible |
| POST | /api/production/simulate | Simulación determinista y eventos |
| POST | /api/scenarios/validate | Validación JSON v1/v2 y línea base AS-IS |
| POST | /api/slp/coordinates | Puntos cartesianos de áreas y centroides |
| POST | /api/slp/corelap/order | Prioridades TCR de CORELAP |
| POST | /api/slp/compare | Costos y recorridos AS-IS / TO-BE |
| POST | /api/slp/anneal | Optimización con recocido simulado |

**Auditoría de modelos de las PPT aportadas:** [docs/REVIEW_PPT_APP_MPS_MRP.md](docs/REVIEW_PPT_APP_MPS_MRP.md).

**Guía técnica v0.5:** [docs/PLANNING_V05.md](docs/PLANNING_V05.md).

## Próximas fases
- [Constructor 3D editable, validación geométrica y JSON](issues/1)
- [Implementar CRAFT, CORELAP, ALDEP y rutas internas](issues/2)
- [SimPy, programación matemática y planificación](issues/3)
- [Accesos, pasillos y rutas transitables cartesianas](issues/6)

**Especificación espacial:** [docs/CARTESIAN_SLP.md](docs/CARTESIAN_SLP.md).

En Render, el archivo `render.yaml` está preparado como referencia. Antes de desplegar, verificar nombres, URL efectivas, CORS, límites de recursos y política de acceso. **La mera presencia de este archivo no implica que los servicios estén activos.**

**Criterio de ingeniería:** las cantidades representadas en 3D deben corresponder a las entradas; las métricas proceden del motor, nunca de animaciones arbitrarias.
