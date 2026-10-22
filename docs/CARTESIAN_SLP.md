# INDUSIM 3D — Coordenadas cartesianas, SLP y AS-IS / TO-BE (v0.3)

## Referencia métrica
- **Planta 2D**: sistema local con origen (0,0) metros, X horizontal, Y vertical en el dibujo.
- **Three.js**: el mismo plano se representa horizontalmente como X,Z, y **Y** se reserva a la altura.
- Cada área se describe por origen inferior-izquierdo (x,z), anchura, profundidad y centroide (x+w/2, z+d/2).
- Un plano georreferenciado de exteriores podría integrarse en el futuro, pero **coordenadas geocéntricas terrestres/GPS no son necesarias ni mejoran la precisión** de un recorrido dentro de la planta.
- El plano actual representa áreas rectangulares y centroides; no se confunde la distancia entre ellos con la distancia real de transporte.

## Distancias y costos
Para cada flujo dirigido i→j:
```
D_ij = |centro_x(i) - centro_x(j)| + |centro_y(i) - centro_y(j)|  [m]
Costo_ij = volumen_ij [unidades/turno] × D_ij [m] × tarifa_ij [S/ por unidad·m]
Costo_total = suma(Costo_ij)  [S/ por turno]
```
La distancia es **Manhattan entre centroides**: una aproximación preliminar, sin pasillos, muros, puertas, montacargas, desniveles ni obstáculos reales. Para decisiones de ingeniería usaremos la distancia más corta en una red de pasillos transitable y puntos de transferencia verificados.

## Línea base AS-IS y propuesta TO-BE
- AS-IS es la distribución guardada al iniciar una evaluación desde Configuración.
- TO-BE es una copia editable; mover áreas o optimizar no modifica la línea base.
- `/api/slp/compare` acepta ambos planos e **impide comparar** si cambian áreas, dimensiones, matriz From-To, costos, relaciones REL, límites o separaciones.
- Comparación incluye costo de cada recorrido, distancia ponderada por volumen, ahorro y desplazamiento de cada centroide.
- El JSON de escenario v2 conserva ambos planos; importaciones de v1 siguen siendo aceptadas.
- El ahorro por turno **no equivale a VAN/TIR ni justifica una inversión** sin incluir el costo de reubicar equipos, paros, obra civil y verificación técnica.

## CORELAP
- `/api/slp/corelap/order` calcula TCR (Total Closeness Rating) sumando pesos de la matriz REL (A=5, E=4, I=3, O=2, U=0, X=−5).
- Genera una **prioridad relacional inicial**, no el layout construido por el CORELAP clásico (la fase de colocación geométrica está pendiente).
- Los pesos son configuraciones iniciales del prototipo; **una relación X no reemplaza una restricción legal ni de seguridad**.

## Recocido simulado
- `/api/slp/anneal`: algoritmo estocástico con semilla reproducible, temperatura inicial, enfriamiento geométrico, iteraciones y cuadrícula.
- Movimientos: translación de una zona, reubicación aleatoria en una rejilla, intercambio de posiciones.
- Se rechazan candidatos con conflictos de geometría y se registra el mejor candidato observado.
- La probabilidad de aceptar un movimiento que aumenta el costo es `exp(-Δ/T)`; permite abandonar mínimos locales.
- **No garantiza óptimo global** y por ahora minimiza solo costo de manejo de materiales.
- Concluir la ingeniería de layout exige restricciones reales de pasillos, áreas de seguridad, puertas y rutas de evacuación.

## Próximos hitos
1. Constructor CORELAP geométrico con áreas, preferencias y restricciones.
2. Puntos de entrada/salida por zona y grafo transitable de corredores; distancias reales por A*/Dijkstra.
3. Optimización híbrida: CORELAP/CRAFT + recocido simulado + restricciones.
4. Comparación económico-productiva AS-IS vs TO-BE con simulación simultánea, costos de implementación y reportes.
