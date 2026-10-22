# Modelos de producción y SLP
## Implementados en MVP
- SLP: matriz de relaciones REL y flujos From-To.
- Distancia: Manhattan entre centroides de áreas rectangulares.
- Costo: suma de flujo por distancia por costo unitario de manejo.
- Mejoramiento local: traslaciones de áreas que mantienen restricciones geométricas.
- Simulación discreta determinista: recursos paralelos, esperas, movimientos y eventos.

## Pendientes (sin reclamar como implementados)
- Diseño SLP integral PQRST, áreas irregulares y recorridos sobre pasillos.
- CRAFT: heurística de mejora por intercambios.
- CORELAP: construcción relacional.
- ALDEP: generación de alternativas.
- QAP, MILP y optimización multiobjetivo del layout.
- MPS, MRP, PL/MILP multiperíodo, EOQ/EPQ y lot-sizing capacitado.
- Job Shop, Flow Shop, Flexible Job Shop, máquinas paralelas y SALBP.
- SimPy estocástico, Monte Carlo, fallas, mantenimiento y OEE.

## Criterios
Los códigos REL son preferencias cualitativas y sus ponderaciones deben ser configurables. La etiqueta X no constituye por sí sola una prohibición legal. Las restricciones de seguridad se modelarán por separado y deben bloquear diseños inseguros. Ningún indicador debe generarse desde una animación ficticia.
