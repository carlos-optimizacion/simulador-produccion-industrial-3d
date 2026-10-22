import {useEffect,useState} from 'react'
import CartesianMap from './CartesianMap'
import {annealPlant, compareLayouts, corelapOrder} from './api'
import type {Plant, LayoutComparison, CorelapOrder, AnnealResult} from './types'

type Props={
 asIs:Plant
 toBe:Plant
 onApply:(plant:Plant)=>void
 onRestore:()=>void
 onError:(message:string)=>void
}
const currency=(value:number)=>new Intl.NumberFormat('es-PE',{style:'currency',currency:'PEN',maximumFractionDigits:2}).format(value)
const number=(value:number)=>new Intl.NumberFormat('es-PE',{maximumFractionDigits:2}).format(value)

export default function SpatialOptimization({asIs,toBe,onApply,onRestore,onError}:Props){
 const [report,setReport]=useState<LayoutComparison|null>(null)
 const [priorities,setPriorities]=useState<CorelapOrder|null>(null)
 const [result,setResult]=useState<AnnealResult|null>(null)
 const [loading,setLoading]=useState(false)
 const [seed,setSeed]=useState(42)
 const [iterations,setIterations]=useState(1200)
 const [step,setStep]=useState(1)
 useEffect(()=>{
   let active=true
   const timer=window.setTimeout(()=>{
     compareLayouts(asIs,toBe).then(r=>{if(active)setReport(r)})
       .catch(e=>{if(active){setReport(null);onError('Comparación AS-IS/TO-BE: '+String(e))}})
   },300)
   return ()=>{active=false;window.clearTimeout(timer)}
 },[asIs,toBe,onError])
 useEffect(()=>{
   let active=true
   corelapOrder(asIs).then(r=>{if(active)setPriorities(r)})
     .catch(e=>{if(active)onError('CORELAP TCR: '+String(e))})
   return ()=>{active=false}
 },[asIs,onError])
 async function anneal(){
   setLoading(true)
   try{
     const r=await annealPlant(toBe,{iterations,grid_step:step,temperature:75,cooling:.995,seed})
     setResult(r)
     onApply(r.plant)
   }catch(e){onError('Recocido simulado: '+String(e))}
   finally{setLoading(false)}
 }
 return <div className="spatial-stack">
  <section className="panel">
   <span className="eyebrow">DISTRIBUCIÓN EN COORDENADAS LOCALES</span>
   <h2>AS-IS vs. TO-BE</h2>
   <CartesianMap plant={asIs} caption="AS-IS · Línea base"/>
   <CartesianMap plant={toBe} caption="TO-BE · Propuesta editable"/>
   {report&&<>
    <div className="metric"><span>Costo AS-IS / turno</span><strong>{currency(report.cost_before)}</strong></div>
    <div className="metric"><span>Costo TO-BE / turno</span><strong>{currency(report.cost_after)}</strong></div>
    <div className="metric"><span>Ahorro proyectado / turno</span><strong>{currency(report.saving_per_shift)} ({number(report.saving_pct)}%)</strong></div>
    <div className="metric"><span>Distancia ponderada · AS-IS / TO-BE</span><strong className="small-result">{number(report.material_handling_weighted_distance_before)} / {number(report.material_handling_weighted_distance_after)} und·m</strong></div>
   </>}
   <button className="btn secondary full" onClick={onRestore}>Recuperar distribución AS-IS</button>
   <small className="caution">Comparación válida solo manteniendo las mismas áreas, dimensiones, flujos, costos y restricciones. Distancias Manhattan entre centroides.</small>
  </section>
  <section className="panel">
    <span className="eyebrow">OPTIMIZACIÓN METAHEURÍSTICA</span>
    <h2>Recocido simulado</h2>
    <div className="fields cols2">
      <label>Iteraciones<input type="number" min="1" max="20000" step="100" value={iterations}
        onChange={e=>setIterations(Math.max(1,Math.min(20000,Number(e.target.value)||1)))}/></label>
      <label>Semilla<input type="number" min="0" max="2147483647" value={seed}
        onChange={e=>setSeed(Math.max(0,Math.floor(Number(e.target.value)||0)))}/></label>
      <label>Cuadrícula (m)<select value={step} onChange={e=>setStep(Number(e.target.value))}>
       <option value=".25">0.25</option><option value=".5">0.50</option><option value="1">1.00</option><option value="2">2.00</option>
      </select></label>
    </div>
    <button className="btn primary full" onClick={()=>{void anneal()}} disabled={loading}>
      {loading?'Evaluando…':'Optimizar TO-BE por recocido'}
    </button>
    {result&&<div className="note">Última corrida: {result.valid_candidates} candidatos factibles, {result.accepted_uphill} movimientos peores aceptados, mejor costo {currency(result.after_cost)}.</div>}
    <small className="caution">Heurística reproducible; no garantiza el óptimo global ni sustituye la ingeniería de pasillos.</small>
  </section>
  <section className="panel">
    <span className="eyebrow">CORELAP · PRIORIDAD RELACIONAL</span>
    <h2>Orden preliminar TCR</h2>
    {priorities?.priority.map(p=><div className="rel-row" key={p.area_id}>
      <b>{p.rank}</b><span>{p.area_name}<small>TCR = {p.tcr} · Centro ({number(p.center_xy_m[0])}, {number(p.center_xy_m[1])}) m</small></span>
    </div>)}
    <small className="caution">Se calcula TCR y orden relacional. La colocación geométrica completa de CORELAP sigue pendiente.</small>
  </section>
 </div>
}
