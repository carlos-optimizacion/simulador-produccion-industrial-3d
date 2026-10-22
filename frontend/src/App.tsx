import {useEffect,useMemo,useState} from 'react'
import PlantScene from './PlantScene'
import {analyzePlant,optimizePlant,simulatePlant} from './api'
import {demoPlant,demoProduction} from './demo'
import type {Area,Plant,Station,LayoutAnalysis,SimResult} from './types'
import './styles.css'

const stages=['Configuración','SLP y distribución 3D','Simulación dinámica','Resultados']
const money=(n:number)=>new Intl.NumberFormat('es-PE',{style:'currency',currency:'PEN'}).format(n)
const fixed=(n:number)=>new Intl.NumberFormat('es-PE',{maximumFractionDigits:2}).format(n)
function Num({value,onChange,min=0,step=.5}:{value:number;onChange:(n:number)=>void;min?:number;step?:number}){
 return <input type="number" min={min} step={step} value={value} onChange={e=>{const n=e.target.valueAsNumber;if(Number.isFinite(n))onChange(n)}}/>
}
export default function App(){
 const [plant,setPlant]=useState<Plant>(()=>structuredClone(demoPlant))
 const [stations,setStations]=useState<Station[]>(()=>structuredClone(demoProduction.stations))
 const [quantity,setQuantity]=useState(12)
 const [stage,setStage]=useState(0)
 const [selected,setSelected]=useState('corte')
 const [analysis,setAnalysis]=useState<LayoutAnalysis|null>(null)
 const [simulation,setSimulation]=useState<SimResult|null>(null)
 const [comparison,setComparison]=useState<{saving_pct:number}|null>(null)
 const [message,setMessage]=useState('')
 const [busy,setBusy]=useState(false)
 const [clock,setClock]=useState(0)
 const [playing,setPlaying]=useState(false)
 const [speed,setSpeed]=useState(5)
 const selectedArea=plant.areas.find(a=>a.id===selected)
 const operations=demoProduction.operations.filter(o=>stations.some(s=>s.id===o.station_id))
 const maxTime=simulation?.makespan_min||0
 const lastEvent=useMemo(()=>simulation?.events.filter(e=>e.t<=clock).at(-1),[simulation,clock])
 function invalidate(){setAnalysis(null);setSimulation(null);setComparison(null);setPlaying(false);setClock(0)}
 function patchArea(id:string,key:keyof Area,value:number){setPlant(p=>({...p,areas:p.areas.map(a=>a.id===id?{...a,[key]:value}:a)}));invalidate()}
 function patchStation(id:string,delta:number){setStations(s=>s.map(x=>x.id===id?{...x,machines:Math.max(1,x.machines+delta)}:x));invalidate()}
 useEffect(()=>{
   if(!playing||!simulation)return
   let raf=0;let last=performance.now()
   const tick=(now:number)=>{const dt=Math.min((now-last)/1000,.12);last=now
     setClock(v=>{const next=v+dt*speed;if(next>=maxTime){setPlaying(false);return maxTime}return next})
     raf=requestAnimationFrame(tick)}
   raf=requestAnimationFrame(tick)
   return()=>cancelAnimationFrame(raf)
 },[playing,simulation,maxTime,speed])
 async function evaluate(){
  setBusy(true);setMessage('');setPlaying(false)
  try{setAnalysis(await analyzePlant(plant));setStage(1)}
  catch(e){setMessage('No se pudo evaluar la distribución. Comprueba la API: '+String(e))}
  finally{setBusy(false)}
 }
 async function optimize(){
  setBusy(true);setMessage('')
  try{const r=await optimizePlant(plant);setPlant(r.plant);setAnalysis(r.analysis);setComparison({saving_pct:r.saving_pct});setSimulation(null);setSelected('')}
  catch(e){setMessage('Error SLP: '+String(e))}
  finally{setBusy(false)}
 }
 async function run(){
  setBusy(true);setMessage('');setPlaying(false)
  try{
   const a=await analyzePlant(plant);setAnalysis(a)
   if(!a.valid){setMessage('Corrige los conflictos geométricos antes de simular.');return}
   const result=await simulatePlant({plant,stations,operations,quantity,travel_speed_m_min:demoProduction.travel_speed_m_min})
   setSimulation(result);setClock(0);setStage(2);setPlaying(true)
  }catch(e){setMessage('No se pudo simular: '+String(e))}
  finally{setBusy(false)}
 }
 function reset(){setPlant(structuredClone(demoPlant));setStations(structuredClone(demoProduction.stations));setQuantity(12);setStage(0);setSelected('corte');setMessage('');invalidate()}
 const title=stages[stage]
 return <div className="shell">
  <header className="topbar"><div className="brand"><div className="logo">I<span>3</span></div><div><strong>INDUSIM <em>3D</em></strong><small>SIMULACIÓN · OPTIMIZACIÓN · SLP</small></div></div><div className="build"><span className="live-dot"/> MVP 0.1 · THREE.JS</div></header>
  <div className="workspace">
   <aside className="sidebar">
    <span className="eyebrow">PROCESO INDUSTRIAL</span>
    {stages.map((name,i)=><button key={name} className={'nav-step '+(stage===i?'active':'')} disabled={i>stage&&!(i===3&&!!simulation)} onClick={()=>{setPlaying(false);setStage(i)}}><span className="step-num">{i+1}</span>{name}</button>)}
    <div className="aside-foot"><strong>Principio de diseño</strong><p>Los datos se ingresan antes de ejecutar la simulación. El entorno 3D representa la cantidad exacta de máquinas configuradas.</p><button className="btn secondary" onClick={reset}>↺ Restablecer demostración</button></div>
   </aside>
   <main className="content">
    <div className="page-heading"><div><span className="eyebrow">INDUSIM / PROYECTO INDUSTRIAL</span><h1>{stage===0?'Datos de la planta':title}</h1><p>{stage===0?'Define espacios, flujos, máquinas y demanda antes de simular.':stage===1?'Analiza la distribución y compara alternativas de layout.':stage===2?'Observa los eventos operativos calculados por el motor.':'Indicadores gerenciales de la simulación y del análisis SLP.'}</p></div><span className="pill">ETAPA 0{stage+1} / 04</span></div>
    {message&&<div className="error" role="alert">{message} <button onClick={()=>setMessage('')}>×</button></div>}
    {stage===0&&<div className="configure">
      <section className="panel wide"><div className="section-title"><h2>01 · Dimensiones y áreas</h2><span className="pill">{plant.areas.length} áreas</span></div>
       <label>Nombre de la planta<input value={plant.name} onChange={e=>{setPlant(p=>({...p,name:e.target.value}));invalidate()}}/></label>
       <div className="fields cols3"><label>Ancho de planta (m)<Num min={1} step={1} value={plant.width} onChange={v=>{setPlant(p=>({...p,width:v}));invalidate()}}/></label><label>Fondo (m)<Num min={1} step={1} value={plant.depth} onChange={v=>{setPlant(p=>({...p,depth:v}));invalidate()}}/></label><label>Separación (m)<Num value={plant.clearance} step={.25} onChange={v=>{setPlant(p=>({...p,clearance:v}));invalidate()}}/></label></div>
       <div className="scroll"><table><thead><tr><th>Área</th><th>X</th><th>Z</th><th>Ancho</th><th>Fondo</th></tr></thead><tbody>{plant.areas.map(a=><tr key={a.id}><td><span className="swatch" style={{background:a.color}}/>{a.name}</td>{(['x','z','width','depth'] as const).map(key=><td key={key}><Num value={a[key]} min={key==='width'||key==='depth'?.25:0} onChange={v=>patchArea(a.id,key,v)}/></td>)}</tr>)}</tbody></table></div>
      </section>
      <section className="panel"><h2>02 · Recursos productivos</h2><label>Unidades a fabricar<Num min={1} step={1} value={quantity} onChange={v=>{setQuantity(Math.max(1,Math.min(1000,Math.floor(v))));invalidate()}}/></label>
       {stations.map(s=><div className="station" key={s.id}><div><b>{s.name}</b><small>{s.area_id}</small></div><div className="counter"><button onClick={()=>patchStation(s.id,-1)}>−</button><strong>{s.machines}</strong><button onClick={()=>patchStation(s.id,1)}>+</button></div></div>)}
       <div className="note">El motor calcula la capacidad según los equipos registrados. No agrega máquinas ficticias.</div>
      </section>
      <section className="panel wide"><h2>03 · Flujos From-To</h2><div className="scroll"><table><thead><tr><th>Origen</th><th>Destino</th><th>Und./turno</th><th>S/ por und·m</th></tr></thead><tbody>{plant.flows.map((f,i)=><tr key={i}><td>{f.source}</td><td>{f.target}</td><td><Num value={f.units_per_shift} step={1} onChange={v=>{setPlant(p=>({...p,flows:p.flows.map((x,j)=>i===j?{...x,units_per_shift:v}:x)}));invalidate()}}/></td><td><Num value={f.cost_per_unit_meter} step={.01} onChange={v=>{setPlant(p=>({...p,flows:p.flows.map((x,j)=>i===j?{...x,cost_per_unit_meter:v}:x)}));invalidate()}}/></td></tr>)}</tbody></table></div></section>
      <div className="actions"><p>Primero se configuran los parámetros. Después se evalúa el layout.</p><button className="btn primary" disabled={busy} onClick={evaluate}>{busy?'Analizando…':'Evaluar SLP y ver planta 3D →'}</button></div>
    </div>}
    {stage>=1&&<div className="split">
      <section className="viewer-panel"><div className="viewer-title"><div><span className="eyebrow">CONSTRUCTOR INDUSTRIAL</span><h2>{plant.name}</h2></div><span className="pill">3D INTERACTIVO</span></div>
       <div className="canvas-wrap"><PlantScene plant={plant} selected={selected} onSelect={setSelected} stations={stations} time={clock} events={stage===2?simulation?.events||[]:[]}/><div className="canvas-hint">Rotar: arrastrar · Zoom: rueda · Seleccionar: clic</div></div>
      </section>
      <aside className="inspector">
       {stage===1&&<>
        <section className="panel"><span className="eyebrow">ANÁLISIS SLP</span><h2>Evaluación del layout</h2>{analysis&&<div className="metric"><span>Costo por turno</span><strong>{money(analysis.material_handling_cost_per_shift)}</strong></div>}
        <div className={'validation '+(!analysis?.valid?'invalid':'')}>{analysis?.valid?'✓ Distribución geométricamente factible':analysis?analysis.violations.length+' conflicto(s) de geometría':'Pendiente de evaluar'}</div>
        {analysis?.violations.map((v,i)=><p className="problem" key={i}>{v.type}: {v.areas.join(', ')}</p>)}
        {comparison&&<div className="saving">Ahorro estimado: {fixed(comparison.saving_pct)}%</div>}
        <button className="btn primary full" disabled={busy||!analysis?.valid} onClick={optimize}>Optimizar distribución</button>
        <button className="btn secondary full" disabled={busy} onClick={evaluate}>Recalcular SLP</button>
        <small className="caution">Estimación Manhattan entre centroides; no incluye corredores reales ni comprobaciones normativas.</small>
        </section>
        <section className="panel"><span className="eyebrow">ÁREA SELECCIONADA</span><h2>{selectedArea?.name||'Seleccione un área'}</h2>{selectedArea&&<div className="fields cols2">{(['x','z','width','depth'] as const).map(k=><label key={k}>{k==='width'?'Ancho':k==='depth'?'Fondo':k.toUpperCase()} (m)<Num value={selectedArea[k]} min={k==='width'||k==='depth'?.25:0} onChange={v=>patchArea(selectedArea.id,k,v)}/></label>)}</div>}</section>
        <section className="panel"><span className="eyebrow">MATRIZ REL</span>{plant.relationships.map((r,i)=><div className="rel-row" key={i}><b>{r.rating}</b><span>{r.source} → {r.target}<small>{r.reason}</small></span></div>)}</section>
        <button className="btn primary full" disabled={busy||!analysis?.valid} onClick={run}>Ejecutar simulación →</button><button className="btn secondary full" onClick={()=>setStage(0)}>← Modificar datos</button>
       </>}
       {stage===2&&simulation&&<>
        <section className="panel"><span className="eyebrow">RELOJ VIRTUAL</span><h2>Reproducción</h2><div className="metric"><span>Tiempo simulado</span><strong>{fixed(clock)} / {fixed(maxTime)} min</strong></div>
        <input type="range" aria-label="Tiempo de simulación" min={0} max={maxTime} step={.01} value={clock} onChange={e=>{setClock(Number(e.target.value));setPlaying(false)}}/>
        <div className="buttons"><button className="btn primary" onClick={()=>{if(clock>=maxTime)setClock(0);setPlaying(v=>!v)}}>{playing?'Ⅱ Pausar':'▶ Reproducir'}</button><button className="btn secondary" onClick={()=>{setClock(0);setPlaying(false)}}>Reiniciar</button></div>
        <label>Velocidad<select value={speed} onChange={e=>setSpeed(Number(e.target.value))}><option value={1}>1 min/s</option><option value={5}>5 min/s</option><option value={15}>15 min/s</option></select></label>
        <div className="note">Último evento: {lastEvent?'Unidad '+lastEvent.job+' · '+lastEvent.type:'Inicio'}</div></section>
        <section className="panel"><h2>Producción</h2><div className="metric"><span>Unidades completadas al finalizar</span><strong>{simulation.units_completed}</strong></div><div className="metric"><span>Duración</span><strong>{fixed(simulation.makespan_min)} min</strong></div><div className="metric"><span>Espera media</span><strong>{fixed(simulation.avg_queue_wait_min)} min</strong></div><button className="btn primary full" onClick={()=>{setStage(3);setPlaying(false)}}>Ver indicadores →</button><button className="btn secondary full" onClick={()=>{setStage(1);setPlaying(false)}}>← Volver a SLP</button></section>
       </>}
       {stage===3&&simulation&&<section className="panel"><span className="eyebrow">INDICADORES GERENCIALES</span><h2>Resultados del escenario</h2><div className="metric"><span>Volumen producido</span><strong>{simulation.units_completed} und.</strong></div><div className="metric"><span>Productividad</span><strong>{fixed(simulation.throughput_units_per_hour)} und./h</strong></div><div className="metric"><span>Costo SLP por turno</span><strong>{analysis?money(analysis.material_handling_cost_per_shift):'—'}</strong></div>
       <h3>Utilización de máquinas</h3>{simulation.stations.map(s=><div className="util" key={s.id}><span>{s.id} · {s.machines} equipo(s) — {fixed(s.utilization_pct)}%</span><div className="track"><span style={{width:String(Math.min(100,s.utilization_pct))+'%'}}/></div></div>)}
       <button className="btn secondary full" onClick={()=>setStage(2)}>← Ver simulación</button></section>}
      </aside>
    </div>}
    {stage===3&&<div className="note post">Resultados demostrativos de un sistema determinista. No constituyen un gemelo digital calibrado ni una evaluación de seguridad industrial.</div>}
   </main>
  </div>
 </div>
}
