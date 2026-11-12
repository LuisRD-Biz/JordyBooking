import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {AlertCircle, CheckCircle2} from 'lucide-react';
import {Logo} from '../ui/Logo';
import {all, api} from '../api';
import {LoginCard} from '../auth';
import {BookingSheet} from '../booking/BookingSheet';
import {CalendarPage} from '../calendar/CalendarPage';
import {dayKey, isDay} from '../lib/dates';
import {Activity} from '../pages/Activity';
import {Appointments} from '../pages/Appointments';
import {Bookings} from '../pages/Bookings';
import {Customers} from '../pages/Customers';
import {Leads} from '../pages/Leads';
import {Packages, Team} from '../pages/Catalog';
import {More} from '../pages/More';
import {Season} from '../pages/Season';
import {Settings} from '../pages/Settings';
import type {Row} from '../shared';
import {StudioContext} from './context';
import type {Dialog, Studio} from './context';
import {Dialogs} from './Dialogs';
import {HOME, afterOverlays, goBack, goSection, navigate, useRoute} from './router';
import type {Route} from './router';
import {BottomNav, Sidebar, Topbar} from './Shell';

const SEASON_KEY = 'jordy.season.always';
const STALE_MS = 30_000;

export function App() {
  const [user, setUser] = useState<Row | null>(null), [checking, setChecking] = useState(true);
  const [local, setLocal] = useState(false), [loginError, setLoginError] = useState('');

  useEffect(() => {
    Promise.all([api('/auth/session').catch(() => null), api('/auth/config')])
      .then(([session, config]) => { setUser(session); setLocal(config.local_access); })
      .catch(() => setLoginError('No se pudo conectar con el servidor.'))
      .finally(() => setChecking(false));
    const expired = () => { setUser(null); setLoginError('Tu sesión terminó. Vuelve a entrar.'); };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, []);

  if (checking) return <div className="login-page"><Logo size="large" pulse/><p>Abriendo el estudio…</p></div>;
  if (!user) return <LoginCard local={local} error={loginError} onLogin={account => { setLoginError(''); goSection(HOME); setUser(account); }}/>;
  return <StudioApp user={user} onLogout={async () => {
    try { await api('/auth/logout', 'POST'); } finally { setUser(null); }
  }}/>;
}

function StudioApp({user, onLogout}: {user: Row; onLogout: () => void}) {
  const zone: string = user.timezone || 'America/Mexico_City';
  const route = useRoute();
  const [data, setData] = useState<{packages: Row[]; resources: Row[]; metrics: Row}>({packages: [], resources: [], metrics: {}});
  const [revision, setRevision] = useState(0), [loading, setLoading] = useState(false), [error, setError] = useState('');
  const [toast, setToast] = useState(''), [dialog, setDialog] = useState<Dialog | null>(null);
  const [today, setToday] = useState(() => dayKey(new Date(), zone));
  const [day, setDay] = useState(today);
  const [seasonAlways, setSeasonAlwaysState] = useState(() => localStorage.getItem(SEASON_KEY) === '1');
  const loadedAt = useRef(0), loadedOnce = useRef(false);

  const baseRef = useRef<Route>({name: HOME, path: HOME});
  if (route.name !== 'reserva') baseRef.current = route;
  const base = baseRef.current;
  const selectedDay = base.name === HOME && isDay(base.param) ? base.param : day;
  useEffect(() => { if (base.name === HOME && isDay(base.param)) setDay(base.param); }, [base]);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [metrics, packages, resources] = await Promise.all([api('/api/dashboard'), all('/api/packages'), all('/api/resources')]);
      setData({metrics, packages, resources});
      setError('');
      loadedAt.current = Date.now();
    } catch (err) {
      setError(`No se pudo actualizar la información del estudio: ${(err as Error).message}`);
    } finally {
      setToday(dayKey(new Date(), zone));
      if (loadedOnce.current) setRevision(value => value + 1);
      loadedOnce.current = true;
      setLoading(false);
    }
  }, [zone]);

  useEffect(() => { void reload(); }, [reload]);
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === 'visible' && Date.now() - loadedAt.current > STALE_MS) void reload();
    };
    document.addEventListener('visibilitychange', refresh);
    return () => document.removeEventListener('visibilitychange', refresh);
  }, [reload]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 4000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const month = Number(today.slice(5, 7));
  const studio: Studio = useMemo(() => ({
    user, zone, today, selectedDay, ...data, revision, reload,
    changed: (message = 'Cambios guardados') => { setToast(message); void reload(); },
    open: (type, row) => afterOverlays(() => setDialog({type, row})),
    openBooking: id => navigate(`reserva/${id}`),
    seasonVisible: seasonAlways || month >= 9,
    seasonAlways,
    setSeasonAlways: value => { localStorage.setItem(SEASON_KEY, value ? '1' : '0'); setSeasonAlwaysState(value); },
  }), [user, zone, today, selectedDay, data, revision, reload, seasonAlways, month]);

  const bookingId = route.name === 'reserva' ? Number(route.param) : 0;

  return <StudioContext.Provider value={studio}>
    <div className="app">
      <Sidebar route={base} onLogout={onLogout}/>
      <div className="workspace">
        <Topbar route={base}/>
        {loading && <div className="loading-line" role="progressbar" aria-label="Actualizando"/>}
        <main className="main">
          {error && <div className="error" role="alert"><AlertCircle size={18}/><span>{error}. Se muestran los últimos datos cargados.</span><button className="text-btn" onClick={() => reload()}>Reintentar</button></div>}
          {base.name === HOME && <CalendarPage day={selectedDay} onDay={value => { setDay(value); navigate(`${HOME}/${value}`, {replace: true}); }}/>}
          {base.name === 'clientes' && <Customers/>}
          {base.name === 'oportunidades' && <Leads/>}
          {base.name === 'mas' && <More onLogout={onLogout}/>}
          {base.name === 'reservaciones' && <Bookings key={base.param || 'todas'} initial={base.param === 'por-aprobar' ? 'pending' : 'all'}/>}
          {base.name === 'citas' && <Appointments/>}
          {base.name === 'paquetes' && <Packages/>}
          {base.name === 'equipo' && <Team/>}
          {base.name === 'temporada' && <Season/>}
          {base.name === 'actividad' && <Activity/>}
          {base.name === 'configuracion' && <Settings onLogout={onLogout}/>}
        </main>
      </div>
      <BottomNav route={base}/>
      {bookingId > 0 && <BookingSheet key={bookingId} id={bookingId} onClose={goBack}/>}
      <Dialogs dialog={dialog} close={() => setDialog(null)}/>
      {toast && <div className="toast" role="status"><CheckCircle2 size={18}/>{toast}</div>}
    </div>
  </StudioContext.Provider>;
}
