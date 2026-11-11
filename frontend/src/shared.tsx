import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {formatInTimeZone, fromZonedTime} from 'date-fns-tz';
import {es} from 'date-fns/locale';
import {Aperture, LayoutDashboard, CalendarDays, ClipboardList, Users, Package, Camera, Snowflake, Activity, Settings, Plus, ArrowUpRight, ArrowRight, ChevronLeft, ChevronRight, Search, X, Check, Clock3, MapPin, ShieldCheck, LogOut, Menu, RefreshCw, CircleHelp, Ban, CalendarCheck, CheckCircle2, AlertCircle, Pencil, FileCheck2} from 'lucide-react';
import {api, all} from './api';
type Row = Record<string, any>;
type Store = {bookings: Row[], customers: Row[], packages: Row[], resources: Row[], blocks: Row[], operations: Row[], audit: Row[]};
type Field = {name: string, label: string, type?: string, value?: any, required?: boolean, options?: {value: any, label: string}[], hint?: string, min?: number, step?: string};
const empty: Store = {bookings: [], customers: [], packages: [], resources: [], blocks: [], operations: [], audit: []};
const navigation = [
  ['overview','Vista general',LayoutDashboard], ['calendar','Agenda',CalendarDays], ['bookings','Reservaciones',ClipboardList],
  ['crm','Oportunidades',ArrowUpRight], ['appointments','Citas y firmas',FileCheck2], ['customers','Clientes',Users], ['packages','Paquetes',Package], ['resources','Equipo y personal',Camera],
  ['christmas','Temporada navideña',Snowflake], ['activity','Actividad',Activity],
] as const;
const labels: Record<string,string> = {pending_approval:'Por aprobar', confirmed:'Confirmada', cancelled:'Cancelada', completed:'Completada', pending:'Pendiente', failed:'Con error', simulated:'Simulada'};
const roles: Record<string,string> = {photographer:'Fotografía', videographer:'Video', assistant:'Asistencia', second_camera:'Segunda cámara', drone:'Dron', studio_set:'Set fotográfico'};
const money = (n: any, currency='MXN') => new Intl.NumberFormat('es-MX', {style:'currency',currency,maximumFractionDigits:0}).format(Number(n));
const initial = (name: string) => name.split(' ').map(x=>x[0]).slice(0,2).join('').toUpperCase();
function Badge({status}: {status: string}) {return <span className={`badge ${status}`}><i/>{labels[status] || status}</span>}
function Empty({icon: Icon=CalendarDays, title, text, action}: {icon?: any,title: string,text: string,action?: React.ReactNode}) {return <div className="empty"><div className="empty-icon"><Icon size={27}/></div><h3>{title}</h3><p>{text}</p>{action}</div>}
function FieldInput({field}: {field: Field}) {return <label className="field"><span>{field.label}{field.required !== false && <b> *</b>}</span>{field.type==='select' ? <select name={field.name} defaultValue={field.value ?? ''} required={field.required !== false}><option value="">Selecciona una opción</option>{field.options?.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select> : field.type==='textarea' ? <textarea name={field.name} defaultValue={field.value} required={field.required !== false} rows={3}/> : <input name={field.name} type={field.type || 'text'} defaultValue={field.value} required={field.required !== false} min={field.min} step={field.step} autoComplete="off"/>}{field.hint && <small>{field.hint}</small>}</label>}
function Modal({title,subtitle,children,onClose}: {title:string,subtitle?:string,children:React.ReactNode,onClose:()=>void}) {
  const ref=useRef<HTMLDialogElement>(null);
  useEffect(()=>{ref.current?.showModal(); const el=ref.current; return ()=>el?.close()},[]);
  return <dialog ref={ref} onCancel={onClose} onClick={e=>{if(e.target===ref.current) onClose()}}><div className="modal-head"><div><span className="eyebrow">JORDY STUDIO</span><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button className="icon-btn" aria-label="Cerrar" onClick={onClose}><X size={20}/></button></div>{children}</dialog>
}
function Editor({title,subtitle,fields,onSave,onClose,children,saveLabel='Guardar'}: {title:string,subtitle?:string,fields:Field[],onSave:(data:Row)=>Promise<void>,onClose:()=>void,children?:React.ReactNode,saveLabel?:string}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  return <Modal title={title} subtitle={subtitle} onClose={onClose}><form onSubmit={async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));setBusy(true);setError('');try{await onSave(data)}catch(err){setError((err as Error).message)}finally{setBusy(false)}}}><div className="form-fields">{fields.map(field=><FieldInput key={field.name} field={field}/>)}{children}{error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}</div><footer className="modal-footer"><button type="button" className="secondary" onClick={onClose} disabled={busy}>Cancelar</button><button className="primary" disabled={busy}>{busy?'Guardando…':saveLabel}<ArrowRight size={16}/></button></footer></form></Modal>
}
function PackageEditor({existing,resources,onSave,onClose}: {existing?:Row,resources:Row[],onSave:(data:Row)=>Promise<void>,onClose:()=>void}) {
  const [reqs,setReqs]=useState<{capability:string,quantity:number}[]>(existing?Object.entries(existing.requirements).map(([capability,quantity])=>({capability,quantity:Number(quantity)})):[{capability:'photographer',quantity:1}]);
  return <Editor title={existing?'Editar paquete':'Nuevo paquete'} subtitle="Define lo que ofreces y los recursos necesarios para realizarlo." onClose={onClose} onSave={d=>onSave({...d,price:d.price,duration_minutes:Number(d.duration_minutes),buffer_minutes:Number(d.buffer_minutes),preparation_minutes:Number(d.preparation_minutes),requirements:reqs})} fields={[
    {name:'name',label:'Nombre del paquete',value:existing?.name}, {name:'kind',label:'Tipo de servicio',type:'select',value:existing?.kind || 'session',options:[{value:'session',label:'Sesión fotográfica'},{value:'event',label:'Evento · requiere contrato'}]},
    {name:'price',label:'Precio',type:'number',min:0,step:'0.01',value:existing?.price}, {name:'currency',label:'Moneda',type:'select',value:existing?.currency || 'MXN',options:[{value:'MXN',label:'Pesos mexicanos (MXN)'},{value:'USD',label:'Dólares (USD)'}]},
    {name:'duration_minutes',label:'Duración de la sesión / evento (min)',type:'number',min:1,value:existing?.duration_minutes || 90}, {name:'buffer_minutes',label:'Margen después (min)',type:'number',min:0,value:existing?.buffer_minutes ?? 30},
    {name:'preparation_minutes',label:'Preparación antes (min)',type:'number',min:0,value:existing?.preparation_minutes ?? 0}, {name:'terms',label:'Servicios incluidos y condiciones',type:'textarea',required:false,value:existing?.terms},
  ]}><div className="requirements"><h3>Personal y equipo requerido</h3><p>Una misma persona solo puede cubrir una función a la vez.</p>{reqs.map((r,i)=><div className="req-row" key={i}><label><span className="sr-only">Capacidad {i+1}</span><select required aria-label={`Capacidad ${i+1}`} value={r.capability} onChange={e=>setReqs(reqs.map((v,j)=>j===i?{...v,capability:e.target.value}:v))}><option value="">Selecciona una capacidad</option>{Array.from(new Set([...Object.keys(roles),...resources.flatMap(r=>r.capabilities)])).map((c:string)=><option key={c} value={c}>{roles[c]||c.replaceAll("_"," ")}</option>)}</select></label><input type="number" aria-label={`Cantidad ${i+1}`} min={1} max={50} required value={r.quantity} onChange={e=>setReqs(reqs.map((v,j)=>j===i?{...v,quantity:Number(e.target.value)}:v))}/><button type="button" className="icon-btn" aria-label={`Quitar requisito ${i+1}`} disabled={reqs.length===1} onClick={()=>setReqs(reqs.filter((_,j)=>i!==j))}><X size={16}/></button></div>)}<datalist id="capabilities">{Object.entries(roles).map(([v,l])=><option key={v} value={v}>{l}</option>)}</datalist><button type="button" className="text-btn" onClick={()=>setReqs([...reqs,{capability:'',quantity:1}])}><Plus size={14}/>Añadir requisito</button></div></Editor>
}

