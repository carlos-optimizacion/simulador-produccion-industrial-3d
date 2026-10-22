"""Deterministic discrete-event production with real configured machine counts."""
from __future__ import annotations
import heapq
from .models import ProductionRequest
from .slp import center

def simulate(req:ProductionRequest)->dict:
    areas={a.id:a for a in req.plant.areas}
    stations={s.id:s for s in req.stations}
    ready={s.id:[0.0]*s.machines for s in req.stations}
    for pool in ready.values(): heapq.heapify(pool)
    events=[]
    waits=[]
    busy={s.id:0.0 for s in req.stations}
    completed=[]
    for job in range(1,req.quantity+1):
        t=0.0
        prev=None
        for op in req.operations:
            st=stations[op.station_id]
            xy=center(areas[st.area_id])
            if prev is not None:
                meters=abs(xy[0]-prev[0])+abs(xy[1]-prev[1])
                duration=meters/req.travel_speed_m_min
                events.append({"t":round(t,4),"type":"move","job":job,"station":st.id,
                    "from":list(prev),"to":list(xy),"duration":round(duration,4)})
                t+=duration
            available=heapq.heappop(ready[st.id])
            start=max(t,available)
            wait=start-t
            waits.append(wait)
            if wait>0:
                events.append({"t":round(t,4),"type":"queue","job":job,"station":st.id,
                  "duration":round(wait,4),"at":list(xy)})
            finish=start+op.minutes_per_unit
            heapq.heappush(ready[st.id],finish)
            busy[st.id]+=op.minutes_per_unit
            events.append({"t":round(start,4),"type":"start","job":job,"station":st.id,
              "duration":op.minutes_per_unit,"at":list(xy)})
            events.append({"t":round(finish,4),"type":"finish","job":job,"station":st.id,"at":list(xy)})
            t=finish
            prev=xy
        completed.append(t)
        events.append({"t":round(t,4),"type":"complete","job":job,"at":list(prev)})
    order={"finish":0,"complete":1,"move":2,"queue":3,"start":4}
    events.sort(key=lambda e:(e["t"],order.get(e["type"],5),e["job"]))
    makespan=max(completed,default=0)
    return {"engine":"DES determinista v0.1","units_completed":req.quantity,
       "makespan_min":round(makespan,4),
       "throughput_units_per_hour":round(req.quantity*60/makespan,4) if makespan else 0,
       "avg_queue_wait_min":round(sum(waits)/len(waits),4) if waits else 0,
       "stations":[{"id":s.id,"machines":s.machines,
            "utilization_pct":round(100*busy[s.id]/(makespan*s.machines),2) if makespan else 0}
            for s in req.stations],"events":events}
