import {useEffect, useRef, useState} from 'react';
import {contact, packageLink, whatsappLink} from './content';
import {SocialIcon} from './icons';
import {chapterPhotos, hero as coverPhoto, photographs, source} from './photos';
import type {Category, Photograph} from './photos';

function Photo({photo, sizes, eager = false}: {photo: Photograph; sizes: string; eager?: boolean}) {
  return <img className={'photo focus-' + photo.focal} src={source(photo)}
    srcSet={photo.widths.map(w => source(photo, w) + ' ' + w + 'w').join(', ')}
    sizes={sizes} alt={photo.alt} width={photo.width} height={photo.height}
    loading={eager ? 'eager' : 'lazy'} fetchPriority={eager ? 'high' : 'auto'} decoding="async"/>;
}

function External({href, className, children}: {href: string; className: string; children: React.ReactNode}) {
  return <a className={className} href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
}

type Open = (photos: Photograph[], index: number) => void;

/** Landscape photos take the full row; portraits go in pairs so nothing is cropped on a phone.
    A portrait left without a partner becomes a wide tile instead of leaving a hole. */
function Gallery({photos, open}: {photos: Photograph[]; open: Open}) {
  const portraits = photos.filter(p => p.orientation === 'portrait');
  const lonely = portraits.length % 2 ? portraits[portraits.length - 1].id : '';
  return <div className="gallery">{photos.map((photo, i) => {
    const shape = photo.orientation === 'portrait' && photo.id !== lonely ? 'tall' : 'wide';
    return <button key={photo.id} className={'tile ' + shape} onClick={() => open(photos, i)} aria-label={'Ampliar: ' + photo.title}>
      <Photo photo={photo} sizes={shape === 'wide' ? '(max-width: 860px) 100vw, 50vw' : '(max-width: 860px) 50vw, 25vw'}/>
      <span className="tile-caption">{photo.title}</span>
    </button>;
  })}</div>;
}

function Viewer({photos, initial, close}: {photos: Photograph[]; initial: number; close: () => void}) {
  const ref = useRef<HTMLDialogElement>(null);
  const touch = useRef(0);
  const [index, setIndex] = useState(initial);
  const move = (n: number) => setIndex(i => (i + n + photos.length) % photos.length);
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {dialog.close(); document.body.style.overflow = previous;};
  }, []);
  return <dialog ref={ref} className="viewer" aria-label="Fotografía ampliada" onCancel={close}
    onTouchStart={e => {touch.current = e.touches[0].clientX;}}
    onTouchEnd={e => {const dx = e.changedTouches[0].clientX - touch.current; if (Math.abs(dx) > 50 && photos.length > 1) move(dx > 0 ? -1 : 1);}}
    onKeyDown={e => {if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {e.preventDefault(); move(e.key === 'ArrowLeft' ? -1 : 1);}}}>
    <button autoFocus className="viewer-close" onClick={close} aria-label="Cerrar">×</button>
    <Photo key={photos[index].id} photo={photos[index]} sizes="100vw" eager/>
    <div className="viewer-controls">{photos.length > 1 && <button onClick={() => move(-1)} aria-label="Fotografía anterior">←</button>}
      <p aria-live="polite"><b>{photos[index].title}</b><span>{index + 1} / {photos.length}</span></p>
      {photos.length > 1 && <button onClick={() => move(1)} aria-label="Fotografía siguiente">→</button>}</div>
  </dialog>;
}

const services = [
  {id:'bodas', category:'Bodas', title:'Bodas', text:'Desde el Save the Date hasta el primer baile: preparativos, ceremonia civil o religiosa y la sesión formal de pareja, en fotografía y video.', cta:'Consultar mi fecha', channel:'bodas'},
  {id:'xv', category:'XV años', title:'XV años', text:'La sesión formal, el arreglo en casa, la bendición familiar, la ceremonia, la entrada y el vals. Fotografía y video para cada momento.', cta:'Cotizar mis XV', channel:'xv'},
  {id:'sesiones', category:'Sesiones', title:'Sesiones', text:'Retratos personales, de pareja y sesiones casuales. Elegimos juntos la luz y la locación, y te guiamos frente a la cámara.', cta:'Cotizar mi sesión', channel:'sesiones'},
] as const;

const packages = [
  {name:'Plata', price:'14,500', coverage:'Cobertura fotográfica del evento', video:'Video Full HD', prints:'70 impresiones y ampliación', digital:'300 fotografías digitales'},
  {name:'Oro', price:'22,500', coverage:'Save the Date y cobertura ampliada', video:'Video y dron', prints:'200 impresiones y ampliaciones', digital:'700 fotografías digitales'},
  {name:'Ruby', price:'34,500', coverage:'Save the Date y Trash the Dress', video:'Video con dos cámaras y dron', prints:'100 impresiones, ampliaciones y photobook', digital:'900 fotografías digitales'},
];
const benefits = [['coverage','Fotografía'], ['video','Video'], ['digital','Entrega digital'], ['prints','Impresos']] as const;

const steps = [
  ['Escríbenos', 'Cuéntanos por WhatsApp la fecha, el lugar y el tipo de evento. Te decimos si tenemos disponibilidad.'],
  ['Elige tu paquete', 'Revisamos juntos las opciones, resolvemos tus dudas y apartamos tu fecha.'],
  ['El gran día', 'Te acompañamos con fotografía y video: los preparativos, la ceremonia y la fiesta.'],
  ['Tus recuerdos', 'Recibes tus fotografías digitales y los impresos que incluye tu paquete.'],
];