function ResourceEditor({existing,resources,onSave,onClose}: {existing?:Row,resources:Row[],onSave:(d:Row)=>Promise<void>,onClose:()=>void}) {
 const [selected,setSelected]=useState<string[]>(existing?.capabilities||[]);
 const choices=Array.from(new Set([...Object.keys(roles),...resources.flatMap(r=>r.capabilities)]));
 return <Editor title={existing?'Editar recurso':'Añadir personal o equipo'} subtitle="Registra a cada persona una sola vez, aunque tenga varias capacidades." onClose={onClose} fields={[{name:'name',label:'Nombre',value:existing?.name},{name:'kind',label:'Tipo',type:'select',value:existing?.kind||'staff',options:[{value:'staff',label:'Persona'},{value:'equipment',label:'Equipo o set'}]}]} onSave={d=>{const custom=String(d.custom||'').trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'');const capabilities=Array.from(new Set([...selected,...(custom?[custom]:[])]));if(!capabilities.length)throw new Error('Selecciona al menos una capacidad.');return onSave({name:d.name,kind:d.kind,capabilities})}}><div className="capability-options"><h3>Capacidades</h3>{choices.map(c=><label key={c}><input type="checkbox" checked={selected.includes(c)} onChange={e=>setSelected(e.target.checked?[...selected,c]:selected.filter(x=>x!==c))}/>{roles[c]||c.replaceAll('_',' ')}</label>)}</div><FieldInput field={{name:'custom',label:'Otra capacidad (opcional)',required:false,hint:'Por ejemplo: iluminación, maquillaje o set infantil.'}}/></Editor>
}


export {navigation,empty,labels,roles,money,initial,Badge,Empty,FieldInput,Modal,Editor,PackageEditor,ResourceEditor};
export type {Row,Store,Field};
