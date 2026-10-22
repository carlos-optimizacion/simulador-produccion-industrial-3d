"""INDUSIM production planning: exact finite-horizon MILP APP and MPS (SciPy/HiGHS).

Not equivalent to full APS: calendar shifts, alternate resources and stochastic
demand require separate models. All quantities and staff are explicitly integral.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint

class AggregateRequest(BaseModel):
    demand: list[int] = Field(min_length=1,max_length=24)
    initial_workers: int = Field(ge=0)
    max_workers: int = Field(gt=0,le=10000)
    initial_inventory: int = Field(ge=0,default=0)
    target_ending_inventory: int = Field(ge=0,default=0)
    units_per_worker_period: int = Field(gt=0)
    overtime_units_per_worker: int = Field(ge=0,default=0)
    max_subcontract_per_period: int = Field(ge=0,default=0)
    worker_period_cost: float = Field(ge=0,default=1000)
    hiring_cost: float = Field(ge=0,default=250)
    layoff_cost: float = Field(ge=0,default=500)
    regular_unit_cost: float = Field(ge=0,default=10)
    overtime_unit_cost: float = Field(ge=0,default=18)
    subcontract_unit_cost: float = Field(ge=0,default=25)
    holding_unit_cost: float = Field(ge=0,default=1)

    @model_validator(mode="after")
    def validate_inputs(self):
        if any(d<0 for d in self.demand): raise ValueError("La demanda no puede ser negativa")
        if self.initial_workers>self.max_workers: raise ValueError("Personal inicial excede máximo")
        return self

class ProductSpec(BaseModel):
    sku:str = Field(min_length=1)
    initial_inventory:int = Field(ge=0,default=0)
    safety_stock:int = Field(ge=0,default=0)
    lot_size:int = Field(gt=0,default=1)
    manufacturing_lead_time:int = Field(ge=0,le=24,default=0)
    unit_production_cost:float = Field(ge=0,default=1)
    unit_holding_cost:float = Field(ge=0,default=0.2)
    setup_cost:float = Field(ge=0,default=0)

class MPSRequest(BaseModel):
    products:list[ProductSpec]=Field(min_length=1,max_length=20)
    forecast:dict[str,list[int]]
    firm_orders:dict[str,list[int]]=Field(default_factory=dict)
    minutes_per_unit:dict[str,float]
    available_minutes_per_period:list[float]=Field(min_length=1,max_length=24)
    aggregate_capacity_units:list[int]|None = None

    @model_validator(mode="after")
    def check(self):
        products={p.sku for p in self.products}
        if len(products)!=len(self.products): raise ValueError("SKU repetido")
        n=len(self.available_minutes_per_period)
        if any(v<0 for v in self.available_minutes_per_period): raise ValueError("Capacidad negativa")
        if set(self.forecast)!=products or set(self.minutes_per_unit)!=products:
            raise ValueError("Pronóstico y minutos por unidad requeridos para cada SKU")
        if any(key not in products for key in self.firm_orders):raise ValueError("Orden firme con SKU desconocido")
        for arr in [*self.forecast.values(),*self.firm_orders.values()]:
            if len(arr)!=n or any(x<0 for x in arr):raise ValueError("Horizonte y demanda inconsistentes")
        if any(v<=0 for v in self.minutes_per_unit.values()):raise ValueError("Tiempo unitario inválido")
        if self.aggregate_capacity_units is not None:
            if len(self.aggregate_capacity_units)!=n or any(x<0 for x in self.aggregate_capacity_units):
                raise ValueError("Capacidad APP inconsistente")
        return self

def _solve(cost:list[float],upper:list[float],constraints:list[tuple[dict[int,float],float,float]])->np.ndarray:
    """Build linear restrictions with coefficients for bounded equality/inequality rows."""
    length=len(cost)
    matrix=np.zeros((len(constraints),length))
    lb=np.zeros(len(constraints))
    ub=np.zeros(len(constraints))
    for i,(coeff,lo,hi) in enumerate(constraints):
        for key,val in coeff.items():matrix[i,key]=val
        lb[i],ub[i]=lo,hi
    result=milp(
        c=np.asarray(cost,dtype=float),
        integrality=np.ones(length,dtype=int),
        bounds=Bounds(np.zeros(length),np.asarray(upper,dtype=float)),
        constraints=[LinearConstraint(matrix,lb,ub)],
        options={"time_limit":20,"mip_rel_gap":0.0001}
    )
    if not result.success or result.x is None:
        raise ValueError("No se encontró solución óptima factible con las capacidades y restricciones del horizonte. "
                         f"HiGHS status={result.status}")
    values=np.rint(result.x).astype(int)
    if not (np.all(values>=0) and np.max(np.abs(matrix@values-np.minimum(np.maximum(matrix@values,lb),ub)))<1e-5):
        raise ValueError("Inconsistencia numérica de la solución entera")
    return values

def optimize_aggregate(req:AggregateRequest)->dict:
    # Per-period decision variables: workforce, hires, layoffs, regular,
    # overtime, subcontract, ending inventory.
    n=len(req.demand)
    fields=["workers","hires","layoffs","regular","overtime","subcontract","inventory"]
    i=lambda t,k: t*7+fields.index(k)
    weights=[req.worker_period_cost,req.hiring_cost,req.layoff_cost,
             req.regular_unit_cost,req.overtime_unit_cost,
             req.subcontract_unit_cost,req.holding_unit_cost]
    cost=weights*n
    upper=[]
    for _ in range(n):
        upper.extend([req.max_workers,req.max_workers,req.max_workers,
                      req.max_workers*req.units_per_worker_period,
                      req.max_workers*req.overtime_units_per_worker,
                      req.max_subcontract_per_period,np.inf])
    rows=[]
    for t,d in enumerate(req.demand):
        w={i(t,"workers"):1,i(t,"hires"):-1,i(t,"layoffs"):1}
        if t>0:w[i(t-1,"workers")]=-1
        rows.append((w,req.initial_workers if t==0 else 0,req.initial_workers if t==0 else 0))
        inventory={i(t,"inventory"):1,i(t,"regular"):-1,
                   i(t,"overtime"):-1,i(t,"subcontract"):-1}
        if t>0:inventory[i(t-1,"inventory")]=-1
        rhs=req.initial_inventory-d if t==0 else -d
        rows.append((inventory,rhs,rhs))
        rows.append(({i(t,"regular"):1,i(t,"workers"):-req.units_per_worker_period},
                     -np.inf,0))
        rows.append(({i(t,"overtime"):1,i(t,"workers"):-req.overtime_units_per_worker},
                     -np.inf,0))
    rows.append(({i(n-1,"inventory"):1},req.target_ending_inventory,np.inf))
    x=_solve(cost,upper,rows)
    periods=[]
    breakdown={k:0.0 for k in fields}
    for t,d in enumerate(req.demand):
        row={"period":t+1,"demand":d}
        for k in fields:row[k]=int(x[i(t,k)])
        if t==0:
            available=req.initial_inventory+row["regular"]+row["overtime"]+row["subcontract"]
        else:
            available=periods[-1]["inventory"]+row["regular"]+row["overtime"]+row["subcontract"]
        assert available-d==row["inventory"]
        for k,w in zip(fields,weights):breakdown[k]+=row[k]*w
        row["internal_production"]=row["regular"]+row["overtime"]
        row["regular_capacity_units"]=row["workers"]*req.units_per_worker_period
        row["overtime_capacity_units"]=row["workers"]*req.overtime_units_per_worker
        row["workforce_utilization_pct"]=round(
            100*row["regular"]/row["regular_capacity_units"],2) if row["regular_capacity_units"] else 0
        periods.append(row)
    return {"method":"APP MILP entero — scipy.optimize.milp / HiGHS",
            "optimal":True,"periods":periods,
            "cost_breakdown":{k:round(v,2) for k,v in breakdown.items()},
            "total_cost":round(sum(breakdown.values()),2),
            "mps_internal_units_per_period":[p["internal_production"] for p in periods],
            "assumptions":["Demanda conocida por periodo","Sin atrasos de entrega",
              "Los salarios y costos variables se suman; unidades homogéneas por familia",
              "No incluye cambios de productividad ni calendarios diarios"]}

def optimize_mps(req:MPSRequest)->dict:
    """Capacity-constrained integer lot scheduling with binary setup indicators.

    Cost = produced quantity * unit cost + held inventory + fixed run cost.
    Includes a limited noncumulative ATP for firm customer orders.
    """
    import math
    horizon=len(req.available_minutes_per_period)
    idx=lambda p,t,k:3*(p*horizon+t)+k
    unit_demand={p.sku:[max(req.forecast[p.sku][t],
                             req.firm_orders.get(p.sku,[0]*horizon)[t])
                         for t in range(horizon)] for p in req.products}
    costs=[];upper=[];rows=[]
    for p,product in enumerate(req.products):
        for t in range(horizon):
            max_units=sum(unit_demand[product.sku][t:])+product.safety_stock
            max_lots=max(1,math.ceil(max_units/product.lot_size))
            if t<product.manufacturing_lead_time:max_lots=0
            costs.extend([product.lot_size*product.unit_production_cost,
                          product.unit_holding_cost,product.setup_cost])
            # lots, inventory, binary setup
            upper.extend([max_lots,np.inf,1 if max_lots else 0])
            balance={idx(p,t,1):1,idx(p,t,0):-product.lot_size}
            if t>0:balance[idx(p,t-1,1)]=-1
            rhs=(product.initial_inventory if t==0 else 0)-unit_demand[product.sku][t]
            rows.append((balance,rhs,rhs))
            rows.append(({idx(p,t,1):1},product.safety_stock,np.inf))
            rows.append(({idx(p,t,0):1,idx(p,t,2):-max_lots},-np.inf,0))
            # A setup is charged if and only if at least one lot is completed.
            rows.append(({idx(p,t,2):1,idx(p,t,0):-1},-np.inf,0))
    for t,available in enumerate(req.available_minutes_per_period):
        capacity={idx(p,t,0):spec.lot_size*req.minutes_per_unit[spec.sku]
             for p,spec in enumerate(req.products)}
        rows.append((capacity,-np.inf,available))
        if req.aggregate_capacity_units is not None:
            limit={idx(p,t,0):spec.lot_size for p,spec in enumerate(req.products)}
            rows.append((limit,-np.inf,req.aggregate_capacity_units[t]))
    x=_solve(costs,upper,rows)
    results=[]
    for p,product in enumerate(req.products):
        completion=[int(x[idx(p,t,0)])*product.lot_size for t in range(horizon)]
        ending=[int(x[idx(p,t,1)]) for t in range(horizon)]
        setups=[int(x[idx(p,t,2)]) for t in range(horizon)]
        release=[0]*horizon
        for t,qty in enumerate(completion):
            if qty:
                release[t-product.manufacturing_lead_time]+=qty
        firm=req.firm_orders.get(product.sku,[0]*horizon)
        atp=[None]*horizon
        for t in range(horizon):
            if t==0 or completion[t]:
                next_run=next((u for u in range(t+1,horizon) if completion[u]>0),horizon)
                atp[t]=(product.initial_inventory if t==0 else 0)+completion[t]-sum(firm[t:next_run])
        results.append({"sku":product.sku,"effective_demand":unit_demand[product.sku],
                        "planned_completions":completion,"planned_releases":release,
                        "projected_ending_inventory":ending,"lot_size":product.lot_size,
                        "manufacturing_lead_time":product.manufacturing_lead_time,
                        "setups":setups,"setup_cost":product.setup_cost,
                        "total_setup_cost":round(sum(setups)*product.setup_cost,2),
                        "atp_non_cumulative":atp})
    capacity_used=[
        round(sum(x[idx(p,t,0)]*spec.lot_size*req.minutes_per_unit[spec.sku]
                  for p,spec in enumerate(req.products)),3)
        for t in range(horizon)]
    return {"method":"MPS MILP con setup binario, lotes y capacidad finita",
            "optimal":True,"periods":horizon,"products":results,
            "capacity_used_minutes":capacity_used,
            "available_minutes_per_period":req.available_minutes_per_period,
            "total_cost":round(float(sum(a*b for a,b in zip(x,costs))),2),
            "demand_policy":"max(pronóstico, pedidos firmes) por SKU y periodo; aproximación",
            "note":"ATP no acumulativo = inventario inicial (solo período 1) más MPS disponible "
                   "menos pedidos firmes hasta la siguiente recepción MPS. "
                   "El cálculo no incluye consumo real de pronóstico ni ATP acumulado. "
                   "Setups, liberaciones y terminaciones están sujetos a la capacidad declarada."}
