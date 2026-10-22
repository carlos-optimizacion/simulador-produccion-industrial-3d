# Plan de verificación del MVP
1. Las áreas fuera de planta son inválidas.
2. Los pares de áreas deben respetar la separación geométrica configurada.
3. Los flujos deben referir áreas existentes.
4. El costo SLP calculado debe igualar la suma flujo × distancia × costo unitario.
5. La búsqueda local no puede empeorar el costo y debe mantener la factibilidad.
6. La simulación debe conservar exactamente la cantidad de equipos ingresada.
7. El número de eventos de terminación debe igualar el número de unidades.
8. El reloj de simulación y los eventos deben permanecer ordenados.
9. Configuración debe preceder al análisis y a la simulación.
10. No confundir Manhattan entre centroides con rutas transitables reales.

## Ejecutar
Desde backend: python -m pytest -q.
Desde frontend: npm install && npm run build.
El pipeline GitHub Actions ejecuta ambos procedimientos en push y pull request.
