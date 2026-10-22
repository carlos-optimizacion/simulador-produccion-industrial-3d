"""Scenario-ready aggregate production planning (APP/S&OP) MILP.

Level, chase and mixed policies share exactly the same cost/volume assumptions.
Backlog/inventory exclusivity is enforced with an integral selector each period.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from .planning import _solve

Policy = Literal["mixed", "level", "chase", "no_layoffs", "no_outsourcing", "no_overtime"]

class APPScenario(BaseModel):
    demand: list[int] = Field(min_length=1, max_length=24)
    initial_workers: int = Field(ge=0)
    max_workers: int = Field(ge=0)
    initial_inventory: int = Field(ge=0, default=0)
    initial_backlog: int = Field(ge=0, default=0)
    target_ending_inventory: int = Field(ge=0, default=0)
    units_per_worker_period: int = Field(gt=0)
    overtime_units_per_worker: int = Field(ge=0, default=0)
    max_subcontract_per_period: int = Field(ge=0, default=0)
    worker_period_cost: float = Field(ge=0, default=1000)
    hiring_cost: float = Field(ge=0, default=250)
    layoff_cost: float = Field(ge=0, default=500)
    regular_unit_cost: float = Field(ge=0, default=10)
    overtime_unit_cost: float = Field(ge=0, default=18)
    subcontract_unit_cost: float = Field(ge=0, default=25)
    holding_unit_cost: float = Field(ge=0, default=1)
    backlog_unit_cost: float = Field(ge=0, default=10)
    allow_backlog: bool = False
    policy: Policy = "mixed"

    @model_validator(mode="after")
    def validate_parameters(self):
        if any(d < 0 for d in self.demand):
            raise ValueError("La demanda no puede ser negativa")
        if self.initial_workers > self.max_workers:
            raise ValueError("Dotación inicial mayor que el máximo permitido")
        if self.initial_inventory and self.initial_backlog:
            raise ValueError("Inventario y pedidos atrasados iniciales no pueden coexistir")
        if self.initial_backlog and not self.allow_backlog:
            raise ValueError("Debe habilitarse backlog para considerar pedidos atrasados iniciales")
        return self

LABELS = ("workers","hires","layoffs","regular","overtime",
          "subcontract","inventory","backlog","inventory_flag")

def optimize_app_scenario(req: APPScenario) -> dict:
    n = len(req.demand)
    ix = lambda t, name: t*len(LABELS)+LABELS.index(name)
    per_worker = req.units_per_worker_period
    per_extra = req.overtime_units_per_worker
    max_internal = req.max_workers*(per_worker+per_extra)
    max_inventory = max(1,req.initial_inventory+n*(max_internal+req.max_subcontract_per_period))
    max_backlog = max(1,req.initial_backlog+sum(req.demand))
    w = (req.worker_period_cost,req.hiring_cost,req.layoff_cost,
         req.regular_unit_cost,req.overtime_unit_cost,req.subcontract_unit_cost,
         req.holding_unit_cost,req.backlog_unit_cost,0)
    costs = list(w)*n
    upper = []
    rows = []
    for t,demand in enumerate(req.demand):
        overtime_cap = 0 if req.policy=="no_overtime" else req.max_workers*per_extra
        subcontract_cap = 0 if req.policy=="no_outsourcing" else req.max_subcontract_per_period
        layoff_cap = 0 if req.policy=="no_layoffs" else req.max_workers
        backlog_cap = max_backlog if req.allow_backlog else 0
        if req.policy=="chase":
            backlog_cap=0
        upper.extend([req.max_workers, req.max_workers, layoff_cap,
                      req.max_workers*per_worker, overtime_cap, subcontract_cap,
                      0 if req.policy=="chase" else max_inventory,
                      backlog_cap, 1])
        staff = {ix(t,"workers"):1, ix(t,"hires"):-1, ix(t,"layoffs"):1}
        if t:
            staff[ix(t-1,"workers")]=-1
        initial=req.initial_workers if t==0 else 0
        rows.append((staff, initial, initial))
        # I[t]-B[t] - R[t]-O[t]-S[t] - I[t-1]+B[t-1] = -D[t]
        balance={ix(t,"inventory"):1, ix(t,"backlog"):-1, ix(t,"regular"):-1,
                 ix(t,"overtime"):-1, ix(t,"subcontract"):-1}
        if t:
            balance[ix(t-1,"inventory")]=-1
            balance[ix(t-1,"backlog")]=1
        rhs=(req.initial_inventory-req.initial_backlog if t==0 else 0)-demand
        rows.append((balance, rhs, rhs))
        rows.append(({ix(t,"regular"):1, ix(t,"workers"):-per_worker},
                    float("-inf"),0))
        rows.append(({ix(t,"overtime"):1, ix(t,"workers"):-per_extra},
                    float("-inf"),0))
        # Mutual exclusion: flag=1 => inventory only; flag=0 => backlog only.
        rows.append(({ix(t,"inventory"):1, ix(t,"inventory_flag"):-max_inventory},
                     float("-inf"),0))
        rows.append(({ix(t,"backlog"):1, ix(t,"inventory_flag"):max_backlog},
                     float("-inf"),max_backlog))
        if t and req.policy=="level":
            rows.append(({ix(t,"regular"):1,ix(t-1,"regular"):-1},0,0))
            rows.append(({ix(t,"workers"):1,ix(t-1,"workers"):-1},0,0))
    rows.append(({ix(n-1,"inventory"):1},req.target_ending_inventory,float("inf")))
    # No backlog is accepted after the final period even if intermediate backlogging is allowed.
    rows.append(({ix(n-1,"backlog"):1},0,0))
    x=_solve(costs,upper,rows)
    periods=[]
    breakdown={k:0.0 for k in LABELS[:-1]}
    for t,d in enumerate(req.demand):
        row={"period":t+1,"demand":d}
        for label in LABELS[:-1]:
            row[label]=int(x[ix(t,label)])
            breakdown[label]+=row[label]*w[LABELS.index(label)]
        row["internal_production"]=row["regular"]+row["overtime"]
        row["available_regular_units"]=row["workers"]*per_worker
        row["available_extra_units"]=row["workers"]*per_extra
        if row["inventory"] and row["backlog"]:
            raise AssertionError("El modelo permite simultáneamente inventario y backlog")
        periods.append(row)
    return {
        "method":"APP MILP entero con backlog y políticas S&OP (HiGHS)",
        "policy":req.policy,"optimal":True,"periods":periods,
        "total_cost":round(sum(breakdown.values()),2),
        "cost_breakdown":{k:round(v,2) for k,v in breakdown.items()},
        "mps_internal_units_per_period":[p["internal_production"] for p in periods],
        "backlog_allowed":req.allow_backlog,
        "note":"Costos definidos por período y unidad de flujo homogénea. "
               "La comparación de políticas conserva la misma demanda, límites y costos."
    }

def compare_app_policies(base:APPScenario)->dict:
    policies=("mixed","level","chase","no_layoffs","no_outsourcing","no_overtime")
    outcomes=[]
    for name in policies:
        req=base.model_copy(update={"policy":name})
        try:
            result=optimize_app_scenario(req)
            outcomes.append({"policy":name,"status":"optimal",
                             "total_cost":result["total_cost"],
                             "periods":result["periods"]})
        except ValueError as exc:
            outcomes.append({"policy":name,"status":"infeasible",
                             "message":str(exc),"total_cost":None})
    feasible=[row for row in outcomes if row["status"]=="optimal"]
    best=min(feasible,key=lambda row:row["total_cost"]) if feasible else None
    return {"method":"Comparación de seis políticas APP con idénticos supuestos",
            "results":outcomes,
            "best_feasible_policy":best["policy"] if best else None,
            "best_total_cost":best["total_cost"] if best else None}
