import {useEffect, useRef, useState} from 'react';
import {contactLinks, hero, photographs, sections, services, studio} from './content';
import type {Category, Photograph} from './content';

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

function ImageSpace({photo, priority = false}: {photo: Photograph; priority?: boolean}) {
  if (photo.src) return <img className="photograph" src={photo.src} alt={photo.alt} width={photo.width} height={photo.height} loading={priority ? 'eager' : 'lazy'} fetchPriority={priority ? 'high' : 'auto'} decoding="async" />;
  return <div className={`image-space scene-${photo.id}`} role="img" aria-label="Espacio reservado para una fotografía autorizada de Jordy Flores; composición abstracta, no es un trabajo del portafolio.">
    <div className="light-study" aria-hidden="true"><span className="light-plane" /><span className="light-arch" /><span className="light-shadow" /><span className="light-line" /></div>
    <div className="frame-corner top-left" aria-hidden="true" /><div className="frame-corner bottom-right" aria-hidden="true" />
    <span className="placeholder-label">Fotografía por seleccionar</span>
    <span className="placeholder-index" aria-hidden="true">JF / {photo.id === 'hero' ? '01' : photo.id}</span>
  </div>;
}

function Footer() {
  return <footer className="site-footer"><a className="brand" href="/" aria-label="Volver al inicio"><Wordmark /></a><p>Historias que se quedan.</p><nav aria-label="Navegación del pie"><a href="/#portafolio">Portafolio</a><a href="/#contacto">Contacto</a><a href="/privacidad/">Privacidad</a></nav><span className="footer-note">Jordy Flores Fotografía</span></footer>;
}

