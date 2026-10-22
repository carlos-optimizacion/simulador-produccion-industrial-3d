"""Finite-horizon single-item lot sizing benchmark from the MPS teaching slides.

Implements comparable heuristics and exact uncapacitated Wagner-Whitin DP.
This is NOT the finite-capacity multi-SKU MPS MILP in planning.py.
"""
from __future__ import annotations
from functools import lru_cache
from pydantic import BaseModel, Field, model_validator

class LotSizingRequest(BaseModel):
    demand: list[int] = Field(min_length=1, max_length=60)
    setup_cost: float = Field(ge=0)
    holding_cost_per_unit_period: float = Field(ge=0)
    unit_production_cost: float = Field(ge=0, default=0)
    period_label: str = "mes"

    @model_validator(mode="after")
    def check(self):
        if any(x < 0 for x in self.demand):
            raise ValueError("La demanda no puede ser negativa")
        return self

def evaluate(req: LotSizingRequest, production: list[int]) -> dict:
    if len(production) != len(req.demand) or any(q < 0 for q in production):
        raise ValueError("Programa de producción inválido")
    stock = 0
    inventory = []
    for quantity, requirement in zip(production, req.demand):
        stock += quantity-requirement
        if stock < 0:
            raise ValueError("Producción tardía o faltantes no permitidos")
        inventory.append(stock)
    if stock != 0:
        raise ValueError("Inventario remanente no necesario al final del horizonte")
    fixed = req.setup_cost * sum(q > 0 for q in production)
    holding = req.holding_cost_per_unit_period * sum(inventory)
    variable = req.unit_production_cost * sum(production)
    return {
      "production": production,
      "ending_inventory": inventory,
      "setups": sum(q > 0 for q in production),
      "setup_cost": round(fixed, 4),
      "holding_cost": round(holding, 4),
      "variable_cost": round(variable, 4),
      "relevant_cost": round(fixed+holding, 4),
      "total_cost": round(fixed+holding+variable, 4)
    }

def lot_for_lot(req: LotSizingRequest) -> list[int]:
    return list(req.demand)

def single_run(req: LotSizingRequest) -> list[int]:
    p = [0]*len(req.demand)
    if sum(req.demand):
        p[0] = sum(req.demand)
    return p

def silver_meal(req: LotSizingRequest) -> list[int]:
    """Least average setup+holding cost per period until next period raises it."""
    d=req.demand
    n=len(d)
    out=[0]*n
    t=0
    while t<n:
        if d[t]==0:
            t+=1
            continue
        last=t
        previous=req.setup_cost
        for end in range(t+1,n):
            holding=sum(req.holding_cost_per_unit_period*d[k]*(k-t)
                        for k in range(t,end+1))
            average=(req.setup_cost+holding)/(end-t+1)
            if average > previous + 1e-10:
                break
            previous=average
            last=end
        out[t]=sum(d[t:last+1])
        t=last+1
    return out

def least_unit_cost(req: LotSizingRequest) -> list[int]:
    d=req.demand
    out=[0]*len(d)
    t=0
    while t<len(d):
        if not d[t]:
            t+=1
            continue
        end=t
        previous=req.setup_cost/d[t]
        for k in range(t+1,len(d)):
            q=sum(d[t:k+1])
            if q==0:
                continue
            holding=req.holding_cost_per_unit_period*sum(
                d[j]*(j-t) for j in range(t,k+1))
            average=(req.setup_cost+holding)/q
            if average > previous+1e-10:
                break
            previous=average
            end=k
        out[t]=sum(d[t:end+1])
        t=end+1
    return out

def wagner_whitin(req: LotSizingRequest) -> list[int]:
    """Exact Wagner-Whitin DP for deterministic uncapacitated single-item lots."""
    d=req.demand
    n=len(d)
    holding=req.holding_cost_per_unit_period
    setup=req.setup_cost

    @lru_cache(None)
    def solve(t:int) -> tuple[float, tuple[tuple[int,int], ...]]:
        if t>=n:
            return (0.0, ())
        if d[t]==0:
            return solve(t+1)
        best_cost=float("inf")
        best_plan=()
        size=0
        holding_total=0.0
        for end in range(t,n):
            size += d[end]
            holding_total += holding*d[end]*(end-t)
            future, tail=solve(end+1)
            cost=setup+holding_total+future
            if cost < best_cost-1e-10:
                best_cost=cost
                best_plan=((t,size),)+tail
        return best_cost,best_plan

    _, selected=solve(0)
    production=[0]*n
    for t,q in selected:
        production[t]=q
    return production

def compare_lot_sizing(req: LotSizingRequest) -> dict:
    methods={
      "Correr en un tiempo":single_run(req),
      "Lote a lote (L4L)":lot_for_lot(req),
      "Silver-Meal":silver_meal(req),
      "Menor costo unitario (LUC)":least_unit_cost(req),
      "Wagner-Whitin (óptimo)":wagner_whitin(req)
    }
    results=[{"method":name,**evaluate(req,production)}
             for name,production in methods.items()]
    results.sort(key=lambda r:(r["relevant_cost"],r["setups"],r["method"]))
    optimal=next(r for r in results if r["method"].startswith("Wagner"))
    for result in results:
        if result["relevant_cost"] < optimal["relevant_cost"]-1e-5:
            raise AssertionError("Una heurística no puede mejorar el óptimo Wagner-Whitin")
        result["extra_cost_vs_optimal"]=round(
            result["relevant_cost"]-optimal["relevant_cost"],4)
    return {
      "problem":"Un solo producto, demanda determinista, horizonte finito, sin capacidad, sin faltantes ni lead time",
      "demand":req.demand,
      "setup_cost":req.setup_cost,
      "holding_cost_per_unit_period":req.holding_cost_per_unit_period,
      "period_label":req.period_label,
      "methods":results,
      "optimum_method":"Wagner-Whitin (óptimo)",
      "optimal_relevant_cost":optimal["relevant_cost"],
      "warning":"El óptimo Wagner-Whitin sólo aplica al problema no capacitado descrito. "
                "Con capacidad, varios SKU y setups de maquinaria usar MILP/CP-SAT."
    }

QUEENSTOWN_CASE = {
    "demand":[200,150,100,50,50,100,150,200,200,250,300,250],
    "setup_cost":500,
    "holding_cost_per_unit_period":1,
    "unit_production_cost":50,
    "period_label":"mes"
}
