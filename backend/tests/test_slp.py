import pytest
from app.models import Plant
from app.sample import SAMPLE_PLANT
from app.slp import analyze,improve,collisions

def test_analysis():
    plant=Plant.model_validate(SAMPLE_PLANT)
    result=analyze(plant)
    assert result["valid"]
    assert result["material_handling_cost_per_shift"]==round(sum(x["cost_per_shift"] for x in result["legs"]),4)
def test_clearance():
    plant=Plant.model_validate(SAMPLE_PLANT)
    plant.areas[1].x=plant.areas[0].x+1
    plant.areas[1].z=plant.areas[0].z+1
    assert not analyze(plant)["valid"] and collisions(plant)
def test_improvement():
    plant=Plant.model_validate(SAMPLE_PLANT)
    result=improve(plant,[4,2])
    assert result["after_cost"]<=result["before_cost"]
    assert result["analysis"]["valid"]
def test_references():
    data={**SAMPLE_PLANT,"flows":[{"source":"unknown","target":"corte","units_per_shift":1}]}
    with pytest.raises(ValueError): Plant.model_validate(data)
