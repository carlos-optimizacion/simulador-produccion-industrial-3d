import {useMemo,useState} from 'react'

type AggregatePeriod={period:number;demand:number;workers:number;hires:number;layoffs:number;regular:number;overtime:number;subcontract:number;inventory:number;backlog:number;internal_production:number;available_regular_units:number}
type AggregateResult={method:string;total_cost:number;periods:AggregatePeriod[];mps_internal_units_per_period:number[];cost_breakdown:Record<string,number>}
type MPSProduct={sku:string;effective_demand:number[];planned_completions:number[];planned_releases:number[];projected_ending_inventory:number[];lot_size:number;manufacturing_lead_time:number;setups:number[];setup_cost:number;total_setup_cost:number;atp_non_cumulative:(number|null)[]}
type MPSResult={products:MPSProduct[];periods:number;capacity_used_minutes:number[];available_minutes_per_period:number[];total_cost:number;demand_policy:string}
type MRPItem={sku:string;kind:string;gross_requirements:number[];scheduled_receipts:number[];net_requirements:number[];planned_order_receipts:number[];planned_order_releases:number[];projected_inventory:number[]|null}
type MRPResult={items:MRPItem[];feasible_within_horizon:boolean;release_before_horizon:{sku:string;needed_period:number;release_period:number;quantity:number}[];end_item_shortages:{sku:string;period:number;missing_units:number}[]}
type Sku = 'A'|'B'
const skus:Sku[]=['A','B']
const initialForecast:Record<Sku,number[]>={A:[12,14,12,14],B:[8,12,14,10]}
const unitMinutes:Record<Sku,number>={A:4,B:6}
const fmt=(n:number)=>new Intl.NumberFormat('es-PE',{maximumFractionDigits:2}).format(n)
const soles=(n:number)=>new Intl.NumberFormat('es-PE',{style:'currency',currency:'PEN'}).format(n)
const BACKEND=(import.meta.env.VITE_API_URL||'http://localhost:8000').replace(/[/]$/, '')
async function callAPI<T>(endpoint:string,payload:unknown):Promise<T>{
 const response=await fetch(BACKEND+endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
 if(!response.ok){
   const result=await response.json().catch(()=>({detail:'Servidor no disponible'}))
   throw new Error(typeof result.detail==='string'?result.detail:JSON.stringify(result.detail))
 }
 return await response.json() as T
}
function Numeric({value,set,min=0,step=1,max}: {value:number;set:(x:number)=>void;min?:number;step?:number;max?:number}){
 return <input type="number" value={value} min={min} max={max} step={step}
   onChange={e=>{const val=e.target.valueAsNumber;if(Number.isFinite(val)){set(max===undefined?Math.max(min,val):Math.max(min,Math.min(max,val)))}}}/>
}
export default function PlanningPage(){
 const [forecast,setForecast]=useState<Record<Sku,number[]>>(()=>structuredClone(initialForecast))
 const [initialStaff,setInitialStaff]=useState(2)
 const [maxStaff,setMaxStaff]=useState(4)
 const [unitsPerWorker,setUnitsPerWorker]=useState(15)
 const [maxOvertime,setMaxOvertime]=useState(5)
 const [minutesAvailable,setMinutesAvailable]=useState([180,180,180,180])
 const [allowBacklog,setAllowBacklog]=useState(false)
 const [policy,setPolicy]=useState('mixed')
 const [backlogCost,setBacklogCost]=useState(10)
 const [subcontractLimit,setSubcontractLimit]=useState(0)
 const [setupBySku,setSetupBySku]=useState<Record<Sku,number>>({A:60,B:45})
 const [policyResults,setPolicyResults]=useState<{results:{policy:string;status:string;total_cost:number|null}[];best_feasible_policy:string|null}|null>(null)
 const [stockSteel,setStockSteel]=useState(80)
 const [stockPackaging,setStockPackaging]=useState(30)
 const [steelLead,setSteelLead]=useState(1)
 const [packagingLead,setPackagingLead]=useState(1)
 const [aggregate,setAggregate]=useState<AggregateResult|null>(null)
 const [mps,setMps]=useState<MPSResult|null>(null)
 const [mrp,setMrp]=useState<MRPResult|null>(null)
 const [busy,setBusy]=useState('')
 const [error,setError]=useState('')
 const demand=useMemo(()=>forecast.A.map((a,t)=>a+forecast.B[t]),[forecast])
 function invalidate(){setAggregate(null);setMps(null);setMrp(null);setPolicyResults(null);setError('')}
 function aggregatePayload(){return {
      demand,initial_workers:initialStaff,max_workers:Math.max(initialStaff,maxStaff),
      initial_inventory:0,target_ending_inventory:0,units_per_worker_period:unitsPerWorker,
      overtime_units_per_worker:maxOvertime,max_subcontract_per_period:subcontractLimit,
      worker_period_cost:150,hiring_cost:20,layoff_cost:40,
      regular_unit_cost:2,overtime_unit_cost:4,subcontract_unit_cost:12,
      holding_unit_cost:.5,backlog_unit_cost:backlogCost,allow_backlog:allowBacklog,policy
 }}
 async function runComparison(){
   setBusy('POLICY');setError('')
   try{
     setPolicyResults(await callAPI('/api/planning/aggregate/scenarios',aggregatePayload()))
   }catch(e){setError('Comparación de escenarios APP: '+String(e))}
   finally{setBusy('')}
 }
 function patchForecast(sku:Sku,t:number,val:number){
   setForecast(old=>({...old,[sku]:old[sku].map((x,i)=>i===t?Math.max(0,Math.floor(val)):x)}));invalidate()
 }
 async function runAggregate(){
   setBusy('APP');setError('');setAggregate(null);setMps(null);setMrp(null)
   try{
     const out=await callAPI<AggregateResult>('/api/planning/aggregate/v2',aggregatePayload())
     setAggregate(out)
   }catch(e){setError('Planificación agregada: '+String(e))}
   finally{setBusy('')}
 }
 async function runMps(){
   if(!aggregate)return
   setBusy('MPS');setError('');setMps(null);setMrp(null)
   try{
     const out=await callAPI<MPSResult>('/api/planning/mps',{
       products:skus.map(sku=>({sku,initial_inventory:0,safety_stock:0,lot_size:2,manufacturing_lead_time:0,
                                  unit_production_cost:sku==='A'?2:2.5,unit_holding_cost:.3,setup_cost:setupBySku[sku]})),
       forecast,firm_orders:{},minutes_per_unit:unitMinutes,
       available_minutes_per_period:minutesAvailable,
       aggregate_capacity_units:aggregate.mps_internal_units_per_period
     })
     setMps(out)
   }catch(e){setError('MPS: '+String(e)+' — La solución APP puede requerir una reconciliación de capacidad o de mix de productos.')}
   finally{setBusy('')}
 }
 async function runMrp(){
   if(!mps)return
   setBusy('MRP');setError('');setMrp(null)
   try{
     const out=await callAPI<MRPResult>('/api/planning/mrp',{
       items:[
         {sku:'A',lead_time_periods:0},
         {sku:'B',lead_time_periods:0},
         {sku:'ACERO',lead_time_periods:steelLead,on_hand:stockSteel,safety_stock:10,lot_multiple:10},
         {sku:'EMPAQUE',lead_time_periods:packagingLead,on_hand:stockPackaging,safety_stock:0,lot_multiple:10}
       ],
       bom:[
         {parent:'A',component:'ACERO',quantity_per_parent:2},
         {parent:'B',component:'ACERO',quantity_per_parent:1},
         {parent:'A',component:'EMPAQUE',quantity_per_parent:1},
         {parent:'B',component:'EMPAQUE',quantity_per_parent:1}
       ],
       mps_planned_completions:Object.fromEntries(mps.products.map(p=>[p.sku,p.planned_completions])),
       end_item_gross_requirements:Object.fromEntries(mps.products.map(p=>[p.sku,p.effective_demand]))
     })
     setMrp(out)
   }catch(e){setError('MRP: '+String(e))}
   finally{setBusy('')}
 }
 return <div className="planning-page">
   <div className="page-heading"><div><span className="eyebrow">INDUSIM / PLANIFICACIÓN DE PRODUCCIÓN</span>
     <h1>APP · MPS · MRP</h1>
     <p>Optimización jerárquica con decisiones enteras, capacidad productiva y lista de materiales.</p>
   </div><span className="pill">MÓDULO v0.5 · DEMOSTRACIÓN EDITABLE</span></div>
   <div className="note">Ejemplo de 4 períodos y dos productos (A y B), pertenecientes a una misma familia.
    Las cifras monetarias y productividades son <strong>hipótesis de demostración</strong>, no datos calibrados de una planta real.
    Cada cambio invalida los planes posteriores hasta volver a calcularlos.</div>
   {error&&<div className="error" role="alert">{error}<button onClick={()=>setError('')}>×</button></div>}
   <div className="plan-layout">
     <section className="panel">
       <span className="eyebrow">PASO 01 / MIX DE DEMANDA</span><h2>Demanda prevista de productos</h2>
       <div className="scroll"><table><thead><tr><th>SKU</th>{demand.map((_,i)=><th key={i}>P{i+1}</th>)}</tr></thead><tbody>
         {skus.map(sku=><tr key={sku}><td>{sku}</td>{forecast[sku].map((v,t)=><td key={t}>
           <Numeric min={0} value={v} set={n=>patchForecast(sku,t,n)}/></td>)}</tr>)}
         <tr><td><b>Familia APP</b></td>{demand.map((v,t)=><td key={t}><b>{v}</b></td>)}</tr>
       </tbody></table></div>
       <div className="fields cols3">
         <label>Dotación inicial<Numeric value={initialStaff} min={0} set={v=>{setInitialStaff(Math.floor(v));if(v>maxStaff)setMaxStaff(v);invalidate()}}/></label>
         <label>Máximo trabajadores<Numeric value={maxStaff} min={initialStaff||1} set={v=>{setMaxStaff(Math.floor(v));invalidate()}}/></label>
         <label>Capacidad regular (und./trabajador·período)<Numeric value={unitsPerWorker} min={1} set={v=>{setUnitsPerWorker(Math.floor(v));invalidate()}}/></label>
         <label>Capacidad extra (und./trabajador·período)<Numeric value={maxOvertime} min={0} set={v=>{setMaxOvertime(Math.floor(v));invalidate()}}/></label>
       </div>
       <div className="fields cols2">
        <label>Política APP
          <select value={policy} onChange={e=>{setPolicy(e.target.value);invalidate()}}>
           <option value="mixed">Mixta · mínimo costo</option>
           <option value="level">Nivelación</option>
           <option value="chase">Persecución</option>
           <option value="no_layoffs">Sin despidos</option>
           <option value="no_outsourcing">Sin subcontratación</option>
           <option value="no_overtime">Sin horas extra</option>
          </select>
        </label>
        <label>Máx. subcontratación (und./período)<Numeric value={subcontractLimit} min={0}
         set={v=>{setSubcontractLimit(Math.floor(v));invalidate()}}/></label>
        <label className="planning-check"><input type="checkbox" checked={allowBacklog}
          onChange={e=>{setAllowBacklog(e.target.checked);invalidate()}}/> Permitir pedidos atrasados (backlog)</label>
        {allowBacklog&&<label>Penalidad backlog (S/ por und·período)
          <Numeric value={backlogCost} min={0} step={.5} set={v=>{setBacklogCost(v);invalidate()}}/>
        </label>}
       </div>
       <button className="btn primary full" disabled={!!busy} onClick={()=>void runAggregate()}>
         {busy==='APP'?'Optimizando…':'1 · Optimizar Planificación Agregada'}
       </button>
       <button className="btn secondary full" disabled={!!busy} onClick={()=>void runComparison()}>
         Comparar seis políticas de planificación
       </button>
     </section>
     <section className="panel">
       <span className="eyebrow">RESULTADO APP · PROGRAMACIÓN ENTERA</span>
       <h2>Personal, inventario y producción</h2>
       {aggregate?<><div className="metric"><span>Costo mínimo APP del escenario</span><strong>{soles(aggregate.total_cost)}</strong></div>
        <div className="scroll"><table><thead><tr><th>Período</th><th>Dem.</th><th>Trab.</th><th>Regular</th><th>Extra</th><th>Invent.</th><th>Backlog</th></tr></thead>
         <tbody>{aggregate.periods.map(p=><tr key={p.period}><td>P{p.period}</td><td>{p.demand}</td><td>{p.workers}</td>
         <td>{p.regular}</td><td>{p.overtime}</td><td>{p.inventory}</td><td>{p.backlog}</td></tr>)}</tbody></table></div>
       </>:<div className="planning-empty">Completa la demanda y ejecuta la optimización APP.</div>}
       {policyResults&&<div className="scroll"><table><thead><tr><th>Política</th><th>Costo APP</th><th>Factible</th></tr></thead>
         <tbody>{policyResults.results.map(row=><tr key={row.policy}><td>{row.policy}</td>
           <td>{row.total_cost===null?'—':soles(row.total_cost)}</td><td>{row.status==='optimal'?'Sí':'No'}</td></tr>)}</tbody>
       </table></div>}
     </section>
     <section className="panel">
       <span className="eyebrow">PASO 02 / DESAGREGACIÓN POR SKU</span>
       <h2>MPS — capacidad finita</h2>
       <p className="planning-explain">El MPS utiliza la capacidad interna aprobada por APP. Los productos requieren 4 y 6 min/unidad, respectivamente. Se contabiliza el costo fijo de cada preparación.</p>
       <div className="fields cols2">
         {skus.map(sku=><label key={sku}>Setup {sku} (S/ por corrida)
          <Numeric value={setupBySku[sku]} min={0} set={v=>{setSetupBySku(old=>({...old,[sku]:v}));setMps(null);setMrp(null)}}/></label>)}
       </div>
       <div className="scroll"><table><thead><tr><th>Capacidad (min.)</th>{minutesAvailable.map((_,i)=><th key={i}>P{i+1}</th>)}</tr></thead>
        <tbody><tr><td>Disponible</td>{minutesAvailable.map((v,i)=><td key={i}><Numeric value={v} min={1}
          set={n=>{setMinutesAvailable(old=>old.map((x,j)=>i===j?n:x));setMps(null);setMrp(null)}}/></td>)}</tr>
          {aggregate&&<tr><td>APP (und. internas)</td>{aggregate.mps_internal_units_per_period.map((v,i)=><td key={i}>{v}</td>)}</tr>}
       </tbody></table></div>
       <button className="btn primary full" disabled={!aggregate||!!busy} onClick={()=>void runMps()}>
         {busy==='MPS'?'Resolviendo…':'2 · Optimizar Plan Maestro de Producción'}
       </button>
     </section>
     <section className="panel">
       <span className="eyebrow">RESULTADO MPS</span><h2>Órdenes terminadas por período</h2>
       {mps?<><div className="metric"><span>Costo variable e inventario MPS</span><strong>{soles(mps.total_cost)}</strong></div>
        <div className="scroll"><table><thead><tr><th>Producto</th>{minutesAvailable.map((_,i)=><th key={i}>P{i+1}</th>)}</tr></thead>
        <tbody>{mps.products.map(p=><tr key={p.sku}><td>{p.sku}</td>{p.planned_completions.map((v,i)=><td key={i}>{v}</td>)}</tr>)}
        <tr><td>Min. utilizados</td>{mps.capacity_used_minutes.map((v,i)=><td key={i}>{fmt(v)}</td>)}</tr>
        {mps.products.map(p=><tr key={p.sku+'-setup'}><td>Preparaciones {p.sku}</td>
          {p.setups.map((v,i)=><td key={i}>{v}</td>)}</tr>)}
        {mps.products.map(p=><tr key={p.sku+'-atp'}><td>ATP {p.sku}</td>
          {p.atp_non_cumulative.map((v,i)=><td key={i}>{v===null?'—':v}</td>)}</tr>)}
        </tbody></table></div>
       </>:<div className="planning-empty">Primero optimiza APP y después ejecuta MPS.</div>}
     </section>
     <section className="panel">
       <span className="eyebrow">PASO 03 / BOM MULTINIVEL</span><h2>MRP — explosión de materiales</h2>
       <p className="planning-explain">BOM: A utiliza 2 unidades de acero y 1 empaque; B utiliza 1 unidad de acero y 1 empaque.</p>
       <div className="fields cols2">
        <label>Acero disponible (unidades)<Numeric value={stockSteel} min={0} set={v=>{setStockSteel(Math.floor(v));setMrp(null)}}/></label>
        <label>Lead time acero (períodos)<Numeric value={steelLead} min={0} max={24} set={v=>{setSteelLead(Math.floor(v));setMrp(null)}}/></label>
        <label>Empaques disponibles<Numeric value={stockPackaging} min={0} set={v=>{setStockPackaging(Math.floor(v));setMrp(null)}}/></label>
        <label>Lead time empaques<Numeric value={packagingLead} min={0} max={24} set={v=>{setPackagingLead(Math.floor(v));setMrp(null)}}/></label>
       </div>
       <button className="btn primary full" disabled={!mps||!!busy} onClick={()=>void runMrp()}>
         {busy==='MRP'?'Calculando…':'3 · Calcular necesidades y liberaciones MRP'}
       </button>
     </section>
     <section className="panel">
       <span className="eyebrow">RESULTADO MRP</span><h2>Compras y fabricación</h2>
       {mrp?<><div className={'validation '+(!mrp.feasible_within_horizon?'invalid':'')}>
         {mrp.feasible_within_horizon?'✓ Materiales y demanda final conciliados en el horizonte':
           'Atención: '+mrp.release_before_horizon.length+' órdenes fuera de horizonte y '+mrp.end_item_shortages.length+' faltantes de producto terminado'}
        </div>
        <div className="scroll"><table><thead><tr><th>SKU · orden de liberación</th>{minutesAvailable.map((_,i)=><th key={i}>P{i+1}</th>)}</tr></thead><tbody>
          {mrp.items.filter(x=>x.kind==='component').map(item=><tr key={item.sku}>
            <td>{item.sku}</td>{item.planned_order_releases.map((v,i)=><td key={i}>{v}</td>)}</tr>)}
        </tbody></table></div>
        {mrp.release_before_horizon.length>0&&<p className="planning-explain">Se requiere adelantar o reprogramar las órdenes fuera del horizonte; el MRP no considera esas entregas garantizadas.</p>}
       </>:<div className="planning-empty">Ejecuta MRP después de obtener un MPS factible.</div>}
     </section>
   </div>
   <div className="note">APP y MPS resuelven modelos MILP independientes con HiGHS. MRP realiza necesidades netas y desfase temporal de órdenes; no optimiza proveedores ni precios. La conexión es jerárquica y puede requerir reconciliación de capacidad. Estos planes todavía no generan automáticamente eventos en la fábrica 3D.</div>
 </div>
}
