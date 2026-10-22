import {useRef,useState} from 'react'
import type {Plant,Station,Operation} from './types'
import {validateScenario} from './api'

export type ScenarioDocument={
  schema_version:'indusim-3d/1'|'indusim-3d/2'
  as_is?:Plant|null
  plant:Plant
  stations:Station[]
  operations:Operation[]
  quantity:number
  travel_speed_m_min:number
}
type Props={
  document:ScenarioDocument
  onImport:(document:ScenarioDocument)=>void
  onError:(message:string)=>void
}
export default function ScenarioToolbar({document,onImport,onError}:Props){
  const fileRef=useRef<HTMLInputElement>(null)
  const [loading,setLoading]=useState(false)
  function exportScenario(){
    const blob=new Blob([JSON.stringify(document,null,2)],{type:'application/json'})
    const url=URL.createObjectURL(blob)
    const anchor=documentNode().createElement('a')
    anchor.href=url
    anchor.download='INDUSIM_3D_escenario_v1.json'
    anchor.click()
    URL.revokeObjectURL(url)
  }
  // Explicit document reference avoids collision with the scenario prop.
  function documentNode(){return window.document}
  async function importScenario(file?:File){
    if(!file)return
    setLoading(true)
    try{
      if(file.size>2_000_000)throw new Error('El archivo excede el límite de 2 MB.')
      const decoded:unknown=JSON.parse(await file.text())
      if(!decoded||typeof decoded!=='object'||Array.isArray(decoded))
        throw new Error('El archivo no contiene un escenario válido.')
      const data=await validateScenario(decoded)
      onImport(data)
    }catch(error){
      onError('Importación rechazada: '+(error instanceof Error?error.message:String(error)))
    }finally{
      setLoading(false)
      if(fileRef.current)fileRef.current.value=''
    }
  }
  return <div className="scenario-actions">
    <button className="btn secondary" type="button" onClick={exportScenario}>↓ Exportar JSON</button>
    <button className="btn secondary" type="button" disabled={loading} onClick={()=>fileRef.current?.click()}>
      {loading?'Validando…':'↑ Importar escenario'}</button>
    <input ref={fileRef} type="file" accept=".json,application/json" aria-label="Seleccionar archivo de escenario"
      hidden onChange={e=>{void importScenario(e.target.files?.[0])}}/>
  </div>
}
