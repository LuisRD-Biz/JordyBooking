import {useEffect, useRef, useState} from 'react';
import {contactLinks, contact, whatsappLink, hero, photographs, sections, services, studio} from './content';
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
  if (photo.src) return <img className="photograph" src={photo.src} srcSet={photo.srcSet} sizes={priority ? "(max-width: 640px) 87vw, (max-width: 950px) 88vw, 49vw" : "(max-width: 640px) 87vw, 42vw"} alt={photo.alt} width={photo.width} height={photo.height} loading={priority ? 'eager' : 'lazy'} fetchPriority={priority ? 'high' : 'auto'} decoding="async" />;
  return <div className={`image-space scene-${photo.id}`} role="img" aria-label="Espacio reservado para una fotografía autorizada de Jordy Flores; composición abstracta, no es un trabajo del portafolio.">
    <div className="light-study" aria-hidden="true"><span className="light-plane" /><span className="light-arch" /><span className="light-shadow" /><span className="light-line" /></div>
    <div className="frame-corner top-left" aria-hidden="true" /><div className="frame-corner bottom-right" aria-hidden="true" />
    <span className="placeholder-label">Fotografía por seleccionar</span>
    <span className="placeholder-index" aria-hidden="true">JF / {photo.id === 'hero' ? '01' : photo.id}</span>
  </div>;
}

function SocialIcon({kind}: {kind: string}) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true" className="social-icon">{kind === 'Instagram' ? <><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7"/></> : kind === 'Facebook' ? <path d="M14 22V12h4l.6-4H14V6c0-1 .4-2 2-2h3V1h-3c-4 0-6 2-6 5v2H7v4h3v10"/> : <><path d="M4 18 2 22l5-1a10 10 0 1 0-3-3Z"/><path d="m8 7 2 3-1 1c1 2 2 3 4 3l1-1 3 2c-1 4-6 2-8 0S5 8 8 7Z"/></>}</svg>;
}
function FloatingContact() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    const update = () => {
      const target = document.getElementById('contacto');
      const photoVisible = Array.from(document.querySelectorAll('main img')).some(image => {
        const box = image.getBoundingClientRect(); return box.bottom > 0 && box.top < innerHeight;
      });
      setHidden(photoVisible || (!!target && target.getBoundingClientRect().top < innerHeight));
    };
    const observer = new IntersectionObserver(update);
    document.querySelectorAll('main img, #contacto').forEach(target => observer.observe(target));
    update();
    return () => observer.disconnect();
  }, []);
  return hidden ? null : <a className="floating-contact" href={whatsappLink()} target="_blank" rel="noopener noreferrer" aria-label="Contactar por WhatsApp"><SocialIcon kind="WhatsApp"/><span>Hablemos</span></a>;
}
function Footer() {
  return <footer className="site-footer"><a className="brand" href="/" aria-label="Volver al inicio"><Wordmark /></a><p>Historias que se quedan.</p><nav aria-label="Navegación del pie"><a href="/#portafolio">Portafolio</a><a href="/#contacto">Contacto</a><a href="/privacidad/">Privacidad</a></nav><div className="footer-socials">{contactLinks().filter(link=>link.label !== "Correo electrónico").map(link=><a key={link.label} href={link.label === "WhatsApp" ? whatsappLink() : link.href} target="_blank" rel="noopener noreferrer"><SocialIcon kind={link.label}/>{link.label}</a>)}</div><span className="footer-note">Jordy Flores Fotografía</span></footer>;
}

