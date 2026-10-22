import type { Plant, Production, LayoutAnalysis, OptimizeResult, SimResult } from './types'
const base=(import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/,'')
async function post<T>(path:string,payload:unknown):Promise<T>{
 const res=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
 if(!res.ok){const err=await res.json().catch(()=>({detail:'Error de comunicación'}))
   throw new Error(typeof err.detail==='string'?err.detail:JSON.stringify(err.detail))}
 return res.json() as Promise<T>
}
export const analyzePlant=(plant:Plant)=>post<LayoutAnalysis>('/api/slp/analyze',plant)
export const optimizePlant=(plant:Plant)=>post<OptimizeResult>('/api/slp/optimize',{plant,steps:[4,2,1]})
export const simulatePlant=(prod:Production)=>post<SimResult>('/api/production/simulate',prod)

export const validateScenario=(data:unknown)=>post<import('./ScenarioToolbar').ScenarioDocument>('/api/scenarios/validate',data)

export const compareLayouts=(as_is:Plant,to_be:Plant)=>post<import('./types').LayoutComparison>('/api/slp/compare',{as_is,to_be})
export const corelapOrder=(plant:Plant)=>post<import('./types').CorelapOrder>('/api/slp/corelap/order',plant)
export const annealPlant=(plant:Plant,params:{iterations:number;grid_step:number;temperature:number;cooling:number;seed:number})=>
 post<import('./types').AnnealResult>('/api/slp/anneal',{plant,...params})
