import React from 'react';
import {Ban, CalendarCheck, Camera, Clock3, Package, Pencil, Plus, Users} from 'lucide-react';
import {useStudio} from '../app/context';
import {Empty, initial, money, roles} from '../shared';

export function Packages() {
  const {packages, open} = useStudio();
  return <div className="stack">
    <div className="page-actions">
      <p className="muted">{packages.length} {packages.length === 1 ? 'paquete' : 'paquetes'}. Las reservaciones conservan el precio y las condiciones con que se ofrecieron.</p>
      <button className="primary" onClick={() => open('package')}><Plus size={18}/>Nuevo paquete</button>
    </div>
    {packages.length ? <div className="card-grid">{packages.map(p => <article className="panel card" key={p.id}>
      <header><span className="tag">{p.kind === 'event' ? 'Evento' : 'Sesión'}</span></header>
      <h2>{p.name}</h2>
      <p className="price">{money(p.price, p.currency)} <small>{p.currency}</small></p>
      <p className="muted prewrap">{p.terms || 'Sin condiciones adicionales registradas.'}</p>
      <ul className="facts">
        <li><Clock3 size={16}/>{p.duration_minutes} min de servicio</li>
        <li><CalendarCheck size={16}/>{p.buffer_minutes} min de margen posterior</li>
      </ul>
      <div className="chips">{Object.entries(p.requirements).map(([role, quantity]) => <span key={role}>{String(quantity)} × {roles[role] || role}</span>)}</div>
      <button className="secondary" onClick={() => open('package', p)}><Pencil size={16}/>Editar paquete</button>
    </article>)}</div> : <section className="panel"><Empty icon={Package} title="Aún no hay paquetes" text="Define precio, duración y personal requerido para poder registrar reservaciones." action={<button className="secondary" onClick={() => open('package')}><Plus size={16}/>Crear el primer paquete</button>}/></section>}
  </div>;
}

export function Team() {
  const {resources, open} = useStudio();
  const staff = resources.filter(r => r.kind === 'staff').length;
  return <div className="stack">
    <div className="page-actions">
      <p className="muted"><Users size={16}/> {staff} personas · <Camera size={16}/> {resources.length - staff} equipos</p>
      <button className="secondary" onClick={() => open('block')}><Ban size={16}/>Bloquear horario</button>
      <button className="primary" onClick={() => open('resource')}><Plus size={18}/>Añadir</button>
    </div>
    {resources.length ? <div className="card-grid">{resources.map(r => <article className="panel card" key={r.id}>
      <header><span className="avatar large">{r.kind === 'staff' ? initial(r.name) : <Camera size={22}/>}</span><span className="tag">{r.kind === 'staff' ? 'Persona' : 'Equipo o set'}</span></header>
      <h2>{r.name}</h2>
      <div className="chips">{r.capabilities.map((c: string) => <span key={c}>{roles[c] || c.replaceAll('_', ' ')}</span>)}</div>
      <div className="row">
        <button className="secondary" onClick={() => open('resource', r)}><Pencil size={16}/>Editar</button>
        <button className="secondary" onClick={() => open('block', {resource_id: r.id})}><Ban size={16}/>Bloquear</button>
      </div>
    </article>)}</div> : <section className="panel"><Empty icon={Camera} title="Aún no hay equipo registrado" text="Añade a cada persona con sus capacidades, y los sets o equipos compartidos." action={<button className="secondary" onClick={() => open('resource')}><Plus size={16}/>Añadir recurso</button>}/></section>}
  </div>;
}
