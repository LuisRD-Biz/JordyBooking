import React, {useEffect, useRef, useState} from 'react';
import {AlertCircle, CalendarDays, Plus, X} from 'lucide-react';
import {useBackClose} from './app/router';

export type Row = Record<string, any>;
export type Field = {name: string; label: string; type?: string; value?: any; required?: boolean; options?: {value: any; label: string}[]; hint?: string; min?: number | string; step?: string};

export const labels: Record<string, string> = {
  pending_approval: 'Por aprobar', confirmed: 'Confirmada', cancelled: 'Cancelada', completed: 'Completada',
  scheduled: 'Agendada', pending: 'Pendiente', failed: 'Con error', simulated: 'Simulada',
};
export const roles: Record<string, string> = {
  photographer: 'Fotografía', videographer: 'Video', assistant: 'Asistencia', second_camera: 'Segunda cámara',
  drone: 'Dron', studio_set: 'Set fotográfico',
};
export const money = (amount: any, currency = 'MXN') =>
  new Intl.NumberFormat('es-MX', {style: 'currency', currency, maximumFractionDigits: 0}).format(Number(amount));
export const initial = (name: string) => name.split(' ').map(part => part[0]).slice(0, 2).join('').toUpperCase();

export function Badge({status, label}: {status: string; label?: string}) {
  return <span className={`badge ${status}`}><i/>{label || labels[status] || status}</span>;
}

export function Empty({icon: Icon = CalendarDays, title, text, action}: {icon?: any; title: string; text: string; action?: React.ReactNode}) {
  return <div className="empty"><div className="empty-icon"><Icon size={26}/></div><h3>{title}</h3><p>{text}</p>{action}</div>;
}

export function FieldInput({field}: {field: Field}) {
  const required = field.required !== false;
  return <label className="field">
    <span>{field.label}{required && <b aria-hidden="true"> *</b>}</span>
    {field.type === 'select'
      ? <select name={field.name} defaultValue={field.value ?? ''} required={required}>
          <option value="">Selecciona una opción</option>
          {field.options?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      : field.type === 'textarea'
        ? <textarea name={field.name} defaultValue={field.value} required={required} rows={3}/>
        : <input name={field.name} type={field.type || 'text'} defaultValue={field.value} required={required} min={field.min} step={field.step} autoComplete="off"/>}
    {field.hint && <small>{field.hint}</small>}
  </label>;
}

/**
 * Modal dialog: a bottom sheet on phones, a centred card (or a side panel with `side`) on
 * larger screens. It owns a history entry, so the phone's "back" closes it.
 */
export function Modal({title, subtitle, children, onClose, side = false, header, routed = false}: {title: string; subtitle?: string; children: React.ReactNode; onClose: () => void; side?: boolean; header?: React.ReactNode; routed?: boolean}) {
  const ref = useRef<HTMLDialogElement>(null);
  useBackClose(onClose, !routed);
  useEffect(() => {
    const element = ref.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return <dialog ref={ref} className={side ? 'side' : undefined} aria-label={title}
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === ref.current) onClose(); }}>
    <div className="modal-head">
      <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
      <button className="icon-btn" aria-label="Cerrar" onClick={onClose}><X size={22}/></button>
    </div>
    {header}
    {children}
  </dialog>;
}

export function Editor({title, subtitle, fields, onSave, onClose, children, saveLabel = 'Guardar', danger = false, tone = 'confirm'}: {title: string; subtitle?: string; fields: Field[]; onSave: (data: Row) => Promise<void> | void; onClose: () => void; children?: React.ReactNode; saveLabel?: string; danger?: boolean; tone?: 'confirm' | 'primary'}) {
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true); setError('');
    try { await onSave(data); } catch (err) { setError((err as Error).message); setBusy(false); return; }
    setBusy(false);
  }
  return <Modal title={title} subtitle={subtitle} onClose={onClose}>
    <form onSubmit={submit}>
      <div className="form-fields">
        {fields.map(field => <FieldInput key={field.name} field={field}/>)}
        {children}
        {error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}
      </div>
      <footer className="modal-footer">
        {/* Leaving a form is not destructive: outlined. The filled red is for what cannot be undone. */}
        <button type="button" className={danger ? 'secondary' : 'danger-btn'} onClick={onClose} disabled={busy}>{danger ? 'No, volver' : 'Cancelar'}</button>
        <button className={danger ? 'danger-btn solid' : tone} disabled={busy}>{busy ? 'Guardando…' : saveLabel}</button>
      </footer>
    </form>
  </Modal>;
}

