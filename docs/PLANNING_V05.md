# INDUSIM 3D — Planificación avanzada APP/MPS/MRP (v0.5)

Se utilizaron las presentaciones facilitadas por el usuario: **Sem11_Planificación Agregada**, **Sem9_Production - MPS** y **Sem10_Production - MRP**. Los ejemplos y criterios aquí descritos son educativos y no equivalen a datos calibrados de una planta.

## APP / S&OP — políticas, costos y backlog

`POST /api/planning/aggregate/v2` resuelve un MILP entero con demanda y costos por período; `POST /api/planning/aggregate/scenarios` compara políticas homogéneas: mixta, nivelación, persecución, sin despidos, sin outsourcing y sin horas extra.

Decisiones por período: trabajadores W, contrataciones H, ceses F, producción normal R, horas extra O, subcontratación S, inventario I y pedidos atrasados B.

Balance: `W[t] = W[t-1]+H[t]-F[t]`, y `I[t]-B[t] = I[t-1]-B[t-1]+R[t]+O[t]+S[t]-D[t]`.

Una variable binaria impide inventario y atraso simultáneos, el backlog final se fija en cero, y se consideran costos de personal, contratación, ceses, producción, horas extra, inventario, subcontratación y penalizaciones de atraso. Si una política es inviable se informa explícitamente.

**Límites**: trabaja en unidades homogéneas por trabajador y período, no todavía en horas de máquina/turno ni con calendarios industriales. Las políticas de nivelación fijan producción regular y personal constantes; persecución fija inventario y backlog a cero. No se declara que una política restringida supere a la mixta sin demostrarlo.

## MPS — variable de setup y ATP

`POST /api/planning/mps` continúa optimizando enteros por SKU y período y ahora admite `setup_cost` en cada producto. El binario de preparación se enlaza a la decisión de producir mediante dos restricciones: `lotes[p,t] <= M[p,t]·y[p,t]`, `y[p,t] <= lotes[p,t]`, y `y[p,t] ∈ {0,1}`. Se minimizan fabricación variable, almacenamiento y costo fijo de preparaciones.

El resultado incluye `setups`, `total_setup_cost` y `atp_non_cumulative`, un ATP simple que calcula inventario inicial (solamente en el primer período) más recepciones planificadas MPS, menos pedidos firmes hasta la siguiente recepción. El consumo de pronóstico y ATP acumulativo siguen pendientes.

La comparación independiente Queenstown (v0.4.1) conserva las reglas lote-a-lote, una corrida, Silver-Meal, costo unitario y Wagner-Whitin óptimo sólo en el caso unicompontente no capacitado.

## MRP — reconciliación de existencias de productos finales

`POST /api/planning/mrp` admite además `end_item_gross_requirements` por SKU final. Revisa su inventario en mano, recepciones confirmadas, terminaciones MPS y demanda final; informa faltantes mediante `end_item_shortages` y calcula inventario disponible por período.

**No se explota la demanda final directamente a componentes** si ya existe producto terminado. Los componentes dependen de las **órdenes de fabricación liberadas**, evitando duplicar materiales cuando existe stock final.

Si los datos de demanda final no se suministran, el sistema indica `inventory_validation=not_provided` para productos finales; no inventa información de cobertura. Las liberaciones anteriores al horizonte siguen siendo advertencias, no abastecimiento garantizado.

## Validación y siguientes fases

Pruebas: balances de W e inventario-backlog, infeasibilidad, capacidad, consistencia de políticas, setup binario, consolidación por costos fijos, inventario de productos finales, BOM y rutas API. GitHub Actions ejecuta `pytest` y compilación frontend.

Pendientes: reproducción integral Dire Wolf bajo supuestos contrastados de la PPT, MPS con setup de máquina y calendario, consumo real de pronóstico, CRP/MRP II y simultáneo MILP de fabricantes/proveedores, integración automática de órdenes APP/MPS/MRP con SimPy y Three.js.

**Importante:** APP y MPS siguen siendo optimizaciones jerárquicas separadas, no una formulación global; un MPS inviable no se corrige automáticamente. MRP es determinista y no optimiza proveedores en esta fase.
