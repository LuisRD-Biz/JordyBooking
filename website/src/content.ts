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
  whatsapp: 'https://wa.me/524499209781', // https://wa.me/ + confirmed international commercial number
  instagram: 'https://www.instagram.com/jordy_fotografia/',
  facebook: 'https://www.facebook.com/Jordyfloresss/',
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

export const hero: Photograph = {"id": "hero", "category": "Bodas", "title": "El instante y su escenario", "aspect": "landscape", "src": "/media/PortadaBoda2-1920.webp", "alt": "Una pareja con vestimenta de boda se besa en el interior de un templo.", "width": 1920, "height": 1371, "srcSet": "/media/PortadaBoda2-640.webp 640w, /media/PortadaBoda2-1200.webp 1200w, /media/PortadaBoda2-1920.webp 1920w"};
export const photographs: Photograph[] = [
  {
    "id": "01",
    "category": "Bodas",
    "title": "El instante y su escenario",
    "aspect": "landscape",
    "src": "/media/PortadaBoda2-1920.webp",
    "alt": "Una pareja con vestimenta de boda se besa en el interior de un templo.",
    "width": 1920,
    "height": 1371,
    "srcSet": "/media/PortadaBoda2-640.webp 640w, /media/PortadaBoda2-1200.webp 1200w, /media/PortadaBoda2-1920.webp 1920w"
  },
  {
    "id": "02",
    "category": "XV años",
    "title": "Una celebración que comienza",
    "aspect": "landscape",
    "src": "/media/PortadaXV1-1920.webp",
    "alt": "Vista amplia de una ceremonia con un vestido de celebración al centro.",
    "width": 1920,
    "height": 1371,
    "srcSet": "/media/PortadaXV1-640.webp 640w, /media/PortadaXV1-1200.webp 1200w, /media/PortadaXV1-1920.webp 1920w"
  },
  {
    "id": "03",
    "category": "Bodas",
    "title": "Una pausa para dos",
    "aspect": "landscape",
    "src": "/media/PortadaBoda1-1920.webp",
    "alt": "Una pareja se besa junto a un automóvil rojo decorado con flores.",
    "width": 1920,
    "height": 1371,
    "srcSet": "/media/PortadaBoda1-640.webp 640w, /media/PortadaBoda1-1200.webp 1200w, /media/PortadaBoda1-1920.webp 1920w"
  },
  {
    "id": "04",
    "category": "XV años",
    "title": "Los pequeños símbolos",
    "aspect": "landscape",
    "src": "/media/flor-56-1920.webp",
    "alt": "Una mano sostiene un estuche rojo abierto con una joya.",
    "width": 1920,
    "height": 1371,
    "srcSet": "/media/flor-56-640.webp 640w, /media/flor-56-1200.webp 1200w, /media/flor-56-1920.webp 1920w"
  },
  {
    "id": "05",
    "category": "Bodas",
    "title": "Todo lo que se siente",
    "aspect": "landscape",
    "src": "/media/Boda-2162-1920.webp",
    "alt": "Dos personas con vestimenta de boda y gafas de fiesta sonríen hacia la cámara.",
    "width": 1920,
    "height": 1371,
    "srcSet": "/media/Boda-2162-640.webp 640w, /media/Boda-2162-1200.webp 1200w, /media/Boda-2162-1920.webp 1920w"
  },
  {
    "id": "06",
    "category": "XV años",
    "title": "Detalles para recordar",
    "aspect": "landscape",
    "src": "/media/flor-307-1920.webp",
    "alt": "Pastel de celebración con una rosa bajo una cúpula y un peluche al lado.",
    "width": 1920,
    "height": 1371,
    "srcSet": "/media/flor-307-640.webp 640w, /media/flor-307-1200.webp 1200w, /media/flor-307-1920.webp 1920w"
  }
];

export const sections = [
  ['nosotros', 'El estudio'], ['servicios', 'Servicios'], ['portafolio', 'Portafolio'], ['contacto', 'Contacto'],
] as const;

export const whatsappMessages = {
  hero: 'Hola, vi la página de Jordy Flores Fotografía y me gustaría cotizar un evento.',
  general: 'Hola, me gustaría recibir información sobre fotografía y video.',
};
export function whatsappLink(kind: keyof typeof whatsappMessages = 'general') {
  return `${contact.whatsapp}?text=${encodeURIComponent(whatsappMessages[kind])}`;
}
