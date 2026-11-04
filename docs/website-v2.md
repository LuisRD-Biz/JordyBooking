# Web V2 — revisión pendiente

Rama `feature/website-polish`, desde main `bff6ab3`. La propuesta local anterior
se conserva en `feature/portfolio-images`, commit `79a1e80`, y sus recursos se
mantienen disponibles; no aparecen en la selección visible de esta versión.

## Fotografías y composición

Originales inspeccionados visualmente: `PortadaBoda2.jpg`, `PortadaBoda1.jpg`,
`Boda-2162.jpg`, `PortadaXV1.jpg`, `flor-56.jpg`, `flor-307.jpg`.
Se respetan los nombres fuente, extensiones y mayúsculas; derivados con sufijos
640/1200/1920 y extensión WebP. No se usan miniaturas del sistema ni stock.
Autorización de publicación confirmada por el usuario en el chat de portafolio.

PortadaBoda2 abre la página; en móvil precede al texto. Se conserva el encuadre
completo, incluyendo arquitectura y rostros. Galería de seis piezas, alternando
escenas de bodas y XV: ceremonia, escenario, automóvil, joya, fiesta y pastel.
Cuadrícula de doce columnas con proporciones 7/5, 8/4 y 6/6; marcos finos y
montajes claros selectivos. En móvil pasa a una columna con márgenes diferenciados.
Sin lightbox: los encuadres completos y seis piezas evitan otra capa de interacción.
Sesiones y Eventos conservan filtros con estado vacío y enlace de consulta.

## Contacto

Número temporal y perfiles centralizados en content.ts. WhatsApp tiene mensajes
distintos para cotización y consulta, codificados con encodeURIComponent.
Se identifica públicamente como contacto temporal del desarrollador. Instagram y
Facebook tienen enlaces en contacto y pie; Instagram también junto a la galería.
No hay formularios, analítica, widgets o conexión a Cloud API. Privacidad actualizada
sin presentarla como aviso integral aprobado.
Botón flotante oculto con fotografías visibles y desde contacto hasta el pie.

## Comprobaciones

- Instalación congelada, TypeScript, build y auditoría estática correctos.
- Rutas con Workers local: inicio y privacidad 200; desconocida/admin/api/.env 404.
  Una comprobación durante la recarga del build dio 404 temporal en privacidad;
  se reinició el servidor y se repitió con el directorio completo.
- WebP sin EXIF/GPS/XMP; originales conservados, sin retoque de color o rostros.
- Revisión visual a 375, 390, 430, 768 y 1440 px; sin desbordamiento horizontal.
- Menú móvil, filtro vacío, galería, contacto y ocultación al llegar al pie revisados.
- WhatsApp abrió su página oficial con número y mensaje exactos, sin enviar nada.
- Instagram y Facebook abrieron los perfiles indicados con avisos de inicio de sesión;
  no se inició sesión ni se verificó contenido detrás de esos avisos.
- Comparativas locales: `.local/portfolio-review/desktop.png` (anterior),
  `.local/polish/after-desktop.png` y `after-mobile.png` (nueva).

No se modifica backend, administrador, migraciones, main, DNS ni Cloudflare.
El PR requiere revisión antes de integrar: main puede activar publicación automática.
Pendientes: aprobación visual, número definitivo y aviso integral revisado.
