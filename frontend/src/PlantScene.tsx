import { Canvas, type ThreeEvent } from '@react-three/fiber'
import { Html, OrbitControls, RoundedBox, Line } from '@react-three/drei'
import { useMemo, useRef, useState } from 'react'
import { Plane, Vector3 } from 'three'
import type { Area, Plant, Station, SimEvent } from './types'
import { snapToGrid, machineCapacity } from './geometry'

type Props = {
  plant:Plant
  selected:string
  onSelect:(id:string)=>void
  stations:Station[]
  time:number
  events:SimEvent[]
  editMode:boolean
  snap:number
  onAreaMove:(id:string,x:number,z:number)=>void
  onMoveComplete:()=>void
  onMoveStart:()=>void
}

const floorPlane = new Plane(new Vector3(0,1,0),0)
const hitPoint = new Vector3()

function AreaTile({
  area,selected,onSelect,editMode,snap,onAreaMove,onMoveStart,onMoveComplete
}: Pick<Props,'selected'|'onSelect'|'editMode'|'snap'|'onAreaMove'|'onMoveStart'|'onMoveComplete'> & {area:Area}){
  const offset=useRef<{x:number;z:number}|null>(null)
  const [dragging,setDragging]=useState(false)
  function down(e:ThreeEvent<PointerEvent>){
    e.stopPropagation()
    onSelect(area.id)
    if(!editMode)return
    if(e.ray.intersectPlane(floorPlane,hitPoint)){
      offset.current={x:area.x-hitPoint.x,z:area.z-hitPoint.z}
      setDragging(true)
      onMoveStart()
      e.target.setPointerCapture(e.pointerId)
    }
  }
  function move(e:ThreeEvent<PointerEvent>){
    if(!offset.current)return
    e.stopPropagation()
    if(e.ray.intersectPlane(floorPlane,hitPoint)){
      const {x,z}=offset.current
      onAreaMove(area.id,snapToGrid(hitPoint.x+x,snap),snapToGrid(hitPoint.z+z,snap))
    }
  }
  function end(e:ThreeEvent<PointerEvent>){
    if(!offset.current)return
    e.stopPropagation()
    offset.current=null
    setDragging(false)
    try{e.target.releasePointerCapture(e.pointerId)}catch{ /* already released */ }
    onMoveComplete()
  }
  return <mesh position={[0,.12,0]} receiveShadow
    onPointerDown={down} onPointerMove={move} onPointerUp={end} onPointerCancel={end}>
    <boxGeometry args={[area.width,.22,area.depth]}/>
    <meshStandardMaterial color={selected===area.id?'#77ede1':area.color}
      transparent opacity={dragging?.92:.74}/>
  </mesh>
}

function Equipment({area,stations,busy}:{area:Area;stations:Station[];busy:Set<string>}){
  const cols=Math.max(1,Math.floor((area.width-.8)/2.2)+1)
  const machines=stations.filter(s=>s.area_id===area.id).flatMap(s=>
    Array.from({length:s.machines},(_,index)=>({station:s,index})))
  const overCapacity=machines.length>machineCapacity(area)
  return <>{machines.map((item,idx)=>{
    const column=idx%cols,row=Math.floor(idx/cols)
    const active=busy.has(item.station.id+'_'+item.index)
    const color=overCapacity?'#ef6474':active?'#37e4b5':'#2b5a78'
    const isCut=item.station.id.toLowerCase().includes('corte')
    const isWeld=item.station.id.toLowerCase().includes('sold')
    return <group key={item.station.id+'-'+item.index}
      position={[-area.width/2+.95+column*2.2,.65,-area.depth/2+.95+row*2.2]}>
      <RoundedBox args={[1.45,1,1.25]} radius={.12} castShadow receiveShadow>
        <meshStandardMaterial color={color} metalness={.45} roughness={.4}/>
      </RoundedBox>
      {isCut?<mesh rotation={[0,0,Math.PI/2]} position={[0,.52,.1]} castShadow>
        <cylinderGeometry args={[.37,.37,.09,24]}/><meshStandardMaterial color="#b3c7d5" metalness={.75}/>
      </mesh>:isWeld?<mesh position={[0,.68,-.1]} castShadow>
        <cylinderGeometry args={[.08,.08,.65,10]}/><meshStandardMaterial color="#afcee3" metalness={.7}/>
      </mesh>:<mesh position={[0,.56,.14]} castShadow>
        <boxGeometry args={[.9,.12,.6]}/><meshStandardMaterial color="#a9c6d8"/>
      </mesh>}
      <Html center position={[0,1.3,0]} distanceFactor={22} style={{pointerEvents:'none'}}>
        <div className="machine-tag">{item.station.name} #{item.index+1}</div>
      </Html>
    </group>
  })}</>
}

