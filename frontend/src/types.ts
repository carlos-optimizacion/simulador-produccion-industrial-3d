export type Rating = 'A'|'E'|'I'|'O'|'U'|'X'
export type Area={id:string;name:string;x:number;z:number;width:number;depth:number;color:string}
export type Flow={source:string;target:string;units_per_shift:number;cost_per_unit_meter:number}
export type Relationship={source:string;target:string;rating:Rating;reason:string}
export type Plant={name:string;width:number;depth:number;clearance:number;areas:Area[];flows:Flow[];relationships:Relationship[]}
export type Station={id:string;name:string;area_id:string;machines:number}
export type Operation={station_id:string;minutes_per_unit:number}
export type Production={plant:Plant;stations:Station[];operations:Operation[];quantity:number;travel_speed_m_min:number}
export type LayoutAnalysis={valid:boolean;violations:{type:string;areas:string[]}[];material_handling_cost_per_shift:number;material_handling_distance_m_units:number;legs:{source:string;target:string;distance_m:number;units_per_shift:number;cost_per_unit_meter:number;cost_per_shift:number}[];relationships:{source:string;target:string;rating:Rating;reason:string;distance_m:number;preference_weight:number}[];distance_method:string;rel_note:string}
export type SimEvent={machine_index?:number;t:number;type:'move'|'queue'|'start'|'finish'|'complete';job:number;station?:string;duration?:number;at?:[number,number];from?:[number,number];to?:[number,number]}
export type SimResult={engine:string;units_completed:number;makespan_min:number;throughput_units_per_hour:number;avg_queue_wait_min:number;stations:{id:string;machines:number;utilization_pct:number}[];events:SimEvent[]}
export type OptimizeResult={plant:Plant;before_cost:number;after_cost:number;saving_pct:number;evaluated_candidates:number;accepted_moves:number;algorithm:string;analysis:LayoutAnalysis}

export type CorelapOrder={method:string;weights:Record<string,number>;priority:{rank:number;area_id:string;area_name:string;tcr:number;center_xy_m:[number,number]}[]}
export type LayoutComparison={cost_before:number;cost_after:number;saving_per_shift:number;saving_pct:number;material_handling_weighted_distance_before:number;material_handling_weighted_distance_after:number;method:string;currency:string;flows:{source:string;target:string;as_is_distance_m:number;to_be_distance_m:number;as_is_cost_per_shift:number;to_be_cost_per_shift:number;saving_per_shift:number}[];relocations:{area_id:string;name:string;from_xy_m:[number,number];to_xy_m:[number,number];displacement_m:number}[]}
export type AnnealResult={plant:Plant;before_cost:number;after_cost:number;saving_pct:number;algorithm:string;valid_candidates:number;considered_candidates:number;accepted_uphill:number;parameters:{seed:number;iterations:number;grid_step:number;temperature:number;cooling:number};history:{iteration:number;best_cost:number;current_cost:number;temperature:number}[];comparison:LayoutComparison}
