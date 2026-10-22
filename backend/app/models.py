"""Pydantic contracts shared across simulation and visualization."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Area(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    x: float = 0
    z: float = 0
    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    color: str = "#4b87b8"

class Flow(BaseModel):
    source: str
    target: str
    units_per_shift: float = Field(ge=0)
    cost_per_unit_meter: float = Field(ge=0, default=1)

class Relationship(BaseModel):
    source: str
    target: str
    rating: Literal["A","E","I","O","U","X"]
    reason: str = ""

class Plant(BaseModel):
    name: str = "Planta de demostración"
    width: float = Field(gt=0, default=32)
    depth: float = Field(gt=0, default=20)
    clearance: float = Field(ge=0, default=0.5)
    areas: list[Area] = Field(min_length=2)
    flows: list[Flow] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_links(self):
        ids=[a.id for a in self.areas]
        if len(ids)!=len(set(ids)):
            raise ValueError("Los identificadores de las áreas deben ser únicos")
        for link in [*self.flows,*self.relationships]:
            if link.source not in ids or link.target not in ids or link.source==link.target:
                raise ValueError("Relación o flujo con áreas inválidas")
        return self

class LayoutRequest(BaseModel):
    plant: Plant
    steps: list[float] = Field(default_factory=lambda:[4.0,2.0,1.0])

class Operation(BaseModel):
    station_id: str
    minutes_per_unit: float = Field(gt=0)

class Station(BaseModel):
    id: str
    name: str
    area_id: str
    machines: int = Field(ge=1)

def station_grid_capacity(area: Area) -> int:
    """Maximum simplified 1.45m x 1.25m machine footprints on a 2.2m pitch."""
    import math
    nx = max(0, math.floor((area.width - 0.8) / 2.2) + 1)
    nz = max(0, math.floor((area.depth - 0.8) / 2.2) + 1)
    return nx * nz

class ProductionRequest(BaseModel):
    plant: Plant
    stations: list[Station] = Field(min_length=1)
    operations: list[Operation] = Field(min_length=1)
    quantity: int = Field(ge=1, le=1000, default=8)
    travel_speed_m_min: float = Field(gt=0, default=30)

    @model_validator(mode="after")
    def check_stations(self):
        ids=[s.id for s in self.stations]
        if len(set(ids))!=len(ids):
            raise ValueError("Identificadores de estaciones duplicados")
        areas={a.id for a in self.plant.areas}
        if any(s.area_id not in areas for s in self.stations):
            raise ValueError("La estación debe pertenecer a un área")
        if any(o.station_id not in ids for o in self.operations):
            raise ValueError("Operación con estación inexistente")
        for area in self.plant.areas:
            count = sum(s.machines for s in self.stations if s.area_id == area.id)
            if count > station_grid_capacity(area):
                raise ValueError(f"El área {area.name} admite {station_grid_capacity(area)} máquinas en la representación 3D; configuradas: {count}.")
        return self

class Scenario(ProductionRequest):
    schema_version: Literal["indusim-3d/1", "indusim-3d/2"] = "indusim-3d/2"
    as_is: Plant | None = None

