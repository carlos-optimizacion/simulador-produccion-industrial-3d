import os
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from .models import Plant,LayoutRequest,ProductionRequest,Scenario
from .slp import analyze,improve
from .simulation import simulate
from .sample import SAMPLE_PLANT,SAMPLE_PRODUCTION
from .spatial import compare,coordinate_map,corelap_priorities
from .anneal import AnnealRequest,optimize_annealing
from .planning import AggregateRequest, MPSRequest, optimize_aggregate, optimize_mps
from .mrp import MRPRequest, explode_mrp
from .lot_sizing import LotSizingRequest, QUEENSTOWN_CASE, compare_lot_sizing

class CompareRequest(BaseModel):
    as_is:Plant
    to_be:Plant

app=FastAPI(title="INDUSIM 3D API",version="0.4.1")
origins=["http://localhost:5173","http://127.0.0.1:5173"]
if os.getenv("FRONTEND_ORIGIN"): origins.append(os.environ["FRONTEND_ORIGIN"].rstrip("/"))
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,
                   allow_methods=["GET","POST"],allow_headers=["Content-Type"])
@app.get("/api/health")
def health(): return {"status":"ok","version":"0.4.1"}
@app.get("/api/demo")
def demo(): return {"plant":SAMPLE_PLANT,"production":SAMPLE_PRODUCTION}
@app.post("/api/slp/analyze")
def slp_analyze(plant:Plant): return analyze(plant)
@app.post("/api/slp/optimize")
def slp_optimize(data:LayoutRequest):
    try: return improve(data.plant,data.steps)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
@app.post("/api/production/simulate")
def production_simulate(req:ProductionRequest):
    if not analyze(req.plant)["valid"]: raise HTTPException(422,"Distribución inviable")
    return simulate(req)

@app.post("/api/scenarios/validate")
def scenario_validate(scenario:Scenario):
    if not analyze(scenario.plant)["valid"]:
        raise HTTPException(422,"El escenario contiene conflictos geométricos.")
    if scenario.as_is is not None:
        try: compare(scenario.as_is,scenario.plant)
        except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    return scenario.model_dump()

@app.post("/api/slp/coordinates")
def slp_coordinates(plant:Plant): return coordinate_map(plant)

@app.post("/api/slp/corelap/order")
def slp_corelap_order(plant:Plant): return corelap_priorities(plant)

@app.post("/api/slp/compare")
def slp_compare(data:CompareRequest):
    try: return compare(data.as_is,data.to_be)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@app.post("/api/slp/anneal")
def slp_anneal(data:AnnealRequest):
    try: return optimize_annealing(data)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@app.post("/api/planning/aggregate")
def planning_aggregate(data: AggregateRequest):
    try:
        return optimize_aggregate(data)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.post("/api/planning/mps")
def planning_mps(data: MPSRequest):
    try:
        return optimize_mps(data)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.post("/api/planning/mrp")
def planning_mrp(data: MRPRequest):
    return explode_mrp(data)

@app.get("/api/planning/lot-sizing/queenstown")
def lot_sizing_queenstown():
    """Teaching benchmark from the provided MPS slide deck."""
    return QUEENSTOWN_CASE

@app.post("/api/planning/lot-sizing/compare")
def lot_sizing_compare(data: LotSizingRequest):
    return compare_lot_sizing(data)
