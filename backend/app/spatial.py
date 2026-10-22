"""Cartesian floor-plan analysis and strictly comparable AS-IS / TO-BE reporting.

Coordinates use a local metric datum: X,Z in Three.js; X,Y on a 2-D plan.
Actual obstacle-aware aisle path lengths are *not* computed by this module.
"""
from __future__ import annotations
from .models import Plant
from .slp import analyze, center, collisions, REL_WEIGHTS

def coordinate_map(plant: Plant) -> dict:
    nodes=[]
    for a in plant.areas:
        cx,cy = center(a)
        nodes.append({
            "id":a.id,"name":a.name,
            "origin_xy_m":[a.x,a.z],
            "center_xy_m":[round(cx,4),round(cy,4)],
            "corners_xy_m":[[a.x,a.z],[a.x+a.width,a.z],
                            [a.x+a.width,a.z+a.depth],[a.x,a.z+a.depth]],
            "area_m2":round(a.width*a.depth,4)
        })
    return {"reference_system":"Local Cartesian X,Y in meters; Three.js X,Z",
            "origin_xy_m":[0,0],"plant_dimensions_m":[plant.width,plant.depth],
            "nodes":nodes}

def corelap_priorities(plant: Plant) -> dict:
    """TCR prioritization only; this is NOT full geometric CORELAP placement."""
    scores={a.id:0 for a in plant.areas}
    connections={a.id:[] for a in plant.areas}
    for link in plant.relationships:
        weight=REL_WEIGHTS[link.rating]
        scores[link.source]+=weight
        scores[link.target]+=weight
        connections[link.source].append({"other":link.target,"rating":link.rating,"weight":weight})
        connections[link.target].append({"other":link.source,"rating":link.rating,"weight":weight})
    ordered=sorted(plant.areas,key=lambda a:(-scores[a.id],-len(connections[a.id]),a.id))
    return {"method":"CORELAP: TCR y orden relacional (sin colocación geométrica)",
            "weights":REL_WEIGHTS,
            "priority":[{"rank":i+1,"area_id":a.id,"area_name":a.name,
                         "tcr":scores[a.id],"relations":connections[a.id],
                         "center_xy_m":list(center(a))} for i,a in enumerate(ordered)],
            "note":"Ponderaciones configuradas como valores heurísticos iniciales, no normas universales."}

def compare(as_is:Plant,to_be:Plant)->dict:
    if collisions(as_is) or collisions(to_be):
        raise ValueError("AS-IS y TO-BE deben respetar límites y distancias geométricas mínimas")
    if (as_is.width,as_is.depth,as_is.clearance)!=(to_be.width,to_be.depth,to_be.clearance):
        raise ValueError("No es comparable: el perímetro o la separación cambió entre escenarios")
    current={a.id:a for a in as_is.areas}
    target={a.id:a for a in to_be.areas}
    if current.keys()!=target.keys():
        raise ValueError("No es comparable: las áreas difieren entre escenarios")
    for id in current:
        a,b=current[id],target[id]
        if (a.width,a.depth)!=(b.width,b.depth):
            raise ValueError("No es comparable: cambian dimensiones de un área")
    if ([f.model_dump() for f in as_is.flows] != [f.model_dump() for f in to_be.flows] or
        [r.model_dump() for r in as_is.relationships]!=[r.model_dump() for r in to_be.relationships]):
        raise ValueError("No es comparable: flujos, costos o relaciones SLP cambiaron")
    a,b=analyze(as_is),analyze(to_be)
    original=a["material_handling_cost_per_shift"]
    proposed=b["material_handling_cost_per_shift"]
    comparison=[]
    for leg_a,leg_b in zip(a["legs"],b["legs"]):
        comparison.append({"source":leg_a["source"],"target":leg_a["target"],
                           "as_is_distance_m":leg_a["distance_m"],
                           "to_be_distance_m":leg_b["distance_m"],
                           "as_is_cost_per_shift":leg_a["cost_per_shift"],
                           "to_be_cost_per_shift":leg_b["cost_per_shift"],
                           "saving_per_shift":round(leg_a["cost_per_shift"]-leg_b["cost_per_shift"],4)})
    relocations=[]
    for id,source in current.items():
        start=center(source)
        end=center(target[id])
        relocations.append({"area_id":id,"name":source.name,
              "from_xy_m":[round(v,4) for v in start],
              "to_xy_m":[round(v,4) for v in end],
              "displacement_m":round(abs(start[0]-end[0])+abs(start[1]-end[1]),4)})
    return {
      "as_is":{"plant":as_is.model_dump(),"analysis":a,"map":coordinate_map(as_is)},
      "to_be":{"plant":to_be.model_dump(),"analysis":b,"map":coordinate_map(to_be)},
      "cost_before":original,"cost_after":proposed,
      "saving_per_shift":round(original-proposed,4),
      "saving_pct":round(100*(original-proposed)/original,2) if original else 0,
      "material_handling_weighted_distance_before":a["material_handling_distance_m_units"],
      "material_handling_weighted_distance_after":b["material_handling_distance_m_units"],
      "flows":comparison,"relocations":relocations,
      "method":"Manhattan entre centroides locales, no rutas reales",
      "currency":"PEN"}
