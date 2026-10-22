"""Event-driven deterministic flow-shop simulation with FIFO queues and real machine IDs.

A minimal discrete-event simulator, not SimPy nor stochastic modeling. All jobs are
released at t=0 and operations follow an identical configured routing.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import heapq
import itertools
from .models import ProductionRequest
from .slp import center, distance

@dataclass
class Workcenter:
    idle: list[int]
    queue: deque[tuple[float,int,int]] = field(default_factory=deque)
    busy_minutes: list[float] = field(default_factory=list)

def simulate(req: ProductionRequest) -> dict:
    stations = {station.id: station for station in req.stations}
    areas = {area.id: area for area in req.plant.areas}
    centers = {s.id: center(areas[s.area_id]) for s in req.stations}
    resources = {
        s.id: Workcenter(list(range(s.machines)), busy_minutes=[0.0] * s.machines)
        for s in req.stations
    }
    for resource in resources.values():
        heapq.heapify(resource.idle)

    sequence = itertools.count()
    # (time, priority, serial, event kind, job id, operation index, machine id)
    # finish events processed before arrivals at equal timestamps.
    pending: list[tuple[float,int,int,str,int,int,int]] = []
    for job in range(1, req.quantity + 1):
        heapq.heappush(pending, (0.0, 1, next(sequence), "arrive", job, 0, -1))

    events: list[dict] = []
    waits: list[float] = []
    completion: dict[int,float] = {}
    processed_operations = 0

    def dispatch(station_id: str, now: float) -> None:
        """Start waiting FIFO jobs on available machines."""
        nonlocal processed_operations
        pool = resources[station_id]
        while pool.idle and pool.queue:
            arrival, job, op_idx = pool.queue.popleft()
            machine_idx = heapq.heappop(pool.idle)
            operation = req.operations[op_idx]
            wait = max(0.0, now - arrival)
            waits.append(wait)
            at = centers[station_id]
            if wait > 1e-9:
                events.append({"t": round(arrival, 4), "type": "queue",
                               "job": job, "station": station_id,
                               "duration": round(wait, 4), "at": list(at)})
            duration = operation.minutes_per_unit
            end = now + duration
            pool.busy_minutes[machine_idx] += duration
            events.append({"t": round(now, 4), "type": "start", "job": job,
                           "station": station_id, "machine_index": machine_idx,
                           "duration": duration, "at": list(at)})
            heapq.heappush(pending, (end, 0, next(sequence), "finish", job, op_idx, machine_idx))
            processed_operations += 1

    while pending:
        now, _, _, kind, job, op_idx, machine_idx = heapq.heappop(pending)
        op = req.operations[op_idx]
        station_id = op.station_id
        if kind == "arrive":
            resources[station_id].queue.append((now, job, op_idx))
            dispatch(station_id, now)
            continue

        location = centers[station_id]
        events.append({"t": round(now, 4), "type": "finish", "job": job,
                       "station": station_id, "machine_index": machine_idx, "at": list(location)})
        heapq.heappush(resources[station_id].idle, machine_idx)
        # Dispatch waiting jobs immediately when equipment becomes free.
        dispatch(station_id, now)

        if op_idx == len(req.operations) - 1:
            completion[job] = now
            events.append({"t": round(now, 4), "type": "complete", "job": job, "at": list(location)})
        else:
            successor = req.operations[op_idx + 1].station_id
            destination = centers[successor]
            travel_m = distance(areas[stations[station_id].area_id],
                                areas[stations[successor].area_id])
            travel = travel_m / req.travel_speed_m_min
            events.append({"t": round(now, 4), "type": "move",
                           "job": job, "station": successor, "from": list(location),
                           "to": list(destination), "duration": round(travel, 4)})
            heapq.heappush(pending, (now + travel, 1, next(sequence),
                                     "arrive", job, op_idx + 1, -1))

    makespan = max(completion.values(), default=0.0)
    # Sorting only for the animation transcript, not for scheduling.
    order = {"finish": 0, "complete": 1, "move": 2, "queue": 3, "start": 4}
    events.sort(key=lambda event: (event["t"], order.get(event["type"], 5), event["job"]))
    return {
        "engine": "DES determinista FIFO v0.2",
        "units_completed": len(completion),
        "makespan_min": round(makespan, 4),
        "throughput_units_per_hour": round(req.quantity * 60.0 / makespan, 4) if makespan else 0,
        "avg_queue_wait_min": round(sum(waits) / len(waits), 4) if waits else 0,
        "stations": [{
            "id": s.id,
            "machines": s.machines,
            "utilization_pct": round(
                100 * sum(resources[s.id].busy_minutes) / (makespan * s.machines), 2
            ) if makespan else 0,
            "machines_detail": [
                {"index": index, "utilization_pct": round(100 * minutes / makespan, 2) if makespan else 0}
                for index, minutes in enumerate(resources[s.id].busy_minutes)
            ]
        } for s in req.stations],
        "events": events,
        "total_operations": processed_operations,
        "travel_method": "Manhattan entre centroides, sin rutas navegables",
    }
