# Revisión visual V5

Base de comparación: `main` en `42ccce1`, con V4 integrada. Cada lámina muestra la misma sección de V4 a la izquierda y de V5 a la derecha. Incluye portada, archivo, bodas, paquetes, XV años, sesiones y contacto.

[Escritorio · 1440 px](escritorio.webp) · [Tablet · 768 px](tablet.webp) · [Móvil · 390 px](movil.webp) · [Móvil pequeño · 360 px](pequeno.webp)

## Auditoría y decisiones

| Observación en V4 | Cambio en V5 |
| --- | --- |
| En la portada, el Volkswagen y la pareja dejan espacio libre para el titular. El único camino directo era explorar. | Se conserva fotografía, foco, título y tipografía. Una segunda acción abre la cotización del evento en WhatsApp. |
| En móvil la segunda figura se desplazaba a la derecha al 89 % del ancho; los retratos también se estrechaban. | Una columna con márgenes de 16 px y fotografía a ancho completo en 360 y 390 px. En tablet se usan dos columnas de peso más parecido. Escritorio conserva su asimetría. |
| El anillo y la arquitectura precedían a las personas en el archivo. | La apertura muestra un beso, la celebración en la escalinata, el baile y una pausa de la pareja. El brindis intercala un detalle colectivo a continuación. |
| Los beneficios de cada paquete estaban mezclados en una lista y el enlace de cotización tenía poco peso. | Se agrupan en fotografía, video, entrega digital e impresos. Los tres tienen el mismo orden de lectura y botón específico. En móvil, los paquetes se apilan. Se conservan importes y entregables confirmados. |
| WhatsApp y las redes competían con igual jerarquía en una zona de contacto extensa. | Composición compacta con botón principal de WhatsApp y enlaces secundarios. Se mantienen número, cuentas y mensajes. |

## Selección y orden

- **Portada** conserva `ultima-luz`. El nuevo campo `isHero` permite seleccionarla independientemente de los destacados. Al ocultarla se conserva el título y sus acciones.
- **Bodas** abre con `jardin`, donde el vestido se lee de cuerpo entero. `preparativos` acompaña con una escala más íntima. Las escenas de pareja, familia, ceremonia y baile continúan en el filtro Bodas.
- **XV años** abre con `ceremonia-xv`: la quinceañera y su vestido aparecen en el eje del altar. `pista`, con la bandera en primer plano, pasa al archivo de celebración.
- **Sesiones** reúne `encuentro` (vertical, pareja junto a la columna) y `calle` (horizontal, abrazo en contraluz). El filtro Sesiones incluye las destacadas cuando el visitante lo elige.
- **Archivo inicial**, en orden: `beso`, `escalinata`, `baile`, `pausa`, `brindis`, `fachada`, `bosque`, `damas`, `joya`, `rojo`, `pista`, `pastel-boda`, `ceremonia`, `copas` y `pastel`. La vista «Todas» evita repetir portada o destacados. Se utilizaron los derivados existentes.

## Verificación local

TypeScript, cuatro pruebas de regresión, prerender y auditoría de 107 archivos. Decodificación de 56 variantes WebP con ancho, proporción y ausencia de EXIF comprobados. Inicio y privacidad respondieron 200; página desconocida, admin, API y archivo de entorno devolvieron 404 con la política de seguridad. Se comprobaron canonical, referencia Open Graph y destinos de WhatsApp sin enviar mensajes.

En Edge se probaron filtros, carga incremental, visor con flechas, Escape y retorno del foco, menú móvil y ausencia de desbordamiento horizontal. Contraste de texto medido sobre colores sólidos: tinta/crema 13.8:1, etiquetas de beneficios 5.6:1, texto sobre vino 12.9:1 y precios 6.9:1. El título sobre fotografía se revisó visualmente. Estas comprobaciones no constituyen una certificación integral WCAG.

### Rendimiento de portada

Observaciones de navegador en localhost, Edge sin interfaz, DPR 1, caché deshabilitada, sin limitación de CPU o red, movimiento reducido. Una carga por tamaño y versión en la pasada registrada. Se muestreó la portada una vez cargadas las fuentes y antes de interactuar. No había Lighthouse CLI disponible. Los tiempos incluyen variación del equipo y del servidor local.

| Ancho | LCP V4 | LCP V5 | CLS inicial V4 / V5 |
| ---: | ---: | ---: | ---: |
| 1440 | 164 ms | 608 ms | 0.0123 / 0.0123 |
| 768 | 68 ms | 56 ms | 0 / 0 |
| 390 | 68 ms | 60 ms | 0 / 0 |
| 360 | 60 ms | 48 ms | 0 / 0 |

En una pasada V5 anterior el LCP de escritorio fue 212 ms. Para decidir sobre rendimiento en producción se necesitan varias cargas con red y CPU controladas. La portada conserva prioridad alta, dimensiones y variantes responsive; las galerías se cargan a demanda.
