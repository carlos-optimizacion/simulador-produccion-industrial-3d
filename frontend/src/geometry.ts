import type {Area,Plant,Station} from './types'

/** Meter-grid rounding used by the 3D drag editor. */
export function snapToGrid(value:number,step:number):number {
  return Math.round(Math.max(0,value)/step)*step
}

/** Mirrors the backend rectangular footprint/clearance rules for instant feedback. */
export function findLayoutProblems(plant:Plant):string[] {
  const problems:string[]=[]
  for(const a of plant.areas){
    if(a.width<=0||a.depth<=0||a.x<0||a.z<0||
       a.x+a.width>plant.width+1e-8||a.z+a.depth>plant.depth+1e-8)
      problems.push('El área '+a.name+' queda fuera de la planta.')
  }
  for(let i=0;i<plant.areas.length;i++){
    const a=plant.areas[i]
    for(const b of plant.areas.slice(i+1)){
      const gapX=Math.max(a.x-(b.x+b.width),b.x-(a.x+a.width))
      const gapZ=Math.max(a.z-(b.z+b.depth),b.z-(a.z+a.depth))
      if(gapX<plant.clearance-1e-8&&gapZ<plant.clearance-1e-8)
        problems.push('Separación insuficiente entre '+a.name+' y '+b.name+'.')
    }
  }
  return problems
}

export function machinesPerArea(plant:Plant,stations:Station[],areaId:string):number {
  return stations.filter(s=>s.area_id===areaId).reduce((n,s)=>n+s.machines,0)
}

/** Simplified rectangular grid capacity, shared with backend/app/models.py. */
export function machineCapacity(area:Area):number {
  const columns=Math.max(0,Math.floor((area.width-.8)/2.2)+1)
  const rows=Math.max(0,Math.floor((area.depth-.8)/2.2)+1)
  return columns*rows
}

export function canMoveArea(plant:Plant,id:string,x:number,z:number):boolean{
  return !findLayoutProblems({...plant,areas:plant.areas.map(a=>a.id===id?{...a,x,z}:a)}).length
}