function Home() {
  const [category, setCategory] = useState<Category | 'Todas'>('Todas');
  const selected = photographs.filter(photo => category === 'Todas' || photo.category === category);
  return <main id="contenido">
    <section className="hero section-wrap" aria-labelledby="hero-title">
      <div className="hero-copy"><p className="eyebrow"><span className="small-line" /> UNA MIRADA. TU HISTORIA.</p><h1 id="hero-title">{studio.headline[0]}<br />{studio.headline[1]}<br /><em>{studio.headline[2]}</em></h1><p className="hero-intro">{studio.introduction}</p><div className="hero-actions"><a className="primary-cta" href={whatsappLink("hero")} target="_blank" rel="noopener noreferrer"><SocialIcon kind="WhatsApp"/>Cotizar por WhatsApp</a><a className="text-link" href="#portafolio">Explorar portafolio <Arrow /></a></div><div className="hero-footnote"><span>FOTOGRAFÍA & VIDEO</span><span>Con intención. Con emoción.</span></div></div>
      <figure className="hero-image"><ImageSpace photo={hero} priority /><figcaption><span>La luz cambia. La emoción permanece.</span><span aria-hidden="true">JF / 01</span></figcaption></figure>
      <a className="scroll-cue" href="#nosotros"><span aria-hidden="true">↓</span> DESCUBRE EL ESTUDIO</a>
    </section>
    <div className="service-ribbon" aria-label="Especialidades"><span>Bodas</span><i aria-hidden="true">✳</i><span>XV años</span><i aria-hidden="true">✳</i><span>Sesiones</span><i aria-hidden="true">✳</i><span>Eventos</span><i aria-hidden="true">✳</i><span>Fotografía y video</span></div>
    <section id="nosotros" className="about section-wrap" aria-labelledby="about-title"><div className="section-label"><span className="eyebrow">01 / EL ESTUDIO</span><span className="signature" aria-hidden="true">jf.</span></div><div><h2 id="about-title">Una mirada cercana<br />a lo que <em>importa.</em></h2><div className="about-text"><p>{studio.aboutText}</p><p>Nos interesan los gestos que no se repiten. Las personas detrás de cada celebración. Esas imágenes que, con el tiempo, se vuelven parte de ti.</p></div></div></section>
    <section id="servicios" className="services dark-section" aria-labelledby="services-title"><div className="section-wrap service-layout"><div className="service-heading"><p className="eyebrow">02 / LO QUE HACEMOS</p><h2 id="services-title">Una historia.<br /><em>Muchas formas</em><br />de recordarla.</h2><p>Momentos distintos, una misma intención:<br />conservar lo que se siente.</p><span className="outline-flower" aria-hidden="true">✳</span></div><div className="service-list">{services.map(service => <a href="#portafolio" key={service.number} onClick={() => setCategory(service.category)}><span className="service-number">{service.number}</span><div><h3>{service.name}</h3><p>{service.detail}</p></div><Arrow diagonal /></a>)}</div></div></section>
    <section id="portafolio" className="portfolio section-wrap" aria-labelledby="portfolio-title"><div className="portfolio-heading"><div><p className="eyebrow">03 / PORTAFOLIO</p><h2 id="portfolio-title">Instantes con<br /><em>algo que contar.</em></h2></div><p className="portfolio-note">Seis fotografías. Dos formas de celebrar.<br />Del gran escenario a los detalles que permanecen.</p></div><div className="filters" role="group" aria-label="Filtrar portafolio">{(['Todas', 'Bodas', 'XV años', 'Sesiones', 'Eventos'] as const).map(item => <button key={item} aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div><p className="sr-only" role="status">{selected.length} fotografías en {category.toLowerCase()}</p>{!selected.length && <div className="empty-portfolio"><p>Estamos preparando esta selección.</p><a className="text-link" href={whatsappLink()} target="_blank" rel="noopener noreferrer">Cuéntanos tu idea <Arrow /></a></div>}<div className="gallery">{selected.map(photo => <figure key={photo.id} className={`gallery-item ${photo.aspect}`}><div className="gallery-image"><ImageSpace photo={photo} /></div><figcaption><div><span className="eyebrow">{photo.category}</span><h3>{photo.title}</h3></div><span className="photo-index">/{photo.id}</span></figcaption></figure>)}</div><a className="instagram-invitation" href={contact.instagram} target="_blank" rel="noopener noreferrer"><SocialIcon kind="Instagram"/>Descubre más historias en Instagram <Arrow diagonal /></a></section>
    <section className="statement section-wrap"><p>Más que una imagen.<br /><em>Una forma de volver.</em></p><span className="eyebrow">JORDY FLORES FOTOGRAFÍA</span></section>
    <section id="contacto" className="contact section-wrap" aria-labelledby="contact-title"><div><p className="eyebrow">04 / CONVERSEMOS</p><h2 id="contact-title">Tu historia comienza<br />con una <em>conversación.</em></h2><p className="contact-intro">Cuéntanos qué estás planeando. Ya sea una boda, XV años, sesión o celebración especial, nos encantará conocer tu historia.</p></div><div className="contact-content"><a className="contact-primary" href={whatsappLink()} target="_blank" rel="noopener noreferrer"><SocialIcon kind="WhatsApp"/><span><small>WHATSAPP</small>Hablemos de tu evento</span><Arrow diagonal /></a><div className="contact-links"><a href={contact.instagram} target="_blank" rel="noopener noreferrer"><SocialIcon kind="Instagram"/>Descubre más historias en Instagram <Arrow diagonal /></a><a href={contact.facebook} target="_blank" rel="noopener noreferrer"><SocialIcon kind="Facebook"/>Encuéntranos en Facebook <Arrow diagonal /></a></div></div></section><FloatingContact/>
  </main>;
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
