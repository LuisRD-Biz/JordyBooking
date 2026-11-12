import React from 'react';
import {
  Activity, CalendarDays, Camera, ClipboardList, FileCheck2, LogOut, MoreHorizontal,
  Package, Plus, Settings, Snowflake, Sparkles, Users,
} from 'lucide-react';
import {initials, roleLabel} from '../auth';
import {Logo} from '../ui/Logo';
import {HOME, goSection, navigate} from './router';
import type {Route} from './router';
import {useStudio} from './context';

type Item = {name: string; label: string; icon: React.ComponentType<{size?: number}>};

export const PRIMARY: Item[] = [
  {name: HOME, label: 'Calendario', icon: CalendarDays},
  {name: 'clientes', label: 'Clientes', icon: Users},
  {name: 'oportunidades', label: 'Oportunidades', icon: Sparkles},
];

export function secondaryItems(seasonVisible: boolean): Item[] {
  return [
    {name: 'reservaciones', label: 'Reservaciones', icon: ClipboardList},
    {name: 'citas', label: 'Citas y firmas', icon: FileCheck2},
    {name: 'paquetes', label: 'Paquetes', icon: Package},
    {name: 'equipo', label: 'Equipo y personal', icon: Camera},
    ...(seasonVisible ? [{name: 'temporada', label: 'Temporada navideña', icon: Snowflake}] : []),
    {name: 'actividad', label: 'Actividad', icon: Activity},
    {name: 'configuracion', label: 'Configuración', icon: Settings},
  ];
}

export const TITLES: Record<string, string> = {
  [HOME]: 'Calendario', clientes: 'Clientes', oportunidades: 'Oportunidades', mas: 'Más',
  reservaciones: 'Reservaciones', citas: 'Citas y firmas', paquetes: 'Paquetes',
  equipo: 'Equipo y personal', temporada: 'Temporada navideña', actividad: 'Actividad',
  configuracion: 'Configuración',
};

const SECTIONS = new Set([HOME, 'clientes', 'oportunidades', 'mas']);

const tabOf = (name: string) => (SECTIONS.has(name) ? name : 'mas');

function link(name: string, push = false) {
  return {
    href: `#/${name}`,
    onClick: (event: React.MouseEvent) => {
      event.preventDefault();
      if (push) navigate(name);
      else goSection(name);
    },
  };
}

export function Sidebar({route, onLogout}: {route: Route; onLogout: () => void}) {
  const {user, metrics, open, seasonVisible} = useStudio();
  const entry = (item: Item) => (
    <a key={item.name} {...link(item.name)} aria-current={route.name === item.name ? 'page' : undefined}>
      <item.icon size={19}/><span>{item.label}</span>
      {item.name === 'reservaciones' && metrics.pending > 0 && <b aria-label={`${metrics.pending} por aprobar`}>{metrics.pending}</b>}
    </a>
  );
  return <aside className="sidebar">
    <a className="brand" {...link(HOME)}>
      <Logo/>
      <span className="brand-name">Jordy Flores<small>Fotografía</small></span>
    </a>
    <button className="primary sidebar-create" onClick={() => open('create')}><Plus size={18}/>Nuevo</button>
    <nav aria-label="Secciones">
      {PRIMARY.map(entry)}
      <hr/>
      {secondaryItems(seasonVisible).map(entry)}
    </nav>
    <div className="profile">
      <span className="avatar">{initials(user.name)}</span>
      <div><strong>{user.name}</strong><small>{roleLabel[user.role] || 'Administrador'}</small></div>
      <button className="icon-btn" aria-label="Cerrar sesión" onClick={onLogout}><LogOut size={18}/></button>
    </div>
  </aside>;
}

export function Topbar({route}: {route: Route}) {
  const {user} = useStudio();
  return <header className="topbar">
    <Logo size="small"/>
    <h1>{TITLES[route.name] || TITLES[HOME]}</h1>
    <a className="avatar" {...link('configuracion', true)} aria-label={`Cuenta de ${user.name}`}>{initials(user.name)}</a>
  </header>;
}

export function BottomNav({route}: {route: Route}) {
  const {open} = useStudio();
  const current = tabOf(route.name);
  const items = [...PRIMARY, {name: 'mas', label: 'Más', icon: MoreHorizontal}];
  return <>
    <button className="fab" aria-label="Crear" onClick={() => open('create')}><Plus size={26}/></button>
    <nav className="bottom-nav" aria-label="Secciones">
      {items.map(item => <a key={item.name} {...link(item.name)} aria-current={current === item.name ? 'page' : undefined}>
        <item.icon size={22}/><span>{item.label}</span>
      </a>)}
    </nav>
  </>;
}
