import {useEffect, useRef, useState} from 'react';
import {contactLinks, whatsappLink, sections} from './content';
import {Home} from './Editorial';

function Arrow({diagonal = false}: {diagonal?: boolean}) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={diagonal ? 'arrow diagonal' : 'arrow'}><path d="M4 12h15m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.2" /></svg>;
}

function Wordmark() {
  return <span className="wordmark">Jordy Flores<span>FOTOGRAFÍA</span></span>;
}

function Header({home}: {home: boolean}) {
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && open) {setOpen(false); toggle.current?.focus();}
    };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [open]);
  return <header className="site-header">
    <a href="/" className="brand" aria-label="Jordy Flores Fotografía, inicio"><Wordmark /></a>
    <button className="menu-toggle" ref={toggle} aria-expanded={open} aria-controls="main-navigation" onClick={() => setOpen(!open)}>{open ? 'Cerrar' : 'Menú'}<span aria-hidden="true">{open ? '−' : '+'}</span></button>
    <nav id="main-navigation" className={open ? 'navigation is-open' : 'navigation'} aria-label="Navegación principal">
      {sections.map(([id, label]) => <a key={id} href={`${home ? '' : '/'}#${id}`} onClick={() => setOpen(false)}>{label}{id === 'contacto' && <Arrow diagonal />}</a>)}
    </nav>
  </header>;
}

function SocialIcon({kind}: {kind: string}) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true" className="social-icon">{kind === 'Instagram' ? <><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7"/></> : kind === 'Facebook' ? <path d="M14 22V12h4l.6-4H14V6c0-1 .4-2 2-2h3V1h-3c-4 0-6 2-6 5v2H7v4h3v10"/> : <><path d="M4 18 2 22l5-1a10 10 0 1 0-3-3Z"/><path d="m8 7 2 3-1 1c1 2 2 3 4 3l1-1 3 2c-1 4-6 2-8 0S5 8 8 7Z"/></>}</svg>;
}
function Footer() {
  return <footer className="site-footer"><a className="brand" href="/" aria-label="Volver al inicio"><Wordmark /></a><p>Historias que se quedan.</p><nav aria-label="Navegación del pie"><a href="/#portafolio">Portafolio</a><a href="/#contacto">Contacto</a><a href="/privacidad/">Privacidad</a></nav><div className="footer-socials">{contactLinks().filter(link=>link.label !== "Correo electrónico").map(link=><a key={link.label} href={link.label === "WhatsApp" ? whatsappLink() : link.href} target="_blank" rel="noopener noreferrer"><SocialIcon kind={link.label}/>{link.label}</a>)}</div><span className="footer-note">Jordy Flores Fotografía</span></footer>;
}

function Privacy() {
  return <main id="contenido" className="legal section-wrap"><p className="eyebrow">JORDY FLORES FOTOGRAFÍA</p><h1>Sobre tu<br /><em>privacidad.</em></h1><p className="legal-lead">Información sobre esta primera versión del sitio.</p><section><h2>Una página de presentación</h2><p>Esta versión muestra información del estudio. No incluye formularios, cuentas de usuario, reservas en línea ni pagos. El sitio no incorpora herramientas de analítica, píxeles publicitarios ni almacenamiento de información en tu navegador.</p></section><section><h2>Funcionamiento técnico</h2><p>Para servir una página web, el proveedor de alojamiento recibe información técnica de las solicitudes, como la dirección IP. El alojamiento está configurado para Cloudflare. Esta página no establece plazos de conservación ni condiciones de otros proveedores que no hayan sido confirmados.</p></section><section><h2>Canales externos</h2><p>Al abrir los enlaces a Instagram, Facebook o WhatsApp saldrás de este sitio y se aplicarán las condiciones del servicio correspondiente. WhatsApp dirige temporalmente al número del desarrollador, no al número comercial definitivo del estudio. No se cargan contenidos incrustados de esas plataformas en esta página.</p></section><section><h2>Aviso integral pendiente</h2><p>El aviso de privacidad integral del estudio está pendiente de revisión y aprobación. Antes de habilitar la recopilación de datos personales en este sitio, deberán publicarse el responsable, las finalidades y los medios para ejercer los derechos que correspondan. Esta nota informativa no sustituye ese aviso.</p></section><a className="text-link" href="/">Volver al estudio <Arrow /></a></main>;
}

function NotFound() {
  return <main id="contenido" className="not-found section-wrap"><p className="eyebrow">404 / FUERA DE ENCUADRE</p><h1>Esta página<br /><em>no está aquí.</em></h1><p>Volvamos a donde empieza la historia.</p><a className="button-dark" href="/">Volver al inicio <Arrow /></a></main>;
}

export function App({path = '/'}: {path?: string}) {
  const home = path === '/' || path === '/index.html';
  const privacy = path === '/privacidad' || path === '/privacidad/' || path === '/privacidad/index.html';
  return <><a className="skip-link" href="#contenido">Saltar al contenido</a><Header home={home} />{home ? <Home /> : privacy ? <Privacy /> : <NotFound />}<Footer /></>;
}