const filters = ['Todas', 'Bodas', 'XV años', 'Sesiones'] as const;
const PAGE = 8;

export function Home() {
  const hero = coverPhoto;
  const [filter, setFilter] = useState<Category | 'Todas'>('Todas');
  const [limit, setLimit] = useState(PAGE);
  const [viewer, setViewer] = useState<{photos: Photograph[]; index: number} | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const open: Open = (photos, index) => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setViewer({photos, index});
  };
  useEffect(() => {
    const io = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {entry.target.classList.add('in'); io.unobserve(entry.target);}
    }), {rootMargin: '0px 0px -8% 0px'});
    document.querySelectorAll('[data-reveal]').forEach(el => io.observe(el));
    return () => io.disconnect();
  }, []);
  function closeViewer() {
    setViewer(null);
    requestAnimationFrame(() => opener.current?.focus({preventScroll:true}));
  }
  const all = photographs.filter(p => !p.isHero);
  const filtered = filter === 'Todas' ? all : all.filter(p => p.category === filter);
  const shown = filtered.slice(0, limit);
  return <main id="contenido">
    <section className="hero">
      {hero && <button className="hero-photo" onClick={() => open([hero], 0)} aria-label={'Ampliar: ' + hero.title}><Photo photo={hero} sizes="100vw" eager/></button>}
      <div className="hero-copy">
        <p className="kicker">Fotografía &amp; video</p>
        <h1>Historias que<br/><em>se quedan.</em></h1>
        <div className="actions">
          <a className="btn primary" href="#portafolio">Explorar portafolio</a>
          <a className="btn ghost" href="#paquetes">Ver paquetes</a>
        </div>
      </div>
    </section>

    <section className="section wrap" id="portafolio">
      <div className="section-head" data-reveal=""><p className="kicker">Portafolio</p><h2>El portafolio</h2></div>
      <div className="chips" role="group" aria-label="Categoría de fotografías">{filters.map(c =>
        <button key={c} aria-pressed={c === filter} onClick={() => {setFilter(c); setLimit(PAGE);}}>{c}</button>
      )}</div>
      <p className="sr-only" role="status">{filter}: {shown.length} de {filtered.length} fotografías.</p>
      <Gallery key={filter} photos={shown} open={(_, index) => open(filtered, index)}/>
      {filtered.length > limit && <button className="btn ghost more" onClick={() => setLimit(n => n + PAGE)}>Ver más fotos</button>}
    </section>

    <section className="section tinted" id="servicios"><div className="wrap">
      <div className="section-head" data-reveal=""><p className="kicker">Lo que hacemos</p><h2>Servicios</h2></div>
      <div className="cards">{services.map(s => {
        const cover = chapterPhotos.find(p => p.category === s.category && p.orientation === 'landscape')
          ?? all.find(p => p.category === s.category && p.orientation === 'landscape');
        return <article className="card service" key={s.id} id={s.id} data-reveal="">
          {cover && <div className="service-photo"><Photo photo={cover} sizes="(max-width: 860px) 100vw, 33vw"/></div>}
          <div className="card-body"><h3>{s.title}</h3><p>{s.text}</p>
            <External className="btn ghost" href={whatsappLink(s.channel)}>{s.cta}</External></div>
        </article>;
      })}</div>
    </div></section>

    <section className="section wrap" id="paquetes">
      <div className="section-head" data-reveal=""><p className="kicker">Inversión</p><h2>Paquetes de boda</h2>
        <p className="lead">Tres opciones para tu boda. ¿XV años o una sesión? Escríbenos y te armamos una cotización a tu medida.</p></div>
      <div className="cards">{packages.map(p =>
        <article className="card package" key={p.name} data-reveal=""><div className="card-body">
          <h3>{p.name}</h3><p className="amount">${p.price} <small>MXN</small></p>
          <dl>{benefits.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{p[key]}</dd></div>)}</dl>
          <External className="btn primary" href={packageLink(p.name)}>Cotizar {p.name}</External>
        </div></article>
      )}</div>
    </section>

    <section className="section tinted" id="proceso"><div className="wrap">
      <div className="section-head" data-reveal=""><p className="kicker">Proceso</p><h2>Cómo trabajamos</h2></div>
      <ol className="steps">{steps.map(([title, text]) => <li key={title} data-reveal=""><h3>{title}</h3><p>{text}</p></li>)}</ol>
    </div></section>

    <section className="section wrap contact" id="contacto">
      <div className="section-head" data-reveal=""><p className="kicker">Contacto</p><h2>Cuéntanos <em>tu historia.</em></h2>
        <p className="lead">Respondemos por WhatsApp y redes sociales.</p></div>
      <div className="contact-buttons" data-reveal="">
        <External className="btn confirm big" href={whatsappLink()}><SocialIcon kind="WhatsApp"/>WhatsApp</External>
        <External className="btn ghost big" href={contact.instagram}><SocialIcon kind="Instagram"/>Instagram</External>
        <External className="btn ghost big" href={contact.facebook}><SocialIcon kind="Facebook"/>Facebook</External>
      </div>
    </section>
    {viewer && <Viewer photos={viewer.photos} initial={viewer.index} close={closeViewer}/>}
  </main>;
}
