import React from 'react';
import {CalendarDays, LogOut, Plus, ShieldCheck, Snowflake} from 'lucide-react';
import {PasswordChange} from '../auth';
import {useStudio} from '../app/context';

export function Settings({onLogout}: {onLogout: () => void}) {
  const {user, zone, open, seasonAlways, setSeasonAlways} = useStudio();
  return <div className="two-columns">
    <section className="panel pad stack">
      <ShieldCheck size={26} aria-hidden="true"/>
      <h2>Tu acceso</h2>
      <p className="muted">{user.local ? 'Acceso local desde esta computadora.' : `Sesión de ${user.name} (${user.email}).`}</p>
      <dl>
        <dt>Zona horaria</dt><dd>{zone}</dd>
        <dt>Sesión</dt><dd>8 horas máximo · 2 horas sin actividad</dd>
        <dt>Acceso</dt><dd>{user.local ? 'Local, en esta computadora' : 'Correo y contraseña'}</dd>
      </dl>
      {!user.local && <PasswordChange email={user.email}/>}
      <button className="secondary" onClick={onLogout}><LogOut size={16}/>Cerrar sesión</button>
    </section>
    <div className="stack">
      <section className="panel pad stack">
        <Snowflake size={26} aria-hidden="true"/>
        <h2>Temporada navideña</h2>
        <p className="muted">La sección aparece sola de septiembre a diciembre. Actívala aquí si necesitas planear antes.</p>
        <label className="check-label"><input type="checkbox" checked={seasonAlways} onChange={e => setSeasonAlways(e.target.checked)}/>Mostrar siempre la temporada navideña</label>
      </section>
      <section className="panel pad stack">
        <CalendarDays size={26} aria-hidden="true"/>
        <h2>Calendario externo</h2>
        <p className="muted">Aún no hay sincronización con iCloud u Outlook. Mientras tanto, registra los compromisos externos como bloqueos.</p>
        <button className="secondary" onClick={() => open('block')}><Plus size={16}/>Registrar bloqueo</button>
      </section>
    </div>
  </div>;
}
