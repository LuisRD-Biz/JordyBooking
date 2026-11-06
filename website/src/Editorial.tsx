import {useEffect, useRef, useState} from 'react';
import {contact, packageLink, whatsappLink} from './content';
import {chapterPhotos, hero, portfolio, source} from './photos';
import type {Category, Photograph} from './photos';

function Photo({photo, sizes, eager = false}: {photo: Photograph; sizes: string; eager?: boolean}) {
  return <img className={'photo focus-' + photo.focal} src={source(photo)}
    srcSet={photo.widths.map(w => source(photo, w) + ' ' + w + 'w').join(', ')}
    sizes={sizes} alt={photo.alt} width={photo.width} height={photo.height}
    loading={eager ? 'eager' : 'lazy'} fetchPriority={eager ? 'high' : 'auto'} decoding="async"/>;
}

function Link({href, children}: {href: string; children: React.ReactNode}) {
  return <a className="ink-link" href={href} target="_blank" rel="noopener noreferrer">{children}<span aria-hidden="true">↗</span></a>;
}

type Open = (photos: Photograph[], index: number) => void;
function Gallery({photos, open}: {photos: Photograph[]; open: Open}) {
  return <div className="prints">{photos.map((photo, i) =>
    <figure key={photo.id} className={'print ' + photo.orientation}>
      <button className="mount" onClick={() => open(photos, i)} aria-label={'Ampliar: ' + photo.title}>
        <Photo photo={photo} sizes="(max-width: 720px) 92vw, 44vw"/><span aria-hidden="true">⤢</span>
      </button>
      <figcaption><i>{photo.title}</i><small>{photo.category}</small></figcaption>
    </figure>
  )}</div>;
}

function Viewer({photos, initial, close}: {photos: Photograph[]; initial: number; close: () => void}) {
  const ref = useRef<HTMLDialogElement>(null);
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
    onKeyDown={e => {if (e.key === 'ArrowLeft') move(-1); if (e.key === 'ArrowRight') move(1);}}>
    <button autoFocus className="close" onClick={close}>Cerrar ×</button>
    <Photo photo={photos[index]} sizes="100vw" eager/>
    <div className="viewer-controls">{photos.length > 1 && <button onClick={() => move(-1)} aria-label="Fotografía anterior">←</button>}
      <p aria-live="polite">{photos[index].title} · {index + 1} / {photos.length}</p>
      {photos.length > 1 && <button onClick={() => move(1)} aria-label="Fotografía siguiente">→</button>}</div>
  </dialog>;
}

const chapters = [
  {id:'bodas', category:'Bodas', title:'El día de su boda.', text:'Desde el Save the Date hasta el primer baile. Acompañamos los preparativos, la ceremonia civil o religiosa y la sesión formal de pareja. Fotografía y video para volver a la mirada de tu familia en medio de la celebración.', cta:'Consultar mi fecha de boda', channel:'bodas'},
  {id:'xv', category:'XV años', title:'Mis quince.', text:'El Save the Date y la sesión formal abren la historia. En casa, la bata, el maquillaje, el peinado y el vestido. Después, la bendición familiar, la ceremonia cuando forma parte del día, la entrada y el vals. Fotografía y video para acompañar cada momento.', cta:'Consultar paquetes de XV años', channel:'xv'},
  {id:'sesiones', category:'Sesiones', title:'Una tarde contigo.', text:'Retratos personales, fotografía de pareja y sesiones casuales. Elegimos juntos la luz y la composición, te guiamos frente a la cámara y buscamos un exterior u otra locación según disponibilidad. Cada presupuesto es personalizado.', cta:'Consultar precio y disponibilidad por WhatsApp', channel:'sesiones'}
] as const;

const packages = [
  {name:'Plata', price:'14,500', items:['Cobertura fotográfica del evento', 'Video Full HD', '70 impresiones y 300 fotografías digitales', 'Ampliación']},
  {name:'Oro', price:'22,500', items:['Save the Date y cobertura ampliada', 'Video y dron', '200 impresiones y 700 fotografías digitales', 'Ampliaciones']},
  {name:'Ruby', price:'34,500', items:['Save the Date y Trash the Dress', 'Video con dos cámaras y dron', '100 impresiones y 900 fotografías digitales', 'Ampliaciones y photobook']}
];

