"""Regression tests for policies, fixed setup costs, root inventory validation."""
import pytest
from fastapi.testclient import TestClient
from app.app_policies import APPScenario,optimize_app_scenario,compare_app_policies
from app.planning import MPSRequest,optimize_mps
from app.mrp import MRPRequest,explode_mrp
from app.main import app

APP = {
    "demand":[20,30,15,25],
    "initial_workers":2,"max_workers":4,"units_per_worker_period":10,
    "overtime_units_per_worker":5,"max_subcontract_per_period":8,
    "initial_inventory":0,"target_ending_inventory":0,
    "worker_period_cost":130,"hiring_cost":40,"layoff_cost":90,
    "regular_unit_cost":3,"overtime_unit_cost":7,
    "subcontract_unit_cost":15,"holding_unit_cost":1,
    "backlog_unit_cost":9,
    "allow_backlog":True
}

def assert_app_balance(data,out):
    wprev=data["initial_workers"]
    netprev=data.get("initial_inventory",0)-data.get("initial_backlog",0)
    for period in out["periods"]:
        assert period["workers"]==wprev+period["hires"]-period["layoffs"]
        net=netprev+period["regular"]+period["overtime"]+period["subcontract"]-period["demand"]
        assert period["inventory"]-period["backlog"]==net
        assert not (period["inventory"]>0 and period["backlog"]>0)
        assert period["regular"]<=period["workers"]*data["units_per_worker_period"]
        assert period["overtime"]<=period["workers"]*data["overtime_units_per_worker"]
        wprev=period["workers"]
        netprev=net
    assert out["periods"][-1]["backlog"]==0

def test_app_backlog_balance():
    result=optimize_app_scenario(APPScenario.model_validate(APP))
    assert_app_balance(APP,result)
    assert result["optimal"]

def test_app_scenarios_consistent_cost_and_policies():
    result=compare_app_policies(APPScenario.model_validate(APP))
    assert len(result["results"])==6
    mixed=next(x for x in result["results"] if x["policy"]=="mixed")
    assert mixed["status"]=="optimal"
    assert result["best_total_cost"]<=mixed["total_cost"]+1e-6
    for row in result["results"]:
        if row["status"]!="optimal":continue
        assert_app_balance(APP,row)
        if row["policy"]=="no_layoffs":assert all(t["layoffs"]==0 for t in row["periods"])
        if row["policy"]=="no_overtime":assert all(t["overtime"]==0 for t in row["periods"])
        if row["policy"]=="no_outsourcing":assert all(t["subcontract"]==0 for t in row["periods"])
        if row["policy"]=="chase":assert all(t["inventory"]==0 and t["backlog"]==0 for t in row["periods"])
        if row["policy"]=="level":
            assert len({t["regular"] for t in row["periods"]})==1
            assert len({t["workers"] for t in row["periods"]})==1

def test_app_can_use_backlog_and_must_clear_before_final_period():
    case={**APP,"demand":[0,20],"initial_workers":1,"max_workers":1,
          "units_per_worker_period":10,"overtime_units_per_worker":0,
          "max_subcontract_per_period":0,"allow_backlog":True}
    with pytest.raises(ValueError,match="factible"):
        optimize_app_scenario(APPScenario.model_validate(case))
    case["demand"]=[20,0]
    result=optimize_app_scenario(APPScenario.model_validate(case))
    assert result["periods"][0]["backlog"]==10
    assert result["periods"][1]["backlog"]==0

def test_setup_binary_cost_single_period():
    sample={
        "products":[{"sku":"A","initial_inventory":0,"lot_size":1,
                     "unit_production_cost":0,"unit_holding_cost":0,"setup_cost":75}],
        "forecast":{"A":[10]},
        "firm_orders":{"A":[4]},
        "minutes_per_unit":{"A":2},
        "available_minutes_per_period":[60]
    }
    result=optimize_mps(MPSRequest.model_validate(sample))
    assert result["total_cost"]==75
    assert result["products"][0]["planned_completions"]==[10]
    assert result["products"][0]["setups"]==[1]
    assert result["products"][0]["atp_non_cumulative"]==[6]

def test_setup_encourages_consolidation():
    data={
        "products":[{"sku":"A","initial_inventory":0,"lot_size":1,
                     "unit_production_cost":0,"unit_holding_cost":1,"setup_cost":100}],
        "forecast":{"A":[5,5,5]},
        "minutes_per_unit":{"A":1},
        "available_minutes_per_period":[60]*3
    }
    result=optimize_mps(MPSRequest.model_validate(data))
    sku=result["products"][0]
    assert sum(sku["setups"])==1
    assert sku["total_setup_cost"]==100
    assert sum(sku["planned_completions"])==15

def test_mrp_root_on_hand_not_double_exploded():
    data={
      "items":[{"sku":"FINAL","on_hand":30,"lead_time_periods":0},
               {"sku":"PIEZA","on_hand":0,"lead_time_periods":0}],
      "bom":[{"parent":"FINAL","component":"PIEZA","quantity_per_parent":2}],
      "mps_planned_completions":{"FINAL":[0,20]},
      "end_item_gross_requirements":{"FINAL":[10,40]}
    }
    result=explode_mrp(MRPRequest.model_validate(data))
    root=next(x for x in result["items"] if x["sku"]=="FINAL")
    component=next(x for x in result["items"] if x["sku"]=="PIEZA")
    assert root["projected_inventory"]==[20,0]
    assert root["initial_on_hand"]==30
    assert component["gross_requirements"]==[0,40]  # 20 produced, not all 50 demanded
    assert result["feasible_within_horizon"]

def test_mrp_detects_uncovered_final_demand():
    data={
      "items":[{"sku":"FINAL","on_hand":3},{"sku":"PIEZA"}],
      "bom":[{"parent":"FINAL","component":"PIEZA","quantity_per_parent":1}],
      "mps_planned_completions":{"FINAL":[2]},
      "end_item_gross_requirements":{"FINAL":[9]}
    }
    result=explode_mrp(MRPRequest.model_validate(data))
    assert not result["feasible_within_horizon"]
    assert result["end_item_shortages"][0]["missing_units"]==4

def test_advanced_endpoints():
    client=TestClient(app)
    scenarios=client.post("/api/planning/aggregate/scenarios",json=APP)
    assert scenarios.status_code==200,scenarios.text
    assert scenarios.json()["best_feasible_policy"] is not None
    chosen=client.post("/api/planning/aggregate/v2",json=APP)
    assert chosen.status_code==200,chosen.text
    assert "backlog" in chosen.json()["periods"][0]
