# Revisión técnica de las PPT: modelos APP, MPS y MRP para INDUSIM 3D

Fuentes suministradas por el usuario (revisión del 22 de octubre de 2026):
1. `Sem11_Planificación Agregada.pptx` — planificación agregada y S&OP (26 diapositivas).
2. `Sem9_Production - MPS.pptx` — MPS, lotificación y políticas de producción (53 diapositivas).
3. `Sem10_Production - MRP.pptx` — MRP I/II, BOM, requerimientos y optimización entre etapas (28 diapositivas).

## Diagnóstico: APP / S&OP
**Presentación Sem11, diapositivas 8–22.** El modelo matemático de la diapositiva 10 incluye fuerza laboral, contratación y cese; producción, horas extra, inventario, subcontratación y **backlog**. En el ejemplo Dire Wolf se trabaja con un horizonte mensual de entre 3 y 18 meses y se comparan estrategias y restricciones ("no despedir", "sin outsourcing", "horas extra costosas", etc.).

**Implementado v0.4**: programación entera de trabajadores, contrataciones, ceses, producción normal y extra, subcontratación e inventario, minimizando costos, sin faltantes.

**Faltantes obligatorios**:
- Backlog B[t] y penalidad por período con balance `I[t]-B[t] = I[t-1]-B[t-1]+P[t]+C[t]-D[t]`; evitar inventario y atraso simultáneos mediante justificación/modelo apropiado.
- Capacidad en horas, carga de recursos y horas extra por trabajador, sin confundir horas con unidades.
- Estrategias `nivelación`, `persecución`, `mixta`, `sin ceses`, `sin outsourcing`, `sin overtime` con comparación de costo total y factibilidad.
- Horizonte agregado típicamente mensual, 3–18 meses; corregir inventarios inicial/final y restricciones por política.
- Benchmarks y escenarios del ejercicio Dire Wolf, sin copiar un costo total como "óptimo" sin replicar exactamente supuestos y datos.

## Diagnóstico: MPS
**Presentación Sem9, diapositivas 18–49.** Se enseñan producción por nivelación y persecución; planeamiento contra demanda, ATP e inventario; estrategias MTS, MTO, ATO, ETO; lotificación unitaria y por periodos, FOQ y reglas especializadas (Silver-Meal, LUC, PPB), además de método exacto Wagner-Whitin y MILP con **variable binaria de setup** `z[t]`.

**Implementado v0.4**: MILP entero multi-SKU con inventario, stock de seguridad, lotes, lead time y capacidad finita en minutos y/o unidades APP. No incluye variables binarias de setup, costo fijo por corrida, ATP ni comparación de políticas.

**Nueva referencia ejecutable v0.4.x**:
- Caso Queenstown Kiwi-99 (diapositivas 32–49): `demand=[200,150,100,50,50,100,150,200,200,250,300,250]`, total 2,000 unidades, setup $500, fabricación $50/unidad, almacenamiento $1/unidad·mes.
- Endpoint `/api/planning/lot-sizing/compare`: compara "Correr en un tiempo", "Lote a lote", "Silver-Meal", "LUC" y "Wagner-Whitin". La última es óptima para un **único SKU sin restricciones de capacidad, con demanda conocida, sin faltantes ni lead time**.
- Cada plan reporta inventario por período, número y costo de setups, mantenimiento, costo variable y costo relevante; las heurísticas no tienen garantía de optimalidad.

**Pendientes**:
- FOQ/EOQ, cantidad de orden periódica POQ y balance parte-período PPB.
- MILP capacitado con `Q[t] <= CAP[t] z[t]`, setup fijo, variación de demanda, inventario, ATP y pedidos firmes que consumen previsión correctamente.
- Comparación del mínimo costo con carga/nivelación, e informe de desviaciones vs costo óptimo.

## Diagnóstico: MRP
**Presentación Sem10, diapositivas 4–24.** El MRP utiliza MPS, BOM e inventarios; muestra ejemplos con lead time 0 y mayor que 0, con y sin inventario disponible, y distingue MRP I de MRP II. La sección de "MRP simple, secuencial y simultáneo" compara la coordinación de fabricantes y componentes, costos de setup, holding y capacidades.

**Implementado v0.4**: BOM multinivel sin ciclos, explosion de necesidades, inventario inicial en componentes, lotificación, lead times, ordenes planeadas y advertencia de órdenes que se necesitarían antes del horizonte.

**Pendientes críticos**:
- Neto correcto de stock y recepciones programadas también para productos finales y subensambles planificados (ejercicio con inventarios A=30, B=10 y D=50 de las diapositivas 17–20).
- MRP capacitado/MRP II: carga por centro, capacidades por etapa y coordinación del MPS.
- Modelo secuencial vs modelo **simultáneo MILP** que minimice suma de costos de fabricantes y proveedores, considerando BOM, lead times, setup, capacidades, stock, transportes cuando corresponda y penalidades.
- Costos ilustrativos de la PPT (slides 22/23/24): $10,500 para ejemplo simple, $5,800 para enfoque secuencial y $8,700 para el denominado simultáneo. **Advertencia: el ejemplo secuencial tiene menor cifra ($5,800) que el simultáneo ($8,700); antes de atribuir una mejora a la coordinación simultánea hay que auditar comparabilidad de datos, restricciones y convenciones del caso.** No usar estas cifras como benchmark de optimalidad sin reconciliarlas.

## Integración gerencial con la fábrica 3D
1. APP determina la disponibilidad agregada de personas, horas y recursos.
2. MPS libera lotes por SKU y período respetando materiales y capacidad.
3. MRP crea órdenes para subensambles y compras, con rutas, tiempos y proveedor.
4. Motor de eventos sincroniza máquinas, materiales, esperas y órdenes; Three.js reproduce **sólo** esas actividades.
5. Comparador gerencial muestra costo, servicio, atrasos, capacidad y eficiencia de alternativas AS-IS y TO-BE.

### Prioridad de trabajo
P0: completar backlog y políticas APP; MPS con setup binario y costo; MRP que descuente inventario de raíz; pruebas reproducibles de Queenstown y Dire Wolf.
P1: escenarios MRP secuencial/simultáneo, integración automática APP/MPS/MRP y auditoría de capacidades.
P2: simulación con turnos, variabilidad, paradas y tablero gerencial 3D.

### Criterio de calidad
Los supuestos del modelo, el período temporal, las unidades, el costo, las diferencias entre heurística y óptimo y la factibilidad deben quedar explícitos para cada escenario.
