import { Canvas } from '@react-three/fiber'
import { Html,OrbitControls,RoundedBox,Line } from '@react-three/drei'
import { useMemo } from 'react'
import type {Plant,Station,SimEvent} from './types'

type Props={plant:Plant;selected:string;onSelect:(id:string)=>void;stations:Station[];time:number;events:SimEvent[]}
function Equipment({area,stations,busy}:{area:Plant['areas'][number];stations:Station[];busy:Set<string>}){
 let offset=0
 const machinery=stations.filter(s=>s.area_id===area.id).flatMap(s=>Array.from({length:s.machines},(_,j)=>({id:s.id,key:s.id+'_'+j,index:offset+j})))
 return <>{machinery.map(e=>{
  const cols=Math.max(1,Math.floor(area.width/2.5)),col=e.index%cols,row=Math.floor(e.index/cols)
  return <group key={e.key} position={[-area.width/2+1.25+2.2*col,.65,-area.depth/2+1.35+2.2*row]}>
   <RoundedBox args={[1.45,1,1.25]} radius={.12} castShadow><meshStandardMaterial color={busy.has(e.id)?'#18c6a1':'#29455f'} metalness={.4}/></RoundedBox>
   <mesh position={[0,.54,.12]}><boxGeometry args={[.9,.1,.6]}/><meshStandardMaterial color="#a9c6d8"/></mesh>
  </group>
 })}</>
}
function Factory({plant,selected,onSelect,stations,time,events}:Props){
 const areaMap=useMemo(()=>new Map(plant.areas.map(a=>[a.id,a])),[plant.areas])
 const busy=useMemo(()=>new Set(events.filter(e=>e.type==='start'&&e.station&&e.t<=time&&time<e.t+(e.duration||0)).map(e=>e.station!)),[events,time])
 const visible=useMemo(()=>{
  const last=new Map<number,SimEvent>()
  for(const e of events)if(e.t<=time)last.set(e.job,e)
  return [...last.entries()].filter(([,e])=>e.type!=='complete').map(([job,event])=>({job,event}))
 },[events,time])
 return <>
 <color attach="background" args={['#0d1727']}/><ambientLight intensity={1.4}/>
 <hemisphereLight args={['#aec8ed','#233348',1]}/>
 <directionalLight castShadow position={[13,30,16]} intensity={2.1}/>
 <mesh position={[plant.width/2,-.18,plant.depth/2]} receiveShadow><boxGeometry args={[plant.width,.32,plant.depth]}/><meshStandardMaterial color="#223247"/></mesh>
 <gridHelper args={[Math.max(plant.width,plant.depth)*1.6,36,'#425d75','#27394e']} position={[plant.width/2,.02,plant.depth/2]}/>
 {plant.areas.map(area=><group key={area.id} position={[area.x+area.width/2,0,area.z+area.depth/2]}>
   <mesh position={[0,.12,0]} receiveShadow onClick={e=>{e.stopPropagation();onSelect(area.id)}}>
    <boxGeometry args={[area.width,.22,area.depth]}/><meshStandardMaterial color={area.color} transparent opacity={.74}/>
   </mesh>
   <Html center position={[0,1.75,0]} distanceFactor={18} style={{pointerEvents:'none'}}>
     <div className={'scene-label'+(selected===area.id?' selected':'')}>{area.name}<small>{area.width} × {area.depth} m</small></div>
   </Html>
   <Equipment area={area} stations={stations} busy={busy}/>
   {selected===area.id&&<mesh position={[0,.26,0]}><boxGeometry args={[area.width+.3,.09,area.depth+.3]}/><meshStandardMaterial color="#fff" wireframe/></mesh>}
 </group>)}
 {plant.flows.map((f,i)=>{
  const a=areaMap.get(f.source),b=areaMap.get(f.target)
  return a&&b?<Line key={i} points={[[a.x+a.width/2,.36,a.z+a.depth/2],[b.x+b.width/2,.36,b.z+b.depth/2]]} color="#c3e3f4" lineWidth={2} transparent opacity={.6} dashed dashSize={.5} gapSize={.3}/>:null
 })}
 {visible.map(({job,event})=>{
  const a=event.at||event.to||[0,0]
  const u=event.type==='move'&&event.from&&event.to?Math.min(1,Math.max(0,(time-event.t)/(event.duration||.001))):1
  const x=event.type==='move'&&event.from?event.from[0]+(a[0]-event.from[0])*u:a[0]
  const z=event.type==='move'&&event.from?event.from[1]+(a[1]-event.from[1])*u:a[1]
  return <mesh key={job} position={[x,1.02,z]}><sphereGeometry args={[.27,12,12]}/><meshStandardMaterial color="#e0f2fe" emissive="#009ddb" emissiveIntensity={.6}/></mesh>
 })}
 <OrbitControls makeDefault target={[plant.width/2,0,plant.depth/2]} maxPolarAngle={Math.PI/2.1} minDistance={5} maxDistance={120}/>
 </>
}
export default function PlantScene(p:Props){return <Canvas shadows camera={{position:[36,31,44],fov:48,near:.1,far:400}} dpr={[1,1.6]}><Factory {...p}/></Canvas>}
