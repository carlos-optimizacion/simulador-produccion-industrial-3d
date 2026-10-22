from fastapi.testclient import TestClient
from app.main import app
from app.models import ProductionRequest
from app.sample import SAMPLE_PLANT,SAMPLE_PRODUCTION
from app.simulation import simulate

def test_machine_counts():
    result=simulate(ProductionRequest.model_validate(SAMPLE_PRODUCTION))
    assert result["units_completed"]==12
    assert [s["machines"] for s in result["stations"]]==[1,2,1]
    assert sum(e["type"]=="complete" for e in result["events"])==12
    assert [e["t"] for e in result["events"]]==sorted(e["t"] for e in result["events"])
def test_machine_capacity():
    req=ProductionRequest.model_validate(SAMPLE_PRODUCTION)
    variant=req.model_copy(deep=True)
    variant.stations[0].machines=2
    assert simulate(variant)["makespan_min"]<=simulate(req)["makespan_min"]
def test_endpoints():
    client=TestClient(app)
    assert client.get("/api/health").status_code==200
    assert client.post("/api/slp/analyze",json=SAMPLE_PLANT).json()["valid"]
    assert client.post("/api/production/simulate",json=SAMPLE_PRODUCTION).json()["units_completed"]==12
