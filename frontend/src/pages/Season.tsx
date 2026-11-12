import React, {useState} from 'react';
import {ArrowRight, CircleHelp, Clock3} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {fmt} from '../lib/dates';
import type {Row} from '../shared';

/** Christmas campaign: six fixed two-hour slots on weekdays of October and November. */
export function Season() {
  const {packages, zone, selectedDay, open} = useStudio();
  const [day, setDay] = useState(selectedDay), [packageId, setPackageId] = useState('');
  const [slots, setSlots] = useState<Row[] | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const eligible = packages.filter(p => p.kind === 'session' && p.duration_minutes === 90 && p.buffer_minutes === 30 && p.preparation_minutes === 0);

  async function search(event: React.FormEvent) {
    event.preventDefault();
    setError(''); setBusy(true);
    try {
      setSlots((await api(`/api/availability/christmas-slots?day=${day}&package_id=${packageId}`)).slots);
    } catch (err) {
      setError(`No se pudieron consultar los horarios: ${(err as Error).message}`);
    } finally { setBusy(false); }
  }

  return <div className="stack">
    <section className="panel season-intro">
      <span className="eyebrow">Octubre y noviembre</span>
      <h2>Sesiones navideñas</h2>
      <p className="muted">Seis horarios al día, de lunes a viernes: 90 minutos de sesión y 30 de margen.</p>
    </section>
    <section className="panel pad">
      <form className="inline-form" onSubmit={search}>
        <label className="field"><span>Paquete navideño</span>
          <select required value={packageId} onChange={e => { setPackageId(e.target.value); setSlots(null); }}>
            <option value="">Selecciona un paquete</option>
            {eligible.map(p => <option value={p.id} key={p.id}>{p.name}</option>)}
          </select>
        </label>
        <label className="field"><span>Fecha</span><input type="date" required value={day} onChange={e => { setDay(e.target.value); setSlots(null); }}/></label>
        <button className="primary" disabled={busy}>{busy ? 'Consultando…' : 'Consultar horarios'}<ArrowRight size={16}/></button>
      </form>
      {!eligible.length && <p className="note">Ningún paquete cumple la plantilla navideña (sesión de 90 min, 30 de margen y sin preparación).</p>}
      {error && <div className="error" role="alert">{error}</div>}
      {slots && (slots.length ? <div className="slots">{slots.map(slot => <button key={slot.starts_at} disabled={!slot.available} onClick={() => open('booking', {package_id: Number(packageId), starts_at: slot.starts_at})}>
        <Clock3 size={18}/><strong>{fmt(slot.starts_at, zone, 'HH:mm')}</strong>
        <span>{slot.available ? 'Disponible' : 'No disponible'}</span>
        <small>Termina {fmt(slot.session_ends_at, zone, 'HH:mm')}</small>
      </button>)}</div> : <p className="note">No hay horarios navideños en esta fecha. Elige un día entre semana de octubre o noviembre.</p>)}
      <p className="note"><CircleHelp size={16}/>Una solicitud no aparta el horario hasta que la apruebes.</p>
    </section>
  </div>;
}
