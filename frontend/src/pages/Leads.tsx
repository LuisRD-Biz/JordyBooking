import React, {useState} from 'react';
import {AlertCircle, Plus, Sparkles} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {ContactPicker, contactPayload} from '../booking/forms';
import {capitalize, fmt, toUtc} from '../lib/dates';
import {Badge, Editor, Empty, Modal, money} from '../shared';
import type {Row} from '../shared';
import {Chips, ListError, Pager, RowCard, SearchBox, usePage} from '../ui/lists';

const STAGES: Record<string, string> = {new: 'Nuevo', contacted: 'Contactado', quoted: 'Cotizado', pending_booking: 'En solicitud', won: 'Contratado', lost: 'No concretado'};
const TONE: Record<string, string> = {new: 'pending', contacted: 'pending', quoted: 'scheduled', pending_booking: 'scheduled', won: 'confirmed', lost: 'cancelled'};
const CHANNELS = ['WhatsApp', 'Instagram', 'Teléfono', 'Recomendación', 'Otro'];
const OPEN = (status: string) => !['won', 'lost', 'pending_booking'].includes(status);

/** Sales opportunities: interest that does not reserve a date or hold resources. */
export function Leads() {
  const {zone, metrics, revision} = useStudio();
  const [stage, setStage] = useState(''), [text, setText] = useState(''), [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false), [selected, setSelected] = useState<number | null>(null);
  const {result, error, busy, loaded, retry} = usePage('/api/search/leads', {status: stage, q: text, page, order: 'desc'}, revision);
  const options = [{value: '', label: 'Todas'}, ...Object.entries(STAGES).map(([value, label]) => ({value, label}))];
  return <section className="panel list">
    <div className="list-controls">
      <SearchBox label="Buscar oportunidad" placeholder="Cliente o servicio…" onSearch={value => { setText(value); setPage(1); }}/>
      <button className="primary" onClick={() => setCreating(true)}><Plus size={16}/>Nueva</button>
      <Chips label="Etapa" options={options} value={stage} onChange={value => { setStage(value); setPage(1); }}/>
    </div>
    <p className="muted pad-x">{metrics.leads || 0} oportunidades · {metrics.quotes || 0} cotizaciones · {metrics.won || 0} contratadas</p>
    <ListError what="las oportunidades" error={error} retry={retry}/>
    {result.items.length > 0 && <ul className="rows" aria-busy={busy}>
      {result.items.map(lead => <RowCard key={lead.id} title={lead.customer_name} subtitle={`${lead.service} · ${lead.channel}`}
        meta={lead.requested_date ? <>Fecha deseada<small>{capitalize(fmt(lead.requested_date, zone, 'EEE d MMM yyyy'))}</small></> : 'Sin fecha definida'}
        badge={<Badge status={TONE[lead.status]} label={STAGES[lead.status]}/>} onClick={() => setSelected(lead.id)}/>)}
    </ul>}
    {!result.items.length && (loaded ? <Empty icon={Sparkles} title="Sin oportunidades en esta etapa" text="Registra aquí a quien pregunta por una fecha, aunque todavía no reserve."/> : !error && <p className="muted pad">Buscando…</p>)}
    <Pager result={result} onPage={setPage}/>
    {creating && <NewLead onClose={() => setCreating(false)}/>}
    {selected && <LeadDetail id={selected} onClose={() => setSelected(null)}/>}
  </section>;
}

function NewLead({onClose}: {onClose: () => void}) {
  const {zone, changed} = useStudio();
  const [contact, setContact] = useState<Row>({new_customer: {name: '', phone: '', email: ''}});
  return <Editor title="Nueva oportunidad" subtitle="El interés no aparta la fecha." onClose={onClose}
    fields={[
      {name: 'service', label: 'Servicio de interés'},
      {name: 'channel', label: 'Canal de contacto', type: 'select', options: CHANNELS.map(value => ({value, label: value}))},
      {name: 'requested_date', label: 'Fecha deseada', type: 'datetime-local', required: false},
      {name: 'notes', label: 'Necesidades y seguimiento', type: 'textarea', required: false},
    ]}
    onSave={async data => {
      await api('/api/leads', 'POST', {...contactPayload(contact), ...data, requested_date: data.requested_date ? toUtc(String(data.requested_date), zone) : null});
      onClose();
      changed('Oportunidad registrada');
    }}>
    <ContactPicker value={contact} onChange={setContact}/>
  </Editor>;
}

