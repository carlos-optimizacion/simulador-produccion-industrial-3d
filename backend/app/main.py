import os
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import Plant,LayoutRequest,ProductionRequest,Scenario
from .slp import analyze,improve
from .simulation import simulate
from .sample import SAMPLE_PLANT,SAMPLE_PRODUCTION

app=FastAPI(title="INDUSIM 3D API",version="0.1.0")
origins=["http://localhost:5173","http://127.0.0.1:5173"]
if os.getenv("FRONTEND_ORIGIN"): origins.append(os.environ["FRONTEND_ORIGIN"].rstrip("/"))
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,
                   allow_methods=["GET","POST"],allow_headers=["Content-Type"])
@app.get("/api/health")
def health(): return {"status":"ok","version":"0.1.0"}
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
    return scenario.model_dump()
