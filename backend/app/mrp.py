"""Time-phased multi-level MRP explosion, lot netting and planned order releases.

MRP is deterministic arithmetic rather than a global cost optimizer.
Production availability and supplier capacity are not yet modeled here.
"""
from __future__ import annotations
from collections import defaultdict, deque
from math import ceil
from pydantic import BaseModel,Field,model_validator

class ItemSpec(BaseModel):
    sku:str = Field(min_length=1)
    lead_time_periods:int=Field(ge=0,le=24,default=0)
    on_hand:int=Field(ge=0,default=0)
    safety_stock:int=Field(ge=0,default=0)
    lot_multiple:int=Field(gt=0,default=1)
    minimum_order:int=Field(ge=0,default=0)
    scheduled_receipts:list[int]=Field(default_factory=list)

class BOMLine(BaseModel):
    parent:str=Field(min_length=1)
    component:str=Field(min_length=1)
    quantity_per_parent:int=Field(gt=0)

class MRPRequest(BaseModel):
    items:list[ItemSpec]=Field(min_length=2,max_length=100)
    bom:list[BOMLine]=Field(min_length=1,max_length=300)
    mps_planned_completions:dict[str,list[int]]
    end_item_gross_requirements:dict[str,list[int]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_horizon_and_bom(self):
        sku=[item.sku for item in self.items]
        if len(set(sku))!=len(sku): raise ValueError("SKU duplicados en MRP")
        available=set(sku)
        if not self.mps_planned_completions:raise ValueError("Se requieren productos finales de MPS")
        if not set(self.mps_planned_completions)<=available:
            raise ValueError("El MPS contiene productos no registrados en items")
        horizon=len(next(iter(self.mps_planned_completions.values())))
        if not set(self.end_item_gross_requirements)<=set(self.mps_planned_completions):
            raise ValueError("Demanda final con SKU fuera del plan maestro MPS")
        for values in self.end_item_gross_requirements.values():
            if len(values)!=horizon or any(x<0 for x in values):
                raise ValueError("Demanda final con horizonte incoherente")

        if not (1<=horizon<=24):raise ValueError("Horizonte MRP entre 1 y 24 periodos")
        for data in self.mps_planned_completions.values():
            if len(data)!=horizon or any(q<0 for q in data):
                raise ValueError("MPS con cantidades u horizonte incoherentes")
        for item in self.items:
            if item.scheduled_receipts and (
                len(item.scheduled_receipts)!=horizon or any(v<0 for v in item.scheduled_receipts)
            ): raise ValueError("Recepciones programadas con horizonte incoherente")
        parents=defaultdict(set)
        incoming=defaultdict(int)
        seen=set()
        for edge in self.bom:
            if edge.parent not in available or edge.component not in available:
                raise ValueError("BOM con SKU inexistente")
            if edge.parent==edge.component or (edge.parent,edge.component) in seen:
                raise ValueError("BOM duplicado o autorreferencial")
            seen.add((edge.parent,edge.component))
            parents[edge.parent].add(edge.component)
            incoming[edge.component]+=1
        # Root products from MPS are not allowed to simultaneously be components.
        if set(self.mps_planned_completions) & set(incoming):
            raise ValueError("Un SKU MPS final no puede ser componente en esta versión")
        indegree={k:incoming[k] for k in available}
        queue=deque(sorted(k for k in available if indegree[k]==0))
        visited=0
        while queue:
            parent=queue.popleft()
            visited+=1
            for child in sorted(parents[parent]):
                indegree[child]-=1
                if indegree[child]==0:queue.append(child)
        if visited!=len(available):raise ValueError("La BOM contiene ciclos")
        return self

def explode_mrp(req:MRPRequest)->dict:
    item_by_id={x.sku:x for x in req.items}
    horizon=len(next(iter(req.mps_planned_completions.values())))
    child_edges=defaultdict(list)
    indegree={x.sku:0 for x in req.items}
    for line in req.bom:
        child_edges[line.parent].append((line.component,line.quantity_per_parent))
        indegree[line.component]+=1
    queue=deque(sorted(id for id,k in indegree.items() if k==0))
    gross={id:[0]*horizon for id in indegree}
    result={}
    past_due=[]
    shortages=[]
    while queue:
        sku=queue.popleft()
        item=item_by_id[sku]
        planned_receipts=[0]*horizon
        releases=[0]*horizon
        if sku in req.mps_planned_completions:
            planned_receipts=list(req.mps_planned_completions[sku])
            for t,qty in enumerate(planned_receipts):
                if not qty:continue
                target=t-item.lead_time_periods
                if target<0:
                    # MPS must be feasible before release to MRP.
                    past_due.append({"sku":sku,"needed_period":t+1,
                                     "release_period":target+1,"quantity":qty})
                else:releases[target]+=qty
            scheduled=item.scheduled_receipts or [0]*horizon
            root_demand=req.end_item_gross_requirements.get(sku)
            stock=item.on_hand
            projected_ending=[]
            if root_demand is not None:
                for t,qty in enumerate(root_demand):
                    stock+=scheduled[t]+planned_receipts[t]-qty
                    projected_ending.append(stock)
                    if stock<item.safety_stock:
                        shortages.append({"sku":sku,"period":t+1,
                            "available_vs_safety_stock":stock-item.safety_stock,
                            "missing_units":item.safety_stock-stock})
            result[sku]={
                "sku":sku,"kind":"mps_end_item",
                "gross_requirements":list(root_demand) if root_demand is not None else [0]*horizon,
                "scheduled_receipts":list(scheduled),
                "net_requirements":[0]*horizon,
                "planned_order_receipts":planned_receipts,
                "planned_order_releases":releases,
                "projected_inventory":projected_ending if root_demand is not None else None,
                "inventory_validation":"checked" if root_demand is not None else "not_provided",
                "initial_on_hand":item.on_hand
            }
        else:
            stock=item.on_hand
            net=[0]*horizon
            inventory=[]
            scheduled=item.scheduled_receipts or [0]*horizon
            for t in range(horizon):
                projected=stock+scheduled[t]-gross[sku][t]
                if projected<item.safety_stock:
                    needed=item.safety_stock-projected
                    qty=ceil(max(needed,item.minimum_order)/item.lot_multiple)*item.lot_multiple
                    net[t]=needed
                    planned_receipts[t]=qty
                    target=t-item.lead_time_periods
                    if target<0:
                        past_due.append({"sku":sku,"needed_period":t+1,
                                         "release_period":target+1,"quantity":qty})
                    else:releases[target]+=qty
                    projected+=qty
                stock=projected
                inventory.append(stock)
            result[sku]={
                "sku":sku,"kind":"component",
                "gross_requirements":list(gross[sku]),
                "scheduled_receipts":list(scheduled),
                "net_requirements":net,
                "planned_order_receipts":planned_receipts,
                "planned_order_releases":releases,
                "projected_inventory":inventory
            }
        for child,qty_per_parent in child_edges[sku]:
            for t,qty in enumerate(releases):
                gross[child][t]+=qty*qty_per_parent
            indegree[child]-=1
            if indegree[child]==0:queue.append(child)
    return {"method":"MRP determinista multinivel (explosión, neteo, lotificación y desfase)",
            "horizon_periods":horizon,"items":list(result.values()),
            "release_before_horizon":past_due,
            "end_item_shortages":shortages,
            "feasible_within_horizon":not bool(past_due or shortages),
            "note":"Órdenes que requieren liberación anterior al horizonte son alertas; "
                   "las recepciones propuestas no están garantizadas sin anticipación/expedición. "
                   "Si se suministra demanda final se valida stock disponible, recibos MPS y faltantes. "
                   "No recalcula el MPS ni valida capacidad de proveedores."}