function LeadDetail({id, onClose}: {id: number; onClose: () => void}) {
  const {zone, packages, revision, changed, open, openBooking} = useStudio();
  const [history, setHistory] = useState<Row | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false), [packageId, setPackageId] = useState('');
  const [version, setVersion] = useState(0);
  React.useEffect(() => {
    let active = true;
    api(`/api/leads/${id}/history`).then(result => { if (active) setHistory(result); }).catch(err => { if (active) setError(`No se pudo abrir la oportunidad: ${err.message}`); });
    return () => { active = false; };
  }, [id, revision, version]);
  async function act(path: string, body: Row, message: string) {
    setBusy(true); setError('');
    try { await api(path, 'POST', body); setVersion(value => value + 1); changed(message); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  const lead: Row | undefined = history?.lead;
  const reopenable = lead && ['won', 'pending_booking'].includes(lead.status) && history!.bookings.length > 0 && history!.bookings.every((b: Row) => b.status === 'cancelled');
  return <Modal side title={lead?.customer_name || 'Oportunidad'} subtitle={lead ? `${lead.service} · ${lead.channel}` : undefined} onClose={onClose}>
    <div className="sheet-body stack">
      {error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}
      {!history && !error && <p className="muted">Abriendo…</p>}
      {lead && <>
        <div className="row"><Badge status={TONE[lead.status]} label={STAGES[lead.status]}/>{lead.requested_date && <span className="tag">{capitalize(fmt(lead.requested_date, zone, 'EEE d MMM yyyy, HH:mm'))}</span>}</div>
        <p className="prewrap">{lead.notes || 'Sin observaciones.'}</p>
        <h3>Cotizaciones</h3>
        <p className="muted">Cada versión conserva el precio y las condiciones del paquete en ese momento.</p>
        {history!.quotes.map((quote: Row) => <article className="quote" key={quote.id}>
          <strong>Versión {quote.version} · {quote.snapshot.name}</strong>
          <span>{money(quote.snapshot.price, quote.snapshot.currency)} · {fmt(quote.created_at, zone, 'd MMM yyyy')}</span>
          {quote.snapshot.terms && <p className="prewrap muted">{quote.snapshot.terms}</p>}
          {OPEN(lead.status) && <button className="secondary" onClick={() => open('booking', {customer_id: lead.customer_id, customer_name: lead.customer_name, package_id: quote.package_id, quote_id: quote.id, quote_snapshot: quote.snapshot, starts_at: lead.requested_date})}>Crear solicitud con esta cotización</button>}
        </article>)}
        {!history!.quotes.length && <p className="muted">Aún no hay cotizaciones.</p>}
        {OPEN(lead.status) && <div className="inline-form">
          <select aria-label="Paquete a cotizar" value={packageId} onChange={event => setPackageId(event.target.value)}>
            <option value="">Elige un paquete para cotizar</option>
            {packages.map(p => <option key={p.id} value={p.id}>{p.name} · {money(p.price, p.currency)}</option>)}
          </select>
          <button className="secondary" disabled={!packageId || busy} onClick={() => act(`/api/leads/${id}/quotes`, {package_id: Number(packageId)}, 'Cotización creada')}>Cotizar</button>
        </div>}
        <h3>Reservaciones</h3>
        {history!.bookings.length ? <ul className="rows inset">{history!.bookings.map((b: Row) => <li key={b.id}>
          <button type="button" className="row-card" onClick={() => openBooking(b.id)}>
            <span className="rc-main"><strong>Reservación #{b.id}</strong><small>{capitalize(fmt(b.starts_at, zone, 'EEE d MMM yyyy, HH:mm'))}</small></span>
            <span className="rc-badge"><Badge status={b.status}/></span>
          </button>
        </li>)}</ul> : <p className="muted">Todavía no hay una solicitud de reservación.</p>}
        {history!.appointments.length > 0 && <>
          <h3>Citas</h3>
          <ul className="plain-list">{history!.appointments.map((a: Row) => <li key={a.id}><span>{capitalize(fmt(a.starts_at, zone, 'EEE d MMM, HH:mm'))} · {a.location}</span><Badge status={a.status}/></li>)}</ul>
        </>}
      </>}
    </div>
    {lead && (reopenable || ['new', 'contacted', 'quoted'].includes(lead.status)) && <footer className="modal-footer">
      {['new', 'contacted', 'quoted'].includes(lead.status) && <button className="danger-btn" disabled={busy} onClick={() => act(`/api/leads/${id}/status`, {status: 'lost'}, 'Oportunidad cerrada')}>No se concretó</button>}
      {lead.status === 'new' && <button className="primary" disabled={busy} onClick={() => act(`/api/leads/${id}/status`, {status: 'contacted'}, 'Marcada como contactada')}>Marcar contactado</button>}
      {reopenable && <button className="secondary" disabled={busy} onClick={() => act(`/api/leads/${id}/status`, {status: 'reopen'}, 'Oportunidad reabierta')}>Volver a cotizar</button>}
    </footer>}
  </Modal>;
}
