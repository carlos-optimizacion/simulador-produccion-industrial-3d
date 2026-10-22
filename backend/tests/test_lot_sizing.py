"""Regression test case from Sem9_Production - MPS (Queenstown Kiwi-99)."""
from fastapi.testclient import TestClient
from app.main import app
from app.lot_sizing import (
  LotSizingRequest, QUEENSTOWN_CASE, compare_lot_sizing,
  evaluate, wagner_whitin
)

def test_queenstown_demand_is_2000():
    assert sum(QUEENSTOWN_CASE["demand"])==2000

def test_exact_dp_dominates_baselines():
    data=LotSizingRequest.model_validate(QUEENSTOWN_CASE)
    compare=compare_lot_sizing(data)
    optimum=compare["optimal_relevant_cost"]
    assert len(compare["methods"])==5
    for method in compare["methods"]:
        assert method["relevant_cost"]>=optimum-1e-8
        assert sum(method["production"])==2000
        assert method["ending_inventory"][-1]==0
        assert min(method["ending_inventory"])>=0

def test_all_at_once_costs_and_setups():
    r=compare_lot_sizing(LotSizingRequest.model_validate(QUEENSTOWN_CASE))
    single=next(x for x in r["methods"] if x["method"]=="Correr en un tiempo")
    assert single["setups"]==1
    assert single["setup_cost"]==500
    assert single["total_cost"]==single["relevant_cost"]+100000

def test_wagner_whitin_zero_demand():
    req=LotSizingRequest(demand=[0,0,0],setup_cost=500,holding_cost_per_unit_period=1)
    result=compare_lot_sizing(req)
    assert result["optimal_relevant_cost"]==0
    assert all(x["setups"]==0 for x in result["methods"])

def test_wagner_whitin_nontrivial():
    req=LotSizingRequest(demand=[10,0,10],setup_cost=100,holding_cost_per_unit_period=1)
    solution=evaluate(req,wagner_whitin(req))
    assert solution["production"]==[20,0,0]
    assert solution["relevant_cost"]==120

def test_lot_sizing_api():
    client=TestClient(app)
    result=client.post("/api/planning/lot-sizing/compare",json=QUEENSTOWN_CASE)
    assert result.status_code==200,result.text
    assert result.json()["optimum_method"]=="Wagner-Whitin (óptimo)"
