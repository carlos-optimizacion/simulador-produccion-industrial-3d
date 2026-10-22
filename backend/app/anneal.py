"""Reproducible simulated annealing for rectangular facility layouts.

Heuristic; cannot certify global optimality or real aisle travel distance.
"""
from __future__ import annotations
import math
import random
from pydantic import BaseModel, Field
from .models import Plant
from .slp import analyze,collisions
from .spatial import compare

class AnnealRequest(BaseModel):
    plant:Plant
    iterations:int=Field(default=1200,ge=1,le=20000)
    grid_step:float=Field(default=1,gt=0,le=10)
    temperature:float=Field(default=75,gt=0,le=1000000)
    cooling:float=Field(default=.995,gt=0,lt=1)
    seed:int=Field(default=42,ge=0,le=2147483647)

def optimize_annealing(req:AnnealRequest)->dict:
    original=req.plant
    if collisions(original):
        raise ValueError("La distribución AS-IS no es geométricamente factible")
    rng=random.Random(req.seed)
    current=original.model_copy(deep=True)
    current_cost=analyze(current)["material_handling_cost_per_shift"]
    best=current.model_copy(deep=True)
    best_cost=current_cost
    initial=current_cost
    temp=req.temperature
    considered=feasible=accepted_uphill=0
    history=[]
    for iteration in range(1,req.iterations+1):
        candidate=current.model_copy(deep=True)
        a=rng.randrange(len(candidate.areas))
        origin=candidate.areas[a]
        if rng.random()<.22:
            # Swap origins while preserving dimensions. Feasibility checked below.
            b=rng.randrange(len(candidate.areas)-1)
            if b>=a: b+=1
            other=candidate.areas[b]
            candidate.areas[a]=origin.model_copy(update={"x":other.x,"z":other.z})
            candidate.areas[b]=other.model_copy(update={"x":origin.x,"z":origin.z})
        else:
            if rng.random()<.23:
                # Global relocation on lattice (useful to escape nearby basins)
                max_x=math.floor((candidate.width-origin.width)/req.grid_step)
                max_z=math.floor((candidate.depth-origin.depth)/req.grid_step)
                if min(max_x,max_z)<0: continue
                x=rng.randint(0,max_x)*req.grid_step
                z=rng.randint(0,max_z)*req.grid_step
            else:
                step=req.grid_step*rng.choice([1,2,3,5])
                dx,dz=rng.choice([(step,0),(-step,0),(0,step),(0,-step)])
                x,z=origin.x+dx,origin.z+dz
            candidate.areas[a]=origin.model_copy(update={"x":round(x,6),"z":round(z,6)})
        considered+=1
        if collisions(candidate):
            temp*=req.cooling
            continue
        feasible+=1
        proposed_cost=analyze(candidate)["material_handling_cost_per_shift"]
        delta=proposed_cost-current_cost
        if delta<0 or rng.random()<math.exp(-max(0.0,delta)/max(temp,1e-12)):
            if delta>0: accepted_uphill+=1
            current,current_cost=candidate,proposed_cost
        if current_cost<best_cost-1e-8:
            best=current.model_copy(deep=True)
            best_cost=current_cost
        if iteration==1 or iteration%max(1,req.iterations//40)==0 or iteration==req.iterations:
            history.append({"iteration":iteration,"temperature":round(temp,6),
                            "best_cost":round(best_cost,4),"current_cost":round(current_cost,4)})
        temp*=req.cooling
    if best_cost>initial+1e-8:
        raise AssertionError("Best-of-run must not exceed initial cost")
    return {"plant":best.model_dump(),"before_cost":initial,"after_cost":best_cost,
            "saving_pct":round(100*(initial-best_cost)/initial,2) if initial else 0,
            "algorithm":"Recocido simulado, búsqueda heurística sin garantía de óptimo global",
            "parameters":{"iterations":req.iterations,"grid_step":req.grid_step,
                          "temperature":req.temperature,"cooling":req.cooling,"seed":req.seed},
            "valid_candidates":feasible,"considered_candidates":considered,
            "accepted_uphill":accepted_uphill,"history":history,
            "comparison":compare(original,best)}
