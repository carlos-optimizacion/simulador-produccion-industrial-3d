import type {Plant} from './types'

/** Scaled engineering floor plan. Local world X,Z maps to drawing X,Y (Y upward). */
export default function CartesianMap({plant,caption}:{plant:Plant;caption:string}){
 const scale=8
 const margin=28
 const w=plant.width*scale+margin*2
 const h=plant.depth*scale+margin*2
 const px=(x:number)=>margin+x*scale
 const py=(z:number)=>margin+(plant.depth-z)*scale
 const center=(id:string)=>{
  const a=plant.areas.find(x=>x.id===id)
  return a?[a.x+a.width/2,a.z+a.depth/2] as [number,number]:null
 }
 const ticksX=Array.from({length:Math.floor(plant.width/5)+1},(_,i)=>i*5)
 const ticksY=Array.from({length:Math.floor(plant.depth/5)+1},(_,i)=>i*5)
 return <figure className="map-figure">
  <figcaption>{caption} <small>Plano X,Y (metros)</small></figcaption>
  <svg className="cartesian-map" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={'Plano cartesiano '+caption}>
    <rect x={margin} y={margin} width={plant.width*scale} height={plant.depth*scale} fill="#0b2435" stroke="#91abc4" strokeWidth={1.5}/>
    {ticksX.map(x=><g key={'x'+x}>
      <line x1={px(x)} y1={margin} x2={px(x)} y2={py(0)} stroke="#5a8499" strokeOpacity=".25"/>
      <text x={px(x)} y={py(0)+14} fontSize="10" textAnchor="middle" fill="#b5cede">{x}</text>
    </g>)}
    {ticksY.map(y=><g key={'y'+y}>
      <line x1={margin} y1={py(y)} x2={px(plant.width)} y2={py(y)} stroke="#5a8499" strokeOpacity=".25"/>
      <text x={margin-7} y={py(y)+4} fontSize="10" textAnchor="end" fill="#b5cede">{y}</text>
    </g>)}
    <text x={w-9} y={py(0)+16} fontSize="10" fill="#9adbd7">X →</text>
    <text x={margin-6} y="14" fontSize="10" fill="#9adbd7">↑ Y</text>
    {plant.areas.map(a=><g key={a.id}>
      <rect x={px(a.x)} y={py(a.z+a.depth)} width={a.width*scale} height={a.depth*scale}
        rx="2" fill={a.color} fillOpacity=".5" stroke={a.color} strokeWidth="1.5"/>
      <text x={px(a.x+a.width/2)} y={py(a.z+a.depth/2)+3}
        textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="bold">{a.id.slice(0,11)}</text>
      <circle cx={px(a.x+a.width/2)} cy={py(a.z+a.depth/2)} r="2.5" fill="white"/>
    </g>)}
    {plant.flows.map((f,i)=>{
      const a=center(f.source),b=center(f.target)
      if(!a||!b)return null
      const middleX=px(b[0])
      return <polyline key={i} points={`${px(a[0])},${py(a[1])} ${middleX},${py(a[1])} ${px(b[0])},${py(b[1])}`}
        fill="none" stroke="#e7d493" strokeOpacity=".75" strokeWidth="1.5" strokeDasharray="4 4"/>
    })}
  </svg>
  <small>Centroides y trazos rectilíneos de referencia. No equivalen a pasillos reales.</small>
 </figure>
}
