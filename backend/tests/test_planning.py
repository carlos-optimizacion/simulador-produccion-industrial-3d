"""Numerical invariants for APP/MPS MILP and multilevel BOM MRP."""
from fastapi.testclient import TestClient
from app.main import app
from app.planning import AggregateRequest,MPSRequest,optimize_aggregate,optimize_mps
from app.mrp import MRPRequest,explode_mrp

def app_example():
    return {"demand":[20,30,25],
      "initial_workers":2,"max_workers":4,"initial_inventory":0,
      "units_per_worker_period":10,"overtime_units_per_worker":4,
      "max_subcontract_per_period":5,
      "worker_period_cost":150,
      "hiring_cost":20,"layoff_cost":40,
      "regular_unit_cost":2,"overtime_unit_cost":4,
      "subcontract_unit_cost":6,"holding_unit_cost":.5}

def mps_example():
    return {"products":[
        {"sku":"A","initial_inventory":5,"safety_stock":0,"lot_size":5,"manufacturing_lead_time":1},
        {"sku":"B","initial_inventory":3,"safety_stock":0,"lot_size":2,"manufacturing_lead_time":0}],
        "forecast":{"A":[2,10,10],"B":[3,4,6]},
        "firm_orders":{"A":[2,9,11]},
        "minutes_per_unit":{"A":5,"B":3},
        "available_minutes_per_period":[90,90,90]}

def mrp_example():
    return {"items":[
        {"sku":"A","lead_time_periods":1},
        {"sku":"SUB","lead_time_periods":0,"lot_multiple":1},
        {"sku":"MAT","lead_time_periods":0,"lot_multiple":5},
        {"sku":"PACK","lead_time_periods":1,"on_hand":5,"lot_multiple":5}],
        "bom":[{"parent":"A","component":"SUB","quantity_per_parent":2},
               {"parent":"SUB","component":"MAT","quantity_per_parent":3},
               {"parent":"A","component":"PACK","quantity_per_parent":1}],
        "mps_planned_completions":{"A":[0,10,5]}}

def test_aggregate_inventory_staff_capacity():
    req=AggregateRequest.model_validate(app_example())
    plan=optimize_aggregate(req)
    old_staff=req.initial_workers
    old_stock=req.initial_inventory
    for p in plan["periods"]:
        assert p["workers"]==old_staff+p["hires"]-p["layoffs"]
        assert p["inventory"]==old_stock+p["regular"]+p["overtime"]+p["subcontract"]-p["demand"]
        assert p["regular"]<=p["workers"]*req.units_per_worker_period
        assert p["overtime"]<=p["workers"]*req.overtime_units_per_worker
        old_stock=p["inventory"];old_staff=p["workers"]
    assert len(plan["mps_internal_units_per_period"])==3
    assert round(sum(plan["cost_breakdown"].values()),2)==plan["total_cost"]

def test_aggregate_infeasible_capacity():
    import pytest
    a=app_example()
    a["max_workers"]=a["initial_workers"]=1
    a["max_subcontract_per_period"]=0
    a["overtime_units_per_worker"]=0
    with pytest.raises(ValueError,match="factible"):
        optimize_aggregate(AggregateRequest.model_validate(a))

def test_mps_balances_lots_and_capacity():
    req=MPSRequest.model_validate(mps_example())
    plan=optimize_mps(req)
    assert len(plan["products"])==2
    for p in plan["products"]:
        spec=next(x for x in req.products if x.sku==p["sku"])
        last=spec.initial_inventory
        for t in range(plan["periods"]):
            qty=p["planned_completions"][t]
            assert qty%spec.lot_size==0
            assert p["projected_ending_inventory"][t]==last+qty-p["effective_demand"][t]
            if t<spec.manufacturing_lead_time: assert qty==0
            last=p["projected_ending_inventory"][t]
    assert all(used<=available+1e-8 for used,available in zip(plan["capacity_used_minutes"],plan["available_minutes_per_period"]))

def test_mps_impossible_demand_raises():
    import pytest
    d=mps_example()
    d["forecast"]["A"][0]=10  # first period cannot be supplied before lead time
    with pytest.raises(ValueError,match="factible"):
        optimize_mps(MPSRequest.model_validate(d))

def test_mrp_multilevel_requirements():
    out=explode_mrp(MRPRequest.model_validate(mrp_example()))
    rows={x["sku"]:x for x in out["items"]}
    assert rows["A"]["planned_order_releases"]==[10,5,0]
    assert rows["SUB"]["gross_requirements"]==[20,10,0]
    assert rows["MAT"]["gross_requirements"]==[60,30,0]
    assert rows["PACK"]["gross_requirements"]==[10,5,0]
    assert rows["MAT"]["planned_order_receipts"]==[60,30,0]
    assert not out["feasible_within_horizon"]  # PACK lead=1, on-hand 5: need a pre-horizon order

def test_mrp_bom_cycle_is_rejected():
    import pytest
    sample=mrp_example()
    sample["bom"].append({"parent":"MAT","component":"A","quantity_per_parent":1})
    with pytest.raises(ValueError):
        MRPRequest.model_validate(sample)

def test_api_endpoints_planning():
    client=TestClient(app)
    agg=client.post("/api/planning/aggregate",json=app_example())
    assert agg.status_code==200,agg.text
    mps=client.post("/api/planning/mps",json=mps_example())
    assert mps.status_code==200,mps.text
    mrp=client.post("/api/planning/mrp",json=mrp_example())
    assert mrp.status_code==200,mrp.text
