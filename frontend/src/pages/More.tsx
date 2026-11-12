import React from 'react';
import {ChevronRight, LogOut} from 'lucide-react';
import {initials, roleLabel} from '../auth';
import {useStudio} from '../app/context';
import {navigate} from '../app/router';
import {secondaryItems} from '../app/Shell';

export function More({onLogout}: {onLogout: () => void}) {
  const {user, metrics, seasonVisible} = useStudio();
  return <div className="stack">
    <section className="panel account-card">
      <span className="avatar large">{initials(user.name)}</span>
      <div><strong>{user.name}</strong><small>{user.local ? 'Acceso local' : user.email} · {roleLabel[user.role] || 'Administrador'}</small></div>
    </section>
    <nav className="panel link-list" aria-label="Más secciones">
      {secondaryItems(seasonVisible).map(item => <a key={item.name} href={`#/${item.name}`} onClick={event => { event.preventDefault(); navigate(item.name); }}>
        <item.icon size={20}/><span>{item.label}</span>
        {item.name === 'reservaciones' && metrics.pending > 0 && <b>{metrics.pending} por aprobar</b>}
        <ChevronRight size={18} aria-hidden="true"/>
      </a>)}
    </nav>
    <button className="secondary" onClick={onLogout}><LogOut size={18}/>Cerrar sesión</button>
  </div>;
}
