# Selección de portafolio — propuesta local

Rama: `feature/portfolio-images`, creada desde `origin/main` (`bff6ab3`).
El usuario confirmó en el chat que todas las fotografías están autorizadas para
publicación, incluidas las personas retratadas. La selección y su integración
permanecen pendientes de revisión visual; no se ha hecho push ni despliegue.

## Inspección y criterio

Se revisaron visualmente las 15 fotografías mediante hojas de contacto y se
ampliaron las candidatas 03, 05, 09, 10 y 11. Los números corresponden al inventario
local de revisión, no a nombres de clientes. No se dedujeron identidades, edades
exactas ni relaciones personales. XV es una clasificación editorial provisional
por vestuario y contexto, pendiente de confirmación del estudio.

La evaluación de nitidez es visual a tamaño de presentación, no un análisis de
foco de cada píxel del original. No se encontraron duplicados exactos por SHA-256.
12 y 14 comparten contexto de ceremonia y vestuario; son momentos diferentes,
no duplicados. Los retratos formales 03, 08 y 09 cubren una función semejante;
se priorizaron 03 y 09 por variedad de escala y ambiente.

| Nº | Categoría editorial | Evaluación y decisión |
| --- | --- | --- |
| 01 | Eventos sociales | Detalle de pastel bien expuesto; peluche y luces compiten por atención. Reserva; no forzar un detalle de menor fuerza visual. |
| 02 | Bodas | Gesto dinámico y líneas de árboles; rostros poco visibles, encuadre muy estrecho y luz contenida. Reserva frente a 05/11. |
| 03 | XV años | Seleccionada: expresión clara, rostro definido y textura lavanda; diagonal aporta variedad. Conservar orientación y manos. |
| 04 | XV años | Risas y energía de grupo, color intenso; fondo y varios gestos dispersan atención. Reserva frente al momento 06. |
| 05 | Bodas | Hero y galería: miradas como centro, separación tonal en blanco y negro, vestuario definido y fondo suave. Recorte 4:5 en hero; original completo en galería. |
| 06 | Eventos sociales | Seleccionada: expresión espontánea y contraste de luces; menor resolución que otras, suficiente para su tamaño web. Conservar ambos rostros. |
| 07 | Sesiones | Retrato individual en blanco y negro, sonrisa visible; fondo denso y encuadre estrecho. Reserva; contexto del evento no confirmado. |
| 08 | XV años | Retrato frontal legible; silla y globos recargan el fondo y repite el papel de retrato formal. Reserva. |
| 09 | XV años | Seleccionada: plano abierto, vestido completo, contraste verde/cielo y perfil legible. Edición oscura deliberada; conservar atmósfera sin aclarado automático. |
| 10 | Sesiones | Seleccionada: gesto cercano, marco natural y luz cálida; detalle más suave que 03. Mantener cuerpos completos y espacio inferior. |
| 11 | Bodas | Seleccionada: líneas del pasillo, contexto y escala amplia; sujetos pequeños y sombras intensas, adecuada como plano abierto, no hero móvil. |
| 12 | XV años | Perfil durante ceremonia; contexto útil pero banco invade el primer plano. Reserva documental. |
| 13 | XV años | Seleccionada: abrazo, amplitud del vestido y luz de pista; rostros ocultos, compensados por la emoción corporal. |
| 14 | XV años | Momento de ceremonia, gesto legible; fondo concurrido y vestimenta blanca domina el encuadre. Reserva, próxima a 12. |
| 15 | Eventos sociales | Seleccionada: acción, color y ambiente colectivo; composición densa, funciona como cierre enérgico, no como portada. |

## Orden propuesto

Hero: 05. Galería: **11 → 03 → 10 → 06 → 09 → 05 → 13 → 15**.
Alterna plano abierto, retrato cercano con textura, retrato ambiental y momento
espontáneo; después paisaje/vestuario, blanco y negro, abrazo y fiesta.
La repetición del hero dentro del filtro Bodas es intencional y reutiliza el mismo
archivo, sin duplicar recursos. Hay 2 bodas, 3 XV, 1 sesión y 2 eventos sociales.
No se añadió una toma de detalle independiente: la 01 queda como alternativa para
el usuario; se recomienda obtener un detalle más limpio para una futura selección.

## Integración

- Ocho imágenes únicas, tres tamaños WebP por imagen: 640, 960 y 1440 px de ancho.
- 24 archivos, aproximadamente 2.87 MiB en total. El navegador elige una variante
  con `srcSet`/`sizes`; no descarga deliberadamente las tres versiones.
- Nombres públicos neutros, sin nombres originales, rutas locales ni clientes.
- Copias generadas desde píxeles orientados: sin EXIF, GPS, XMP o perfiles heredados.
  No se modificó el color ni se aplicó retoque generativo.
- Hero prioritario; galería con carga diferida, dimensiones explícitas y alt descriptivo.
- Galería conserva proporciones originales para no cortar vestidos, manos o contexto.
  Hero usa 4:5 con foco vertical al 35%, comprobado en la portada.
- Los originales permanecen intactos. Inventario, rutas fuente, hashes y hojas de
  contacto están únicamente en `.local/portfolio-review/`, excluido de Git y del build.

## Comprobaciones y revisión

TypeScript, build y auditoría estática correctos (42 archivos de distribución).
WebP comprobados sin metadatos y hashes de los originales seleccionados sin cambios.
Vista de escritorio 1440×960 y móvil 390×844 sin desbordamiento horizontal; filtro
Bodas y carga de variantes de 640 px verificados. Capturas locales en el directorio
de revisión. No se repitieron pruebas de backend: no hay cambios en ese componente.

Vista local: iniciar `pnpm dev` desde `website/`, abrir `http://127.0.0.1:5174/`.
Revisar hero, categorías y orden antes de autorizar cualquier publicación.
