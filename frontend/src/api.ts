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