function Packages() {
  return <section className="packages" id="paquetes"><div className="wrap">
    <h3>Paquetes de boda</h3><div className="price-grid">{packages.map(p =>
      <article key={p.name}><h4>{p.name}</h4><p className="amount">${p.price} <small>MXN</small></p>
      <ul>{p.items.map(item => <li key={item}>{item}</li>)}</ul><Link href={packageLink(p.name)}>Cotizar {p.name}</Link></article>
    )}</div></div></section>;
}

export function Home() {
  const [filter, setFilter] = useState<Category | 'Todas'>('Todas');
  const [limit, setLimit] = useState(4);
  const [viewer, setViewer] = useState<{photos: Photograph[]; index: number} | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const open: Open = (photos, index) => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setViewer({photos, index});
  };
  function closeViewer() {
    setViewer(null);
    requestAnimationFrame(() => opener.current?.focus({preventScroll:true}));
  }
  const filtered = portfolio.filter(p => filter === 'Todas' || filter === p.category);
  return <main id="contenido">
    <section className="cover">
      {hero && <Photo photo={hero} sizes="100vw" eager/>}
      <div className="cover-copy"><p className="kicker">Fotografía &amp; video</p>
        <h1>Historias que<br/><em>se quedan.</em></h1>
        <a className="cover-button" href="#portafolio">Explorar portafolio <span aria-hidden="true">↓</span></a>
      </div>
      {hero && <button className="cover-credit" onClick={() => open([hero], 0)} aria-label={'Ampliar ' + hero.title}>{hero.title} <span aria-hidden="true">⤢</span></button>}
    </section>
    <div className="imprint wrap" id="nosotros"><span className="kicker">El estudio</span><p>Fotografiamos bodas, quince años y la complicidad de un retrato.</p>
      <a href="#servicios">Conoce las colecciones <span aria-hidden="true">↓</span></a></div>
    <section className="archive wrap" id="portafolio"><div className="section-head"><h2>El portafolio<span>.</span></h2>
      <div className="filters" aria-label="Categoría de fotografías">{(['Todas','Bodas','XV años','Sesiones'] as const).map(c =>
        <button key={c} aria-pressed={c === filter} onClick={() => {setFilter(c); setLimit(4);}}>{c}</button>
      )}</div></div>
      <Gallery photos={filtered.slice(0,limit)} open={(_,index) => open(filtered,index)}/>
      {filtered.length === 0 && <p>No hay fotografías visibles en esta colección.</p>}
      {filtered.length > limit && <button className="more" onClick={() => setLimit(n => n + 4)}>Ver más fotografías <span aria-hidden="true">＋</span></button>}
    </section>
    <div id="servicios">{chapters.map(ch => <div key={ch.id}>
      <section className={'chapter chapter-' + ch.id} id={ch.id}><div className="wrap">
        <div className="story-intro"><div><p className="kicker">{ch.category}</p><h2>{ch.title}</h2></div>
        <div><p>{ch.text}</p><Link href={whatsappLink(ch.channel)}>{ch.cta}</Link></div></div>
        <Gallery photos={chapterPhotos.filter(p => p.category === ch.category)} open={open}/>
      </div></section>
      {ch.id === 'bodas' && <Packages/>}
    </div>)}</div>
    <section className="inquire" id="contacto"><div className="wrap"><p className="kicker">Contacto</p>
      <h2>Cuéntame <em>tu historia.</em></h2><Link href={whatsappLink()}>Hablemos por WhatsApp</Link>
      <div className="contact-networks"><Link href={contact.instagram}>Instagram</Link><Link href={contact.facebook}>Facebook</Link></div>
    </div></section>{viewer && <Viewer photos={viewer.photos} initial={viewer.index} close={closeViewer}/>}
  </main>;
}
