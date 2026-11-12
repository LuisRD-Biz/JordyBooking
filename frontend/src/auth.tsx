import React, {useState} from 'react';
import {ArrowRight, Eye, EyeOff, KeyRound, ShieldCheck} from 'lucide-react';
import {Logo} from './ui/Logo';
import {api} from './api';
import type {Row} from './shared';

export function initials(name?: string) {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] || 'J') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

export const roleLabel: Record<string, string> = {admin: 'Administrador', employee: 'Equipo', client: 'Cliente'};

function PasswordInput({name, label, autoComplete, minLength}: {name: string, label: string, autoComplete: string, minLength?: number}) {
  const [visible, setVisible] = useState(false);
  return <label className="field"><span>{label}<b> *</b></span>
    <span className="password-field">
      <input name={name} type={visible ? 'text' : 'password'} required autoComplete={autoComplete} minLength={minLength} maxLength={128} spellCheck={false} autoCapitalize="none"/>
      <button type="button" className="icon-btn" aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'} aria-pressed={visible} onClick={() => setVisible(v => !v)}>{visible ? <EyeOff size={17}/> : <Eye size={17}/>}</button>
    </span>
  </label>;
}

export function LoginCard({local, error, onLogin}: {local: boolean, error: string, onLogin: (user: Row) => void}) {
  const [message, setMessage] = useState(''), [busy, setBusy] = useState(false);
  const shown = message || error;
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setMessage(''); setBusy(true);
    const form = new FormData(e.currentTarget);
    try {
      onLogin(await api(local ? '/auth/local' : '/auth/login', 'POST', local ? {} : {email: form.get('email'), password: form.get('password')}));
    } catch (err) {
      setMessage((err as Error).message);
      const password = e.currentTarget.elements.namedItem('password') as HTMLInputElement | null;
      if (password) { password.value = ''; password.focus(); }
    } finally { setBusy(false); }
  }
  return <div className="login-page"><div className="login-card">
    <Logo size="large"/>
    <p className="brand-title">Jordy Flores <em>Fotografía</em></p>
    <h1>Un lugar para<br/>todo tu estudio.</h1>
    <p>Tu agenda, tu equipo y cada historia por capturar.</p>
    <form onSubmit={submit} noValidate={false}>
      {!local && <>
        <label className="field"><span>Correo<b> *</b></span><input name="email" type="email" required autoComplete="username" inputMode="email" autoCapitalize="none" spellCheck={false} maxLength={254} autoFocus/></label>
        <PasswordInput name="password" label="Contraseña" autoComplete="current-password"/>
      </>}
      <button className="primary" type="submit" disabled={busy}>{busy ? 'Verificando…' : 'Entrar al estudio'}<ArrowRight size={18}/></button>
    </form>
    {shown && <p className="error" role="alert">{shown}</p>}
    <small><ShieldCheck size={14}/>{local ? 'Acceso privado desde esta computadora' : 'Sesión protegida · 5 intentos fallidos bloquean 15 minutos'}</small>
  </div></div>;
}

export function PasswordChange({email}: {email?: string}) {
  const [state, setState] = useState<{ok?: string, error?: string, busy?: boolean}>({});
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget, form = new FormData(formEl);
    if (form.get('new_password') !== form.get('confirm')) { setState({error: 'Las contraseñas nuevas no coinciden.'}); return; }
    setState({busy: true});
    try {
      await api('/auth/password', 'POST', {current_password: form.get('current_password'), new_password: form.get('new_password')});
      formEl.reset();
      setState({ok: 'Contraseña actualizada. Se cerraron tus otras sesiones.'});
    } catch (err) { setState({error: (err as Error).message}); }
  }
  return <form className="password-form" onSubmit={submit}>
    <input type="email" name="username" value={email || ''} autoComplete="username" readOnly hidden/>
    <PasswordInput name="current_password" label="Contraseña actual" autoComplete="current-password"/>
    <PasswordInput name="new_password" label="Contraseña nueva (mínimo 12 caracteres)" autoComplete="new-password" minLength={12}/>
    <PasswordInput name="confirm" label="Repite la contraseña nueva" autoComplete="new-password" minLength={12}/>
    <button className="secondary" type="submit" disabled={state.busy}><KeyRound size={15}/>{state.busy ? 'Guardando…' : 'Cambiar contraseña'}</button>
    {state.error && <p className="error" role="alert">{state.error}</p>}
    {state.ok && <p className="success" role="status">{state.ok}</p>}
  </form>;
}
