"""Initial SLP analysis and feasible local search; NOT CRAFT or exact MILP."""
from __future__ import annotations
from .models import Plant,Area

REL_WEIGHTS={"A":5,"E":4,"I":3,"O":2,"U":0,"X":-5}

def center(area:Area)->tuple[float,float]:
    return (area.x+area.width/2,area.z+area.depth/2)

def distance(a:Area,b:Area)->float:
    p,q=center(a),center(b)
    return abs(p[0]-q[0])+abs(p[1]-q[1])

def collisions(plant:Plant)->list[dict]:
    problems=[]
    for a in plant.areas:
        if a.x < -1e-8 or a.z < -1e-8 or a.x+a.width > plant.width+1e-8 or a.z+a.depth > plant.depth+1e-8:
            problems.append({"type":"outside","areas":[a.id]})
    for i,a in enumerate(plant.areas):
        for b in plant.areas[i+1:]:
            xgap=max(a.x-(b.x+b.width), b.x-(a.x+a.width))
            zgap=max(a.z-(b.z+b.depth), b.z-(a.z+a.depth))
            if xgap < plant.clearance-1e-8 and zgap < plant.clearance-1e-8:
                problems.append({"type":"clearance","areas":[a.id,b.id]})
    return problems

def analyze(plant:Plant)->dict:
    areas={a.id:a for a in plant.areas}
    legs=[]
    for f in plant.flows:
        d=distance(areas[f.source],areas[f.target])
        legs.append({"source":f.source,"target":f.target,"distance_m":round(d,4),
          "units_per_shift":f.units_per_shift,"cost_per_unit_meter":f.cost_per_unit_meter,
          "cost_per_shift":round(d*f.units_per_shift*f.cost_per_unit_meter,4)})
    rel=[]
    for r in plant.relationships:
        d=distance(areas[r.source],areas[r.target])
        rel.append({"source":r.source,"target":r.target,"rating":r.rating,"reason":r.reason,
                    "distance_m":round(d,4),"preference_weight":REL_WEIGHTS[r.rating]})
    problems=collisions(plant)
    return {"valid":not problems,"violations":problems,"legs":legs,"relationships":rel,
      "material_handling_cost_per_shift":round(sum(x["cost_per_shift"] for x in legs),4),
      "material_handling_distance_m_units":round(sum(x["distance_m"]*x["units_per_shift"] for x in legs),4),
      "distance_method":"Manhattan entre centroides, sin modelamiento de rutas",
      "rel_note":"X es una preferencia REL; no reemplaza restricciones legales de seguridad."}

def improve(plant:Plant,steps:list[float]|None=None)->dict:
    if collisions(plant):
        raise ValueError("La distribución de partida viola los límites o separaciones.")
    steps=steps if steps is not None else [4,2,1]
    if any(step<=0 for step in steps):
        raise ValueError("Los pasos deben ser mayores que cero")
    current=plant.model_copy(deep=True)
    initial=analyze(current)["material_handling_cost_per_shift"]
    count=moves=0
    for step in steps:
        while True:
            best=current
            cost=analyze(current)["material_handling_cost_per_shift"]
            for idx,area in enumerate(current.areas):
                for dx,dz in [(-step,0),(step,0),(0,-step),(0,step)]:
                    trial=current.model_copy(deep=True)
                    trial.areas[idx]=area.model_copy(update={"x":round(area.x+dx,5),"z":round(area.z+dz,5)})
                    count+=1
                    if collisions(trial): continue
                    value=analyze(trial)["material_handling_cost_per_shift"]
                    if value<cost-1e-7:
                        best,cost=trial,value
            if best is current: break
            current=best
            moves+=1
    result=analyze(current)
    after=result["material_handling_cost_per_shift"]
    return {"plant":current.model_dump(),"before_cost":initial,"after_cost":after,
      "saving_pct":round(100*(initial-after)/initial,2) if initial else 0,
      "evaluated_candidates":count,"accepted_moves":moves,
      "algorithm":"Búsqueda local por traslaciones (no CRAFT ni óptimo global)","analysis":result}
