import {useState} from 'react';
import {whatsappLink, sections} from './content';
import {Home} from './Editorial';
import {SocialIcon} from './icons';

function Arrow() {
  return <span aria-hidden="true"> →</span>;
}

function Header({home}: {home: boolean}) {
  const [open, setOpen] = useState(false);
  return <header className="site-header"><div className="bar wrap">
    <a href="/" className="brand" aria-label="Jordy Flores Fotografía, inicio"><img className="brand-logo" src="/logo-camara.svg" alt="" width="765" height="578"/><span className="wordmark">Jordy Flores<small>FOTOGRAFÍA</small></span></a>
    <button className="menu-toggle" aria-expanded={open} aria-controls="main-navigation" onClick={() => setOpen(!open)}>{open ? 'Cerrar' : 'Menú'}<i aria-hidden="true"/></button>
    <nav id="main-navigation" className={open ? 'site-nav is-open' : 'site-nav'} aria-label="Navegación principal">
      {sections.map(([id, label]) => <a key={id} href={`${home ? '' : '/'}#${id}`} onClick={() => setOpen(false)}>{label}</a>)}
    </nav>
  </div></header>;
}

function Dock({home}: {home: boolean}) {
  return <div className="dock">
    <a className="btn ghost" href={`${home ? '' : '/'}#paquetes`}>Ver paquetes</a>
    <a className="btn primary" href={whatsappLink()} target="_blank" rel="noopener noreferrer"><SocialIcon kind="WhatsApp"/>WhatsApp</a>
  </div>;
}

function Footer() {
  return <footer className="site-footer"><div className="wrap">
    <a className="brand" href="/" aria-label="Volver al inicio"><span className="wordmark">Jordy Flores<small>FOTOGRAFÍA</small></span></a>
    <nav aria-label="Navegación del pie"><a href="/#portafolio">Portafolio</a><a href="/#paquetes">Paquetes</a><a href="/#contacto">Contacto</a><a href="/privacidad/">Privacidad</a></nav>
    <p>Fotografía y video · Bodas, XV años y sesiones</p>
  </div></footer>;
}

function Privacy() {
  return <main id="contenido" className="legal section-wrap"><p className="eyebrow">JORDY FLORES FOTOGRAFÍA</p><h1>Sobre tu<br /><em>privacidad.</em></h1><p className="legal-lead">Información sobre esta primera versión del sitio.</p><section><h2>Una página de presentación</h2><p>Esta versión muestra información del estudio. No incluye formularios, cuentas de usuario, reservas en línea ni pagos. El sitio no incorpora herramientas de analítica, píxeles publicitarios ni almacenamiento de información en tu navegador.</p></section><section><h2>Funcionamiento técnico</h2><p>Para servir una página web, el proveedor de alojamiento recibe información técnica de las solicitudes, como la dirección IP. El alojamiento está configurado para Cloudflare. Esta página no establece plazos de conservación ni condiciones de otros proveedores que no hayan sido confirmados.</p></section><section><h2>Canales externos</h2><p>Al abrir los enlaces a Instagram, Facebook o WhatsApp saldrás de este sitio y se aplicarán las condiciones del servicio correspondiente. WhatsApp dirige temporalmente al número del desarrollador, no al número comercial definitivo del estudio. No se cargan contenidos incrustados de esas plataformas en esta página.</p></section><section><h2>Aviso integral pendiente</h2><p>El aviso de privacidad integral del estudio está pendiente de revisión y aprobación. Antes de habilitar la recopilación de datos personales en este sitio, deberán publicarse el responsable, las finalidades y los medios para ejercer los derechos que correspondan. Esta nota informativa no sustituye ese aviso.</p></section><a className="text-link" href="/">Volver al estudio <Arrow /></a></main>;
}

function NotFound() {
  return <main id="contenido" className="not-found section-wrap"><p className="eyebrow">404 / FUERA DE ENCUADRE</p><h1>Esta página<br /><em>no está aquí.</em></h1><p>Volvamos a donde empieza la historia.</p><a className="btn primary" href="/">Volver al inicio</a></main>;
}

export function App({path = '/'}: {path?: string}) {
  const home = path === '/' || path === '/index.html';
  const privacy = path === '/privacidad' || path === '/privacidad/' || path === '/privacidad/index.html';
  return <><a className="skip-link" href="#contenido">Saltar al contenido</a><Header home={home} />{home ? <Home /> : privacy ? <Privacy /> : <NotFound />}<Footer /><Dock home={home} /></>;
}