function Home() {
  const [category, setCategory] = useState<Category | 'Todas'>('Todas');
  const links = contactLinks();
  const selected = photographs.filter(photo => category === 'Todas' || photo.category === category);
  return <main id="contenido">
    <section className="hero section-wrap" aria-labelledby="hero-title">
      <div className="hero-copy"><p className="eyebrow"><span className="small-line" /> UNA MIRADA. TU HISTORIA.</p><h1 id="hero-title">{studio.headline[0]}<br />{studio.headline[1]}<br /><em>{studio.headline[2]}</em></h1><p className="hero-intro">{studio.introduction}</p><a className="text-link" href="#portafolio">Explorar portafolio <Arrow /></a><div className="hero-footnote"><span>FOTOGRAFÍA & VIDEO</span><span>Con intención. Con emoción.</span></div></div>
      <figure className="hero-image"><ImageSpace photo={hero} priority /><figcaption><span>La luz cambia. La emoción permanece.</span><span aria-hidden="true">01 — 04</span></figcaption></figure>
      <a className="scroll-cue" href="#nosotros"><span aria-hidden="true">↓</span> DESCUBRE EL ESTUDIO</a>
    </section>
    <div className="service-ribbon" aria-label="Especialidades"><span>Bodas</span><i aria-hidden="true">✳</i><span>XV años</span><i aria-hidden="true">✳</i><span>Sesiones</span><i aria-hidden="true">✳</i><span>Eventos</span><i aria-hidden="true">✳</i><span>Fotografía y video</span></div>
    <section id="nosotros" className="about section-wrap" aria-labelledby="about-title"><div className="section-label"><span className="eyebrow">01 / EL ESTUDIO</span><span className="signature" aria-hidden="true">jf.</span></div><div><h2 id="about-title">Una mirada cercana<br />a lo que <em>importa.</em></h2><div className="about-text"><p>{studio.aboutText}</p><p>Nos interesan los gestos que no se repiten. Las personas detrás de cada celebración. Esas imágenes que, con el tiempo, se vuelven parte de ti.</p></div></div></section>
    <section id="servicios" className="services dark-section" aria-labelledby="services-title"><div className="section-wrap service-layout"><div className="service-heading"><p className="eyebrow">02 / LO QUE HACEMOS</p><h2 id="services-title">Una historia.<br /><em>Muchas formas</em><br />de recordarla.</h2><p>Momentos distintos, una misma intención:<br />conservar lo que se siente.</p><span className="outline-flower" aria-hidden="true">✳</span></div><div className="service-list">{services.map(service => <a href="#portafolio" key={service.number} onClick={() => setCategory(service.category)}><span className="service-number">{service.number}</span><div><h3>{service.name}</h3><p>{service.detail}</p></div><Arrow diagonal /></a>)}</div></div></section>
    <section id="portafolio" className="portfolio section-wrap" aria-labelledby="portfolio-title"><div className="portfolio-heading"><div><p className="eyebrow">03 / PORTAFOLIO</p><h2 id="portfolio-title">Instantes con<br /><em>algo que contar.</em></h2></div><p className="portfolio-note">Estamos preparando una selección de historias.<br />Estos espacios son composiciones visuales de muestra, no fotografías de trabajos realizados.</p></div><div className="filters" role="group" aria-label="Filtrar portafolio">{(['Todas', 'Bodas', 'XV años', 'Sesiones', 'Eventos'] as const).map(item => <button key={item} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div><p className="sr-only" role="status">{selected.length} espacios en {category.toLowerCase()}</p><div className="gallery">{selected.map(photo => <figure key={photo.id} className={`gallery-item ${photo.aspect}`}><div className="gallery-image"><ImageSpace photo={photo} /></div><figcaption><div><span className="eyebrow">{photo.category}</span><h3>{photo.title}</h3></div><span className="photo-index">/{photo.id}</span></figcaption></figure>)}</div></section>
    <section className="statement section-wrap"><p>Más que una imagen.<br /><em>Una forma de volver.</em></p><span className="eyebrow">JORDY FLORES FOTOGRAFÍA</span></section>
    <section id="contacto" className="contact section-wrap" aria-labelledby="contact-title"><div><p className="eyebrow">04 / CONTACTO</p><h2 id="contact-title">Toda historia empieza<br />con un <em>hola.</em></h2></div><div className="contact-content">{links.length ? <><p>Cuéntanos qué tienes en mente.<br />El primer paso es conocernos.</p><div className="contact-links">{links.map(link => <a key={link.label} href={link.href} rel={link.href.startsWith('https:') ? 'noopener noreferrer' : undefined}>{link.label}<Arrow diagonal /></a>)}</div></> : <><p>Estamos preparando nuestros canales oficiales de contacto. Pronto podrás encontrarlos aquí.</p><span className="contact-status"><span aria-hidden="true" /> CONTACTO EN PREPARACIÓN</span><a className="text-link" href="#servicios">Conoce nuestros servicios <Arrow /></a></>}</div></section>
  </main>;
}

function Privacy() {
  return <main id="contenido" className="legal section-wrap"><p className="eyebrow">JORDY FLORES FOTOGRAFÍA</p><h1>Sobre tu<br /><em>privacidad.</em></h1><p className="legal-lead">Información sobre esta primera versión del sitio.</p><section><h2>Una página de presentación</h2><p>Esta versión muestra información del estudio. No incluye formularios, cuentas de usuario, reservas en línea ni pagos. El sitio no incorpora herramientas de analítica, píxeles publicitarios ni almacenamiento de información en tu navegador.</p></section><section><h2>Funcionamiento técnico</h2><p>Para servir una página web, el proveedor de alojamiento recibe información técnica de las solicitudes, como la dirección IP. La publicación está preparada para Cloudflare. Esta página no establece plazos de conservación ni condiciones de otros proveedores que no hayan sido confirmados.</p></section><section><h2>Canales externos</h2><p>Cuando se habiliten enlaces oficiales a redes sociales o mensajería, al abrirlos saldrás de este sitio y se aplicarán las condiciones del servicio correspondiente. No se cargan contenidos incrustados de esas plataformas en esta página.</p></section><section><h2>Aviso integral pendiente</h2><p>El aviso de privacidad integral del estudio está pendiente de revisión y aprobación. Antes de habilitar la recopilación de datos personales en este sitio, deberán publicarse el responsable, las finalidades y los medios para ejercer los derechos que correspondan. Esta nota informativa no sustituye ese aviso.</p></section><a className="text-link" href="/">Volver al estudio <Arrow /></a></main>;
}

function NotFound() {
  return <main id="contenido" className="not-found section-wrap"><p className="eyebrow">404 / FUERA DE ENCUADRE</p><h1>Esta página<br /><em>no está aquí.</em></h1><p>Volvamos a donde empieza la historia.</p><a className="button-dark" href="/">Volver al inicio <Arrow /></a></main>;
}

export function App({path = '/'}: {path?: string}) {
  const home = path === '/' || path === '/index.html';
  const privacy = path === '/privacidad' || path === '/privacidad/' || path === '/privacidad/index.html';
  return <><a className="skip-link" href="#contenido">Saltar al contenido</a><Header home={home} />{home ? <Home /> : privacy ? <Privacy /> : <NotFound />}<Footer /></>;
}
