import type {Plant,Production} from './types'
export const demoPlant:Plant={
name:'Planta metalmecánica — Demostración',width:36,depth:24,clearance:0.5,
areas:[
{id:'almacen',name:'Materias primas',x:1,z:1,width:7,depth:6,color:'#60a5fa'},
{id:'corte',name:'Corte',x:12,z:2,width:7,depth:6,color:'#fb923c'},
{id:'soldadura',name:'Soldadura',x:24,z:2,width:8,depth:7,color:'#fbbf24'},
{id:'inspeccion',name:'Inspección',x:24,z:14,width:8,depth:6,color:'#4ade80'},
{id:'despacho',name:'Despacho',x:2,z:15,width:8,depth:6,color:'#c084fc'}],
flows:[
{source:'almacen',target:'corte',units_per_shift:90,cost_per_unit_meter:.22},
{source:'corte',target:'soldadura',units_per_shift:80,cost_per_unit_meter:.22},
{source:'soldadura',target:'inspeccion',units_per_shift:75,cost_per_unit_meter:.22},
{source:'inspeccion',target:'despacho',units_per_shift:70,cost_per_unit_meter:.22}],
relationships:[
{source:'almacen',target:'corte',rating:'A',reason:'Alto flujo'},
{source:'corte',target:'soldadura',rating:'E',reason:'Secuencia de proceso'},
{source:'soldadura',target:'inspeccion',rating:'I',reason:'Control final'},
{source:'soldadura',target:'despacho',rating:'X',reason:'Humos: evitar cercanía'}]}
export const demoProduction:Production={
plant:demoPlant,stations:[
{id:'corte',name:'Cortadora',area_id:'corte',machines:1},
{id:'soldadura',name:'Soldadoras',area_id:'soldadura',machines:2},
{id:'inspeccion',name:'Control de calidad',area_id:'inspeccion',machines:1}],
operations:[{station_id:'corte',minutes_per_unit:7},{station_id:'soldadura',minutes_per_unit:10},{station_id:'inspeccion',minutes_per_unit:5}],
quantity:12,travel_speed_m_min:30}
