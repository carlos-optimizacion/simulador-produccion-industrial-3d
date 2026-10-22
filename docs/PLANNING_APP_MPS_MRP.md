# Motor de planificación jerárquica — INDUSIM v0.4

El motor diferencia los tres niveles de decisión de la planificación industrial.

## 1. Planificación agregada (APP) — optimización MILP
Horizonte: 1–24 periodos, una familia homogénea de producción. Modelo de **programación lineal entera mixta** (implementado con todas las variables enteras) mediante SciPy/HiGHS.

**Decisiones por periodo:** trabajadores W, contrataciones H, ceses F, producción normal R, horas extra O, subcontratación S e inventario I.

Función objetivo:

```
Min  Σt (cW*W[t] + cH*H[t] + cF*F[t] + cR*R[t]
          + cO*O[t] + cS*S[t] + cI*I[t])
```

Con restricciones:
```
W[t] = W[t-1] + H[t] - F[t] (W[-1]=dotación inicial)
I[t] = I[t-1] + R[t] + O[t] + S[t] - D[t]
R[t] <= capacidad_regular_por_persona * W[t]
O[t] <= capacidad_extra_por_persona * W[t]
0 <= W[t] <= trabajadores_máximos
0 <= S[t] <= subcontratación_máxima_por_periodo
I[T-1] >= inventario_final_requerido
Todas las decisiones son enteras y no negativas.
```

**Interpretación de costos:** la remuneración fija por trabajador se suma al costo incremental de fabricar cada unidad. No incluir dos veces salarios bajo ambos conceptos.

## 2. Programa Maestro de Producción (MPS) — optimización MILP

El plan es por SKU y periodo. Los compromisos se agregan mediante `demanda efectiva = max(pronóstico, pedidos firmes)` en cada periodo; es una simplificación explícita de consumo de pronóstico, no una agregación de ambas series.

**Decisiones:** número entero de lotes terminados x[p,t] e inventario I[p,t].

```
Min Σp,t (cProd[p] * lote[p] * x[p,t] + cStock[p] * I[p,t])
I[p,t] = I[p,t-1] + lote[p] * x[p,t] - demandaEfectiva[p,t]
Σp lote[p] * x[p,t] * minutosPorUnidad[p] <= capacidadMinutos[t]
Σp lote[p] * x[p,t] <= capacidadUnidadesAPP[t] (si se suministra)
I[p,t] >= stockSeguridad[p]
x[p,t] = 0 si t < leadTimeFabricación[p]
```

Cada finalización genera la **liberación** de la orden de producción adelantada por el lead time en periodos.

## 3. MRP multinivel

A partir de finalizaciones de MPS y una BOM acíclica:
1. Desfasar las liberaciones de órdenes finales según su lead time.
2. Explotar necesidades dependientes en una BOM con cantidades por unidad padre.
3. Neto por periodo: inventario anterior + recepciones programadas − necesidades brutas, respetando stock de seguridad.
4. Lotificar mediante mínimo de pedido y múltiplos.
5. Desfasar órdenes de compra o fabricación por lead time.
6. Señalar órdenes que debieron liberarse **antes** del comienzo del horizonte, sin presentarlas como ejecutables automáticamente.

**MRP todavía no realiza optimización matemática de costos de proveedores, lotes conjuntos o capacidad de materiales.**

## Integración

`APP → MPS`: pasar `mps_internal_units_per_period` como `aggregate_capacity_units`, siempre que el usuario haya agregado productos en la misma familia, unidad y periodo. Verificar la compatibilidad del mix; una solución APP óptima no garantiza automáticamente un MPS factible.

`MPS → MRP`: pasar el diccionario `sku: planned_completions` del MPS como `mps_planned_completions`, y conservar el mismo lead time por producto en el catálogo MRP.

**Siguiente hito técnico:** reconciliación automática APP–MPS cuando falla la desagregación, integración de inventarios iniciales y unidades por producto/familia, restricciones de proveedor, lot-sizing capacitado y enlace con la simulación 3D de órdenes.
