# Plan técnico
## Fase 1 — MVP verificable
- Modelos de datos coherentes para áreas, flujos, relaciones SLP y estaciones.
- Backend: análisis de distancia Manhattan entre centroides y comprobación geométrica.
- Optimización de layout mediante búsqueda local factible (sin declarar óptimo global).
- Eventos discretos deterministas con conteo exacto de máquinas por estación.
- React + Three.js / React Three Fiber, datos primero y simulación después.
- Pruebas unitarias y CI.

## Fase 2 — Constructor avanzado
- Arrastre en 3D, snapping, validación en tiempo real, áreas irregulares y accesos.
- Corredores reales, algoritmo de rutas internas y colisiones de material handlers.
- Catálogo GLB/GLTF de equipos y escala métrica real.
- Importación/exportación versionada de escenarios y trazabilidad.

## Fase 3 — Modelos industriales
- Implementar y verificar variantes CRAFT, CORELAP, ALDEP.
- MPS, MRP, planificación agregada, MILP, balanceo de línea, Job Shop y Flow Shop.
- Motor SimPy: fallas MTBF/MTTR, lotes, mantenimientos, turnos y recursos.
- Monte Carlo, intervalos de confianza, calibración y análisis de sensibilidad.

## Fase 4 — Aplicación gerencial
- Análisis económico multiobjetivo y comparación de escenarios.
- Dashboard con métricas y gamificación de decisiones gerenciales.
- Autenticación, controles de acceso, auditoría y despliegue administrado.

No desplegar como aplicación de decisiones industriales certificada antes de validar datos reales, rutas, seguridad normativa y escenarios de producción.