function Factory(p:Props & {onDragState:(active:boolean)=>void}){
  const {plant,selected,onSelect,stations,time,events,editMode,snap,onAreaMove,onMoveStart,onMoveComplete,onDragState}=p
  const [dragging,setDragging]=useState(false)
  const areaMap=useMemo(()=>new Map(plant.areas.map(a=>[a.id,a])),[plant.areas])
  const busy=useMemo(()=>new Set(events.filter(e=>
    e.type==='start'&&e.station!==undefined&&e.machine_index!==undefined &&
    e.t<=time && time<e.t+(e.duration||0)).map(e=>e.station+'_'+e.machine_index)),[events,time])
  const visible=useMemo(()=>{
    const last=new Map<number,SimEvent>()
    for(const e of events)if(e.t<=time)last.set(e.job,e)
    return [...last.entries()].filter(([,e])=>e.type!=='complete').map(([job,event])=>({job,event}))
  },[events,time])
  function begin(){setDragging(true);onDragState(true);onMoveStart()}
  function complete(){setDragging(false);onDragState(false);onMoveComplete()}
  return <>
    <color attach="background" args={['#0d1727']}/>
    <ambientLight intensity={1.4}/>
    <hemisphereLight args={['#aec8ed','#233348',1]}/>
    <directionalLight castShadow position={[13,30,16]} intensity={2.1} shadow-mapSize={[1024,1024]}/>
    <mesh position={[plant.width/2,-.18,plant.depth/2]} receiveShadow>
      <boxGeometry args={[plant.width,.32,plant.depth]}/>
      <meshStandardMaterial color="#223247"/>
    </mesh>
    <gridHelper args={[Math.max(plant.width,plant.depth)*1.6,36,'#425d75','#27394e']}
      position={[plant.width/2,.02,plant.depth/2]}/>
    {plant.areas.map(area=><group key={area.id}
      position={[area.x+area.width/2,0,area.z+area.depth/2]}>
      <AreaTile area={area} selected={selected} onSelect={onSelect} editMode={editMode} snap={snap}
        onAreaMove={onAreaMove} onMoveStart={begin} onMoveComplete={complete}/>
      <Html center position={[0,1.85,0]} distanceFactor={18} style={{pointerEvents:'none'}}>
        <div className={'scene-label'+(selected===area.id?' selected':'')}>
          {area.name}<small>{area.width} × {area.depth} m</small>
        </div>
      </Html>
      <Equipment area={area} stations={stations} busy={busy}/>
      {selected===area.id&&<mesh position={[0,.26,0]}>
        <boxGeometry args={[area.width+.3,.09,area.depth+.3]}/>
        <meshStandardMaterial color="#8fffee" wireframe/>
      </mesh>}
    </group>)}
    {plant.flows.map((f,i)=>{
      const a=areaMap.get(f.source),b=areaMap.get(f.target)
      return a&&b?<Line key={i}
        points={[[a.x+a.width/2,.36,a.z+a.depth/2],[b.x+b.width/2,.36,b.z+b.depth/2]]}
        color="#b0e0f3" lineWidth={2} dashed dashSize={.5} gapSize={.3} transparent opacity={.7}/>:null
    })}
    {visible.map(({job,event})=>{
      const end=event.to||event.at||[0,0]
      const t=event.type==='move'&&event.from&&event.to
        ?Math.min(1,Math.max(0,(time-event.t)/(event.duration||.001))):1
      const x=event.type==='move'&&event.from?event.from[0]+(end[0]-event.from[0])*t:end[0]
      const z=event.type==='move'&&event.from?event.from[1]+(end[1]-event.from[1])*t:end[1]
      return <mesh key={job} position={[x,1.1,z]} castShadow>
        <boxGeometry args={[.43,.43,.43]}/>
        <meshStandardMaterial color="#d6faf9" emissive="#079fbd" emissiveIntensity={.6}/>
      </mesh>
    })}
    <OrbitControls makeDefault enabled={!dragging} target={[plant.width/2,0,plant.depth/2]}
      maxPolarAngle={Math.PI/2.1} minDistance={5} maxDistance={120}/>
  </>
}
export default function PlantScene(p:Props){
  return <Canvas shadows camera={{position:[36,31,44],fov:48,near:.1,far:400}} dpr={[1,1.6]}>
    <Factory {...p} onDragState={()=>{}}/>
  </Canvas>
}