export function PackageEditor({existing, resources, onSave, onClose}: {existing?: Row; resources: Row[]; onSave: (data: Row) => Promise<void>; onClose: () => void}) {
  const [reqs, setReqs] = useState<{capability: string; quantity: number}[]>(existing
    ? Object.entries(existing.requirements).map(([capability, quantity]) => ({capability, quantity: Number(quantity)}))
    : [{capability: 'photographer', quantity: 1}]);
  const capabilities = Array.from(new Set([...Object.keys(roles), ...resources.flatMap(r => r.capabilities as string[])]));
  const update = (index: number, change: Partial<{capability: string; quantity: number}>) =>
    setReqs(reqs.map((req, i) => (i === index ? {...req, ...change} : req)));
  return <Editor title={existing ? 'Editar paquete' : 'Nuevo paquete'} subtitle="Lo que ofreces y los recursos que necesita." onClose={onClose}
    onSave={data => onSave({...data, duration_minutes: Number(data.duration_minutes), buffer_minutes: Number(data.buffer_minutes), preparation_minutes: Number(data.preparation_minutes), requirements: reqs})}
    fields={[
      {name: 'name', label: 'Nombre del paquete', value: existing?.name},
      {name: 'kind', label: 'Tipo de servicio', type: 'select', value: existing?.kind || 'session', options: [{value: 'session', label: 'Sesión fotográfica'}, {value: 'event', label: 'Evento · requiere contrato'}]},
      {name: 'price', label: 'Precio', type: 'number', min: 0, step: '0.01', value: existing?.price},
      {name: 'currency', label: 'Moneda', type: 'select', value: existing?.currency || 'MXN', options: [{value: 'MXN', label: 'Pesos mexicanos (MXN)'}, {value: 'USD', label: 'Dólares (USD)'}]},
      {name: 'duration_minutes', label: 'Duración (min)', type: 'number', min: 1, value: existing?.duration_minutes || 90},
      {name: 'buffer_minutes', label: 'Margen después (min)', type: 'number', min: 0, value: existing?.buffer_minutes ?? 30},
      {name: 'preparation_minutes', label: 'Preparación antes (min)', type: 'number', min: 0, value: existing?.preparation_minutes ?? 0},
      {name: 'terms', label: 'Servicios incluidos y condiciones', type: 'textarea', required: false, value: existing?.terms},
    ]}>
    <fieldset className="group">
      <legend>Personal y equipo requerido</legend>
      <p className="muted">Una misma persona solo cubre una función a la vez.</p>
      {reqs.map((req, index) => <div className="req-row" key={index}>
        <select required aria-label={`Capacidad ${index + 1}`} value={req.capability} onChange={e => update(index, {capability: e.target.value})}>
          <option value="">Selecciona una capacidad</option>
          {capabilities.map(c => <option key={c} value={c}>{roles[c] || c.replaceAll('_', ' ')}</option>)}
        </select>
        <input type="number" aria-label={`Cantidad ${index + 1}`} min={1} max={50} required value={req.quantity} onChange={e => update(index, {quantity: Number(e.target.value)})}/>
        <button type="button" className="icon-btn" aria-label={`Quitar requisito ${index + 1}`} disabled={reqs.length === 1} onClick={() => setReqs(reqs.filter((_, i) => i !== index))}><X size={18}/></button>
      </div>)}
      <button type="button" className="text-btn" onClick={() => setReqs([...reqs, {capability: '', quantity: 1}])}><Plus size={16}/>Añadir requisito</button>
    </fieldset>
  </Editor>;
}

export function ResourceEditor({existing, resources, onSave, onClose}: {existing?: Row; resources: Row[]; onSave: (data: Row) => Promise<void>; onClose: () => void}) {
  const [selected, setSelected] = useState<string[]>(existing?.capabilities || []);
  const choices = Array.from(new Set([...Object.keys(roles), ...resources.flatMap(r => r.capabilities as string[])]));
  return <Editor title={existing ? 'Editar recurso' : 'Añadir personal o equipo'} subtitle="Registra a cada persona una sola vez, aunque tenga varias capacidades." onClose={onClose}
    fields={[
      {name: 'name', label: 'Nombre', value: existing?.name},
      {name: 'kind', label: 'Tipo', type: 'select', value: existing?.kind || 'staff', options: [{value: 'staff', label: 'Persona'}, {value: 'equipment', label: 'Equipo o set'}]},
    ]}
    onSave={data => {
      const custom = String(data.custom || '').trim().normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
      const capabilities = Array.from(new Set([...selected, ...(custom ? [custom] : [])]));
      if (!capabilities.length) throw new Error('Selecciona al menos una capacidad.');
      return onSave({name: data.name, kind: data.kind, capabilities});
    }}>
    <fieldset className="group check-grid">
      <legend>Capacidades</legend>
      {choices.map(c => <label className="check-label" key={c}>
        <input type="checkbox" checked={selected.includes(c)} onChange={e => setSelected(e.target.checked ? [...selected, c] : selected.filter(x => x !== c))}/>
        {roles[c] || c.replaceAll('_', ' ')}
      </label>)}
    </fieldset>
    <FieldInput field={{name: 'custom', label: 'Otra capacidad (opcional)', required: false, hint: 'Por ejemplo: iluminación, maquillaje o set infantil.'}}/>
  </Editor>;
}
