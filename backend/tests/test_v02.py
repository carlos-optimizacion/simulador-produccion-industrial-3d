from app.models import Plant,ProductionRequest,Scenario
from app.sample import SAMPLE_PLANT,SAMPLE_PRODUCTION
from app.simulation import simulate
from fastapi.testclient import TestClient
from app.main import app
import pytest

def test_first_two_jobs_can_run_in_parallel():
    d = dict(SAMPLE_PRODUCTION)
    d["stations"] = [dict(s) for s in d["stations"]]
    d["stations"][0]["machines"] = 2
    out = simulate(ProductionRequest.model_validate(d))
    first = [e for e in out["events"] if e["type"] == "start" and e["station"] == "corte"]
    assert len([e for e in first if e["t"] == 0]) == 2
    assert set(e["machine_index"] for e in first if e["t"] == 0) == {0, 1}

def test_exact_equipment_instances():
    out = simulate(ProductionRequest.model_validate(SAMPLE_PRODUCTION))
    assert [len(s["machines_detail"]) for s in out["stations"]] == [1, 2, 1]
    assert out["total_operations"] == 3 * SAMPLE_PRODUCTION["quantity"]
    assert len([e for e in out["events"] if e["type"] == "complete"]) == SAMPLE_PRODUCTION["quantity"]
    for event in out["events"]:
        if event["type"] in {"start", "finish"}:
            machine_count = next(s["machines"] for s in out["stations"] if s["id"] == event["station"])
            assert 0 <= event["machine_index"] < machine_count

def test_cannot_fit_too_many_machines():
    scenario = {**SAMPLE_PRODUCTION, "stations": [dict(s) for s in SAMPLE_PRODUCTION["stations"]]}
    scenario["stations"][0]["machines"] = 100
    with pytest.raises(ValueError, match="admite"):
        ProductionRequest.model_validate(scenario)

def test_scenario_schema_validation_and_api():
    client=TestClient(app)
    payload={"schema_version":"indusim-3d/1",**SAMPLE_PRODUCTION}
    assert client.post("/api/scenarios/validate",json=payload).status_code==200
    bad={"schema_version":"not-valid",**SAMPLE_PRODUCTION}
    assert client.post("/api/scenarios/validate",json=bad).status_code==422

def test_all_jobs_complete_with_repeated_station():
    d=dict(SAMPLE_PRODUCTION)
    d["operations"]=[{"station_id":"corte","minutes_per_unit":2},
                     {"station_id":"soldadura","minutes_per_unit":3},
                     {"station_id":"corte","minutes_per_unit":1}]
    out=simulate(ProductionRequest.model_validate(d))
    assert out["units_completed"]==12
    assert out["total_operations"]==36
    assert out["makespan_min"]>0
