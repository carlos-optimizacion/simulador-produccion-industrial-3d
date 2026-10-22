"""AS-IS/TO-BE Cartesian SLP and reproducible simulated annealing."""
import math
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Plant
from app.sample import SAMPLE_PLANT
from app.spatial import compare,coordinate_map,corelap_priorities
from app.anneal import AnnealRequest,optimize_annealing
from app.slp import analyze

@pytest.fixture
def original():
    return Plant.model_validate(SAMPLE_PLANT)

def test_local_centers(original):
    nodes={n["id"]:n for n in coordinate_map(original)["nodes"]}
    assert nodes["almacen"]["center_xy_m"]==[4.5,4.0]
    assert nodes["corte"]["origin_xy_m"]==[12,2]
    assert nodes["almacen"]["area_m2"]==42
    assert coordinate_map(original)["origin_xy_m"]==[0,0]

def test_corelap_tcr_is_symmetric(original):
    ranks=corelap_priorities(original)["priority"]
    assert len(ranks)==len(original.areas)
    assert ranks[0]["rank"]==1
    scores={x["area_id"]:x["tcr"] for x in ranks}
    assert scores["almacen"]==5
    assert scores["corte"]==9  # A+E
    assert scores["soldadura"]==2  # E+I+X
    assert scores["despacho"]==-5

def test_identical_layout_has_zero_saving(original):
    comp=compare(original,original.model_copy(deep=True))
    assert comp["saving_pct"]==0
    assert comp["saving_per_shift"]==0
    assert all(x["displacement_m"]==0 for x in comp["relocations"])

def test_reject_non_comparable_demand(original):
    alt=original.model_copy(deep=True)
    alt.flows[0].units_per_shift+=1
    with pytest.raises(ValueError,match="flujos"):
        compare(original,alt)

def test_reject_infeasible_to_be(original):
    alt=original.model_copy(deep=True)
    alt.areas[0].x=100
    with pytest.raises(ValueError,match="geométricas"):
        compare(original,alt)

def test_reject_area_resize_for_same_scenario(original):
    alt=original.model_copy(deep=True)
    alt.areas[0].width+=1
    with pytest.raises(ValueError,match="dimensiones"):
        compare(original,alt)

def test_recocido_is_seeded_and_nonworsening(original):
    req=AnnealRequest(plant=original,iterations=250,grid_step=1,temperature=80,cooling=.985,seed=21)
    a=optimize_annealing(req)
    b=optimize_annealing(req)
    assert a["plant"]==b["plant"]
    assert a["after_cost"]<=a["before_cost"]
    assert a["comparison"]["to_be"]["analysis"]["valid"]
    assert a["parameters"]["seed"]==21
    assert a["considered_candidates"]<=250

def test_anneal_rejects_infeasible_start(original):
    original.areas[0].x=999
    with pytest.raises(ValueError,match="AS-IS"):
        optimize_annealing(AnnealRequest(plant=original,iterations=10))

def test_endpoints_expose_cartesian_and_comparison(original):
    client=TestClient(app)
    x=client.post("/api/slp/coordinates",json=original.model_dump())
    assert x.status_code==200
    assert len(x.json()["nodes"])==5
    c=client.post("/api/slp/corelap/order",json=original.model_dump())
    assert c.status_code==200
    cmp=client.post("/api/slp/compare",json={"as_is":original.model_dump(),"to_be":original.model_dump()})
    assert cmp.status_code==200
    sa=client.post("/api/slp/anneal",json={"plant":original.model_dump(),"iterations":120,"seed":42})
    assert sa.status_code==200
    assert sa.json()["after_cost"]<=sa.json()["before_cost"]
