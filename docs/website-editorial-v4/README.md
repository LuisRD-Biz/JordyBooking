# Catálogo editorial del estudio

La selección contiene 21 imágenes. Veinte proceden de la carpeta local `Photos/` y una, la ceremonia de XV años, del portafolio anterior. Para dos imágenes de la carpeta ya existían derivados en la web. Se conservan las firmas presentes en el encuadre. Las cuatro fotografías identificadas como Pexels quedaron fuera de la selección del estudio. Los originales están fuera del directorio de publicación.

## Cambiar una fotografía

1. Preparar WebP en varios anchos sin ampliar el original. Aplicar la orientación EXIF antes del redimensionado, conservar las proporciones y exportar sin metadatos personales. Guardar los derivados en `website/public/media/editorial/` con el formato `nombre-ANCHO.webp`.
2. Editar `website/src/photo-manifest.ts`. Conservar el identificador al sustituir una imagen, indicar las dimensiones del encuadre, los anchos disponibles, descripción visual, título, orientación y categoría. `base` es el prefijo público sin tamaño ni extensión.
3. `visible` controla la inclusión en la página. En V5, `isHero` selecciona la portada y `featured` reserva una fotografía para su capítulo. Si se oculta la portada, se conserva la portada tipográfica. El filtro de una categoría permite explorar también sus destacadas. Las restantes van al portafolio filtrable en orden de posición. Las galerías presentan el encuadre completo. La portada admite recorte y usa `focal` para anclar el sujeto.
4. Desde `website/`, ejecutar `pnpm build`. El prerender comprueba rutas de variantes, texto alternativo, dimensiones declaradas e identificadores únicos de las imágenes visibles. Revisar los recortes de portada a 390 y 1440 px. Para retirar un archivo del acceso público, retirar sus derivados de `public/` además de ocultarlo en el catálogo.

Los servicios y paquetes se mantienen en `Editorial.tsx`. Para Plata, Oro y Ruby se utilizó el texto facilitado por el desarrollador. El archivo «Paquetes de boda.html» no apareció en el proyecto. Los precios de XV años y sesiones se consultan con el estudio.

## Revisión visual

[Portada en escritorio](escritorio.jpg) · [Portada en móvil](movil.jpg) · [Galería](escritorio-galeria.jpg) · [Comparativa de paquetes](escritorio-paquetes.jpg)

## Administración futura

Una interfaz privada autenticada podría editar borradores con este mismo contrato. Guardaría originales en almacenamiento privado y generaría derivados estáticos versionados después de verificar tipo, dimensiones y metadatos. Un operador revisaría la previsualización antes de aprobar una versión del manifiesto y sus imágenes. La web pública consumiría únicamente esa versión publicada. Conservar la versión anterior permitiría revertir una selección sin recuperar archivos manualmente.
