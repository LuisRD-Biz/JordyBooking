/** Public copy only. Never import CRM records or environment files here. */
export type Category = 'Bodas' | 'XV años' | 'Sesiones' | 'Eventos';
export type Photograph = {
  id: string; category: Category; title: string; aspect: 'portrait' | 'landscape';
  src: string | null; alt: string; width: number; height: number; srcSet?: string;
};

export const studio = {
  name: 'Jordy Flores Fotografía',
  headline: ['Hay momentos', 'que merecen', 'quedarse.'],
  introduction: 'Fotografía y video para volver a sentir. Las miradas, los abrazos y esos pequeños instantes que hacen tu historia.',
  about: 'Una mirada cercana a lo que importa.',
  aboutText: 'Una boda, una celebración, una nueva etapa. Cada historia tiene su propio ritmo. Nuestro enfoque es acompañarla con sensibilidad, cuidando la luz, los detalles y la forma en que quieres recordarla.',
};

// Populate only with links confirmed by Jordy. Empty channels do not render.
export const contact = {
  whatsapp: '', // https://wa.me/ + confirmed international commercial number
  instagram: '',
  facebook: '',
  email: '',
};

export function contactLinks() {
  const candidates = [
    {label: 'WhatsApp', value: contact.whatsapp, hosts: ['wa.me']},
    {label: 'Instagram', value: contact.instagram, hosts: ['instagram.com', 'www.instagram.com']},
    {label: 'Facebook', value: contact.facebook, hosts: ['facebook.com', 'www.facebook.com', 'fb.com']},
  ];
  const links: {label: string; href: string}[] = [];
  for (const item of candidates) {
    if (!item.value) continue;
    const url = new URL(item.value);
    if (url.protocol !== 'https:' || !item.hosts.includes(url.hostname) || url.username || url.password) {
      throw new Error(`Enlace público no válido: ${item.label}`);
    }
    links.push({label: item.label, href: url.href});
  }
  if (contact.email) {
    if (!/^[^\s@?&]+@[^\s@?&]+\.[^\s@?&]+$/.test(contact.email)) throw new Error('Correo público no válido');
    links.push({label: 'Correo electrónico', href: `mailto:${contact.email}`});
  }
  return links;
}

export const services = [
  {number: '01', name: 'Bodas', detail: 'El inicio de algo que vale la pena recordar.', category: 'Bodas'},
  {number: '02', name: 'XV años', detail: 'Una nueva etapa. Una celebración muy tuya.', category: 'XV años'},
  {number: '03', name: 'Sesiones fotográficas', detail: 'Un momento para detenerte y ser tú.', category: 'Sesiones'},
  {number: '04', name: 'Eventos sociales', detail: 'Las personas y los instantes que los reúnen.', category: 'Eventos'},
  {number: '05', name: 'Fotografía y video', detail: 'La emoción, también en movimiento.', category: 'Todas'},
] as const;

// Publication permission confirmed by the owner; neutral public filenames.
export const hero: Photograph = {
  "id": "hero",
  "category": "Bodas",
  "title": "Una mirada compartida",
  "aspect": "portrait",
  "src": "/media/bodas-02-1440.webp",
  "alt": "Retrato en blanco y negro de una pareja con vestido de boda y traje, mirándose entre árboles.",
  "width": 1440,
  "height": 2160,
  "srcSet": "/media/bodas-02-640.webp 640w, /media/bodas-02-960.webp 960w, /media/bodas-02-1440.webp 1440w"
};
export const photographs: Photograph[] = [
  {
    "id": "01",
    "category": "Bodas",
    "title": "Bajo el cielo",
    "aspect": "landscape",
    "src": "/media/bodas-01-1440.webp",
    "alt": "Una pareja con vestimenta de boda al fondo de un pasillo entre sillas y flores.",
    "width": 1440,
    "height": 960,
    "srcSet": "/media/bodas-01-640.webp 640w, /media/bodas-01-960.webp 960w, /media/bodas-01-1440.webp 1440w"
  },
  {
    "id": "02",
    "category": "XV años",
    "title": "Luz en lavanda",
    "aspect": "portrait",
    "src": "/media/xv-01-1440.webp",
    "alt": "Retrato de una persona con tiara recostada sobre un vestido lavanda.",
    "width": 1440,
    "height": 1800,
    "srcSet": "/media/xv-01-640.webp 640w, /media/xv-01-960.webp 960w, /media/xv-01-1440.webp 1440w"
  },
  {
    "id": "03",
    "category": "Sesiones",
    "title": "Entre árboles",
    "aspect": "portrait",
    "src": "/media/sesiones-01-1440.webp",
    "alt": "Dos personas abrazadas bajo las ramas de un árbol, en una sesión al aire libre.",
    "width": 1440,
    "height": 2160,
    "srcSet": "/media/sesiones-01-640.webp 640w, /media/sesiones-01-960.webp 960w, /media/sesiones-01-1440.webp 1440w"
  },
  {
    "id": "04",
    "category": "Eventos",
    "title": "La alegría de estar",
    "aspect": "landscape",
    "src": "/media/eventos-01-1440.webp",
    "alt": "Dos personas sonríen mientras bailan bajo luces violetas.",
    "width": 1440,
    "height": 961,
    "srcSet": "/media/eventos-01-640.webp 640w, /media/eventos-01-960.webp 960w, /media/eventos-01-1440.webp 1440w"
  },
  {
    "id": "05",
    "category": "XV años",
    "title": "Verde y cielo",
    "aspect": "portrait",
    "src": "/media/xv-02-1440.webp",
    "alt": "Persona con tiara y vestido verde de amplia falda en un jardín bajo cielo nublado.",
    "width": 1440,
    "height": 2160,
    "srcSet": "/media/xv-02-640.webp 640w, /media/xv-02-960.webp 960w, /media/xv-02-1440.webp 1440w"
  },
  {
    "id": "06",
    "category": "Bodas",
    "title": "Una mirada compartida",
    "aspect": "portrait",
    "src": "/media/bodas-02-1440.webp",
    "alt": "Retrato en blanco y negro de una pareja con vestido de boda y traje, mirándose entre árboles.",
    "width": 1440,
    "height": 2160,
    "srcSet": "/media/bodas-02-640.webp 640w, /media/bodas-02-960.webp 960w, /media/bodas-02-1440.webp 1440w"
  },
  {
    "id": "07",
    "category": "XV años",
    "title": "Un abrazo en la pista",
    "aspect": "portrait",
    "src": "/media/xv-03-1440.webp",
    "alt": "Dos personas se abrazan durante un baile; un vestido rosa ocupa el primer plano.",
    "width": 1440,
    "height": 2016,
    "srcSet": "/media/xv-03-640.webp 640w, /media/xv-03-960.webp 960w, /media/xv-03-1440.webp 1440w"
  },
  {
    "id": "08",
    "category": "Eventos",
    "title": "La fiesta en movimiento",
    "aspect": "landscape",
    "src": "/media/eventos-02-1440.webp",
    "alt": "Escena de fiesta con un artista de traje rojo sosteniendo una bandera y personas a su alrededor.",
    "width": 1440,
    "height": 1029,
    "srcSet": "/media/eventos-02-640.webp 640w, /media/eventos-02-960.webp 960w, /media/eventos-02-1440.webp 1440w"
  }
];

export const sections = [
  ['nosotros', 'El estudio'], ['servicios', 'Servicios'], ['portafolio', 'Portafolio'], ['contacto', 'Contacto'],
] as const;
