import {useEffect, useState} from 'react';
import {formatInTimeZone} from 'date-fns-tz';
import {api} from './api';
import {Modal} from './shared';
import type {Row} from './shared';

const labels:Record<string,string> = {
  price:'Precios y paquetes', wedding:'Boda', xv:'XV años', session:'Sesión',
  other_service:'Otro servicio', availability:'Disponibilidad', reschedule:'Posible cambio de fecha',
  deposit:'Anticipo / apartado', contract:'Contrato', payment:'Pago', agreement:'Posible acuerdo',
  appointment:'Posible cita', cancellation:'Posible cancelación', jordy_attention:'Atención de Jordy',
  date:'Fecha mencionada', explicit:'Explícito', possible:'Posible', ambiguous:'Ambiguo',
  pending:'Pendiente', reviewed:'Revisado', dismissed:'Descartado',
  statement:'Afirmación', question:'Pregunta', negated:'Negación',
  hypothetical:'Hipótesis', correction:'Corrección', inquiry:'Consulta',
  tentative:'Fecha tentativa', hold_review:'Apartado por revisar', unknown:'Sin acuerdo',
  proposed:'Propuesto', verbally_reported:'Acuerdo verbal reportado',
};
const label=(v:string)=>labels[v]||v;
function Signal({row,onReview,onOpen}:{row:Row,onReview:(r:Row,state:string)=>Promise<void>,onOpen?:(id:number)=>void}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[original,setOriginal]=useState<Row|null>(null);
  async function review(state:string){setBusy(true);setError('');try{await onReview(row,state)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  return <article className="commercial-item">
    <strong>{label(row.kind)} · {label(row.certainty)}</strong>
    <small>{label(row.context)} · {label(row.review_state)} · Mensaje #{row.message_id}{row.direction?` · ${row.direction==='incoming'?'Contacto':'Estudio'}`:''}</small>
    <p>“{row.evidence}”</p>
    {row.kind==='date'&&<p>{row.mentioned_date||'Fecha incompleta o ambigua: revisar el mensaje original.'}</p>}
    <div className="commercial-actions"><button className="text-btn" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{setOriginal(await api(`/api/messaging/conversations/${row.conversation_id}/messages/${row.message_id}`))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>Ver mensaje original</button>{onOpen&&<button className="text-btn" onClick={()=>onOpen(row.conversation_id)}>Ver conversación</button>}
      <button className="text-btn" disabled={busy||row.review_state==='reviewed'} onClick={()=>review('reviewed')}>Marcar revisado</button>
      <button className="text-btn" disabled={busy||row.review_state==='dismissed'} onClick={()=>review('dismissed')}>Descartar señal</button>
    </div>{error&&<p className="error" role="alert">{error}</p>}{original&&<Modal title="Mensaje original" subtitle={`Mensaje #${original.id} · ${original.direction==='incoming'?'Contacto':'Estudio'}`} onClose={()=>setOriginal(null)}><div className="detail-body"><p className="message-preview">{original.body||'Contenido sin transcripción'}</p><small>{original.occurred_at} · {original.status}</small></div></Modal>}
  </article>
}

export function ConversationCommercial({conversation,section}:{conversation:Row,section:string}) {
  const [data,setData]=useState<Row|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [notice,setNotice]=useState('');
  const [body,setBody]=useState(''),[source,setSource]=useState('manual'),[bookings,setBookings]=useState<Row[]>([]);
  const cid=conversation.id;
  useEffect(()=>{let active=true;setData(null);setError('');
    api(`/api/commercial/conversations/${cid}`).then(d=>{if(active)setData(d)}).catch(e=>{if(active)setError(e.message)});
    if(conversation.customer_id)api(`/api/search/bookings?customer_id=${conversation.customer_id}&page_size=100`).then(d=>{if(active)setBookings(d.items)}).catch(()=>{if(active){setBookings([]);setError('No se pudieron cargar las reservas del contacto. Vuelve a abrir la conversación.')}});
    else setBookings([]);
    return()=>{active=false}
  },[cid,conversation.customer_id]);
  async function action(fn:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await fn();setNotice('Cambios guardados. Ninguna reserva se modificó.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  async function reload(){setData(await api(`/api/commercial/conversations/${cid}`))}
  return <section className="commercial-panel"><h3>{section==='signals'?'Señales comerciales':section==='notes'?'Notas de Jordy':'Fechas y propuestas'}</h3>
    <p className="muted">Son observaciones del texto, no hechos confirmados. Revisarlas no confirma ni cambia una reserva.</p>
    <button hidden={section!=='signals'} className="secondary" disabled={busy} onClick={()=>action(async()=>setData(await api(`/api/commercial/conversations/${cid}/analyze`,'POST')))}>Analizar mensajes guardados</button>
    {error&&<p className="error" role="alert">{error}</p>}
    {notice&&<p className="success-note" role="status">{notice}</p>}
    {!data?<p>{error?'Seguimiento no disponible. Vuelve a abrir la conversación.':'Cargando seguimiento…'}</p>:<>
      <div hidden={section!=='signals'} className="commercial-signals">{data.signals.map((r:Row)=><Signal key={r.id} row={r} onReview={async(r,state)=>{await api(`/api/commercial/conversations/${cid}/signals/${r.id}`,'PATCH',{state});await reload()}}/>)}
      {!data.signals.length&&<p className="muted">Sin señales guardadas. Puedes analizar el texto de esta conversación.</p>}</div>
      <div hidden={section!=='notes'}><p className="muted">Registra lo acordado por llamada, audio o en persona. No se transcriben audios.</p>
      <form onSubmit={e=>{e.preventDefault();void action(async()=>{await api(`/api/commercial/conversations/${cid}/notes`,'POST',{body,source});setBody('');await reload()})}}>
        <label className="field"><span>Origen de la nota</span><select value={source} onChange={e=>setSource(e.target.value)}><option value="manual">Nota manual</option><option value="call">Llamada</option><option value="audio">Audio escuchado por Jordy</option><option value="in_person">En persona</option></select></label>
        <label className="field"><span>Acuerdo o contexto</span><textarea required maxLength={2000} value={body} onChange={e=>setBody(e.target.value)}/></label><button className="secondary" disabled={busy||!body.trim()}>Guardar nota</button>
      </form>
      {data.notes.map((n:Row)=><article className="commercial-item" key={n.id}><small>Nota manual de Jordy · {n.created_at.slice(0,10)}</small><p>{n.body}</p></article>)}
      </div><div hidden={section!=='plans'}><h4>Registrar fecha comercial o propuesta de cambio</h4>
        <p>Consulta y fecha tentativa no ocupan recursos. Un apartado queda por revisar hasta definir su política. Para aprobar cambios operativos, abre la reserva y usa Reprogramar.</p>
        <form onSubmit={e=>{e.preventDefault();const f=e.currentTarget;const d=Object.fromEntries(new FormData(f));void action(async()=>{await api(`/api/commercial/conversations/${cid}/plans`,'POST',{
          ...d,lead_id:d.lead_id?Number(d.lead_id):null,booking_id:d.booking_id?Number(d.booking_id):null,tentative_date:d.tentative_date||null,
          alternative_dates:String(d.alternative_dates||'').split(',').map(v=>v.trim()).filter(Boolean)
        });f.reset();await reload()})}}>
          <label className="field"><span>Tipo de propuesta</span><select name="kind"><option value="inquiry">Consulta</option><option value="tentative">Fecha tentativa</option><option value="hold_review">Apartado por revisar</option><option value="reschedule">Propuesta de reprogramación</option></select></label>
          <label className="field"><span>Fecha solicitada</span><input name="requested_date" type="date" required/></label>
          <label className="field"><span>Fecha tentativa (opcional)</span><input name="tentative_date" type="date"/></label>
          <label className="field"><span>Fechas alternativas (AAAA-MM-DD, separadas por comas)</span><input name="alternative_dates"/></label>
          <label className="field"><span>Horario aproximado (opcional)</span><input name="time_note" maxLength={200} placeholder="Por acordar"/></label>
          <label className="field"><span>Estado del acuerdo</span><select name="agreement"><option value="unknown">Sin acuerdo</option><option value="proposed">Propuesto</option><option value="verbally_reported">Acuerdo verbal reportado</option></select></label>
          <label className="field"><span>Oportunidad del contacto</span><select name="lead_id"><option value="">Sin vincular</option>{conversation.leads.map((l:Row)=><option key={l.id} value={l.id}>#{l.id} · {l.service}</option>)}</select></label>
          <label className="field"><span>Reserva del contacto (obligatoria para reprogramación)</span><select name="booking_id"><option value="">Sin reserva</option>{bookings.filter(b=>b.customer_id===conversation.customer_id).map(b=><option key={b.id} value={b.id}>#{b.id} · {b.starts_at?.slice(0,10)} · {b.status}</option>)}</select></label>
          <label className="field"><span>Notas de la propuesta</span><textarea name="notes" maxLength={2000}/></label><button className="secondary" disabled={busy}>Guardar propuesta sin ocupar recursos</button>
        </form>
      {data.plans.map((p:Row)=><article className="commercial-item" key={p.id}><Plan row={p}/><button className="text-btn" disabled={busy||p.review_state!=='pending'} onClick={()=>action(async()=>{await api(`/api/commercial/conversations/${cid}/plans/${p.id}`,'PATCH',{state:'reviewed'});await reload()})}>Marcar revisada (sin aprobar reserva)</button></article>)}
      </div>
    </>}
  </section>
}

function Plan({row}:{row:Row}) {return <><strong>{label(row.kind)} · {row.requested_date}</strong><p>{row.time_note||'Horario por acordar'} · {label(row.agreement)} · {label(row.review_state)}</p>{row.tentative_date&&<p>Tentativa: {row.tentative_date}</p>}{row.alternative_dates.length>0&&<p>Alternativas: {row.alternative_dates.join(', ')}</p>}<p>{row.notes}</p><small>Sin ocupación de recursos{row.booking_id?` · Propuesta vinculada a reserva #${row.booking_id}; su horario operativo no cambia`:''}</small></>}

export function CommercialAgenda({day,onOpen}:{day?:string,onOpen:(id:number)=>void}) {
  const [rows,setRows]=useState<Row[]|null>(null),[error,setError]=useState(''),[offset,setOffset]=useState(0);
  useEffect(()=>{setOffset(0)},[day]);
  useEffect(()=>{let active=true;setRows(null);setError('');api(`/api/commercial/plans?offset=${offset}${day?`&day=${day}`:''}`).then(d=>{if(active)setRows(d)}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[day,offset]);
  return <section className="panel commercial-panel"><h2>Fechas comerciales · sin bloqueo</h2><p className="muted">Consultas, tentativas y cambios propuestos. Las reservas confirmadas se muestran en la agenda operativa.</p>{error&&<p className="error">{error}</p>}{!rows?<p>Cargando propuestas…</p>:!rows.length?<p>No hay propuestas{day?' para este día':''}.</p>:rows.map(r=><article className="commercial-item" key={r.id}><Plan row={r}/><button className="text-btn" onClick={()=>onOpen(r.conversation_id)}>Abrir conversación</button></article>)}<button className="text-btn" disabled={!offset} onClick={()=>setOffset(v=>v-200)}>Anterior</button><button className="text-btn" disabled={!rows||rows.length<200} onClick={()=>setOffset(v=>v+200)}>Siguiente</button></section>
}

export function DailySummary({zone,onOpen}:{zone:string,onOpen:(id:number)=>void}) {
  const [day,setDay]=useState(()=>formatInTimeZone(new Date(),zone,'yyyy-MM-dd'));
  const [report,setReport]=useState<Row|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [schedule,setSchedule]=useState<Row>({local_time:'',start_day:''}),[notice,setNotice]=useState('');
  useEffect(()=>{let active=true;setLoading(true);setReport(null);setError('');api(`/api/commercial/summaries/${day}`).then(d=>{if(active)setReport(d)}).catch(e=>{if(active)setError(e.message)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[day]);
  useEffect(()=>{api('/api/commercial/schedule').then(d=>setSchedule({...d,local_time:d.local_time?.slice(0,5)||'',start_day:d.start_day||''})).catch(e=>setError(e.message))},[]);
  async function regenerate(){setBusy(true);setError('');try{setReport(await api(`/api/commercial/summaries/${day}`,'POST'))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  const c=report?.content;
  return <>
    <section className="panel commercial-panel"><h2>Resumen diario</h2><p>Lo detectado en mensajes, lo registrado y lo aprobado se muestran por separado. Hoy es un resumen parcial.</p>
      <div className="commercial-actions"><label className="field"><span>Fecha · {zone}</span><input type="date" required value={day} max={formatInTimeZone(new Date(),zone,'yyyy-MM-dd')} onChange={e=>{if(e.target.value)setDay(e.target.value)}} disabled={busy}/></label><button className="primary" disabled={busy||loading} onClick={regenerate}>{busy?'Generando…':'Generar / actualizar resumen'}</button></div>
      {error&&<p className="error" role="alert">{error}</p>}
      {loading?<p>Cargando resumen…</p>:!c?<p>No hay resumen guardado para este día. Puedes generarlo con los mensajes almacenados.</p>:<>
        <small>Guardado: {formatInTimeZone(new Date(report!.generated_at),zone,'dd/MM/yyyy HH:mm')}. Regenerar actualiza el contenido y conserva las revisiones.</small>
        <div className="crm-metrics"><span>{c.first_contacts} contactos nuevos</span><span>{c.returning_contacts} retomaron contacto</span><span>{c.pending_decisions} señales por revisar</span></div>
        <h3>Detectado en conversaciones</h3><p>Las cifras por servicio y tema cuentan menciones entrantes, excluyendo negaciones y señales descartadas.</p>
        <div className="chips">{Object.entries({...c.services,...c.questions}).map(([k,v])=><span key={k}>{label(k)}: {String(v)}</span>)}</div>
        <div className="commercial-signals">{c.signals.map((s:Row)=><Signal row={s} key={s.id} onOpen={onOpen} onReview={async(r,state)=>{await api(`/api/commercial/conversations/${r.conversation_id}/signals/${r.id}`,'PATCH',{state});setReport(await api(`/api/commercial/summaries/${day}`,'POST'))}}/>)}</div>
        {!c.signals.length&&<p>Sin señales detectadas.</p>}
        <h3>Conversaciones y seguimiento pendiente</h3><p>{c.unanswered_note}</p>
        {c.conversations.map((v:Row)=><article className="commercial-item" key={v.id}><strong>{v.name}</strong><p>{v.first_contact?'Primer contacto':v.returning?'Volvió a escribir':'Actividad saliente'}{v.awaiting_reply_at_close?' · Sin respuesta del estudio al cierre':''}</p><button className="text-btn" onClick={()=>onOpen(v.id)}>Ver conversación</button></article>)}
        <h3>Registrado realmente en CRM y agenda</h3>
        {!c.registered_operations.length&&<p>Sin cambios operativos registrados este día. Una fecha mencionada no implica una reprogramación aprobada.</p>}
        {c.registered_operations.map((o:Row)=><p key={o.id}>{o.action} · Registro #{o.entity_id} · {formatInTimeZone(new Date(o.created_at),zone,'HH:mm')}</p>)}
        <h3>Confirmado por Jordy en el sistema</h3>{c.jordy_confirmed.length?c.jordy_confirmed.map((o:Row)=><p key={o.id}>{o.action==='booking.confirmed'?'Reserva confirmada':'Reprogramación registrada'} · Reserva #{o.entity_id}</p>):<p>No hay confirmaciones ni reprogramaciones registradas por Jordy este día.</p>}
        <h3>Notas manuales y propuestas comerciales</h3>{c.manual_notes.map((n:Row)=><article className="commercial-item" key={n.id}><p>{n.body}</p><button className="text-btn" onClick={()=>onOpen(n.conversation_id)}>Ver conversación</button></article>)}
        {c.commercial_plans.map((p:Row)=><article className="commercial-item" key={p.id}><Plan row={p}/><button className="text-btn" onClick={()=>onOpen(p.conversation_id)}>Ver conversación</button></article>)}
      </>}
    </section>
    <section className="panel commercial-panel"><h2>Ejecución nocturna</h2><p>Elige una hora local para resumir el día anterior. Si la computadora está apagada, se recupera lo pendiente al abrir el panel, un día por minuto. Dejar la hora vacía desactiva la ejecución automática.</p>
      <form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');setNotice('');try{await api('/api/commercial/schedule','PUT',{local_time:schedule.local_time||null,start_day:schedule.start_day});setNotice('Horario guardado. No se enviarán mensajes.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}><label className="field"><span>Hora local · {zone}</span><input type="time" value={schedule.local_time} onChange={e=>setSchedule({...schedule,local_time:e.target.value})}/></label><label className="field"><span>Primer día a recuperar</span><input type="date" required value={schedule.start_day} onChange={e=>setSchedule({...schedule,start_day:e.target.value})}/></label><button className="secondary" disabled={busy}>Guardar horario</button></form>
      {schedule.last_day&&<p>Último día recuperado: {schedule.last_day}</p>}{schedule.last_error&&<p className="error">Resumen pendiente de recuperación ({schedule.last_error}).</p>}{notice&&<p role="status">{notice}</p>}
    </section>
  </>
}
