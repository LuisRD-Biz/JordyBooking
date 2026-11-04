# Verificación del entregable CRM y documentos

Fecha: 16 de octubre de 2026. Entorno local Windows, Python 3.13, PostgreSQL 18.

## Resultado

- **52 pruebas aprobadas** con PostgreSQL real, en un esquema aleatorio dentro de
  `jordy_panel_test`. La suite elimina únicamente su propio esquema.
- Ruff y comprobación de formato aprobados para backend, scripts, migraciones y tests.
- TypeScript y compilación de producción Vite aprobados.
- `alembic check`: no se detectaron operaciones nuevas; modelos y esquema coinciden.
- Sin publicación remota. La aplicación y PostgreSQL permanecen en localhost.

La suite mantiene una advertencia de deprecación del cliente de pruebas de Starlette
con httpx. No falla ninguna prueba; queda pendiente actualizar ese adaptador cuando se
revise la compatibilidad de dependencias. No se incorporó httpx2 solo para silenciarla.

## Cobertura

Regresión previa: disponibilidad, contratos, asignación, concurrencia real, exclusión
PostgreSQL, aprobación, cancelación, reprogramación atómica, idempotencia, auditoría,
outbox simulado, sesión, autorización y protección de origen.

Documentos: PDF e imagen válidos, contenido inválido, extensión prohibida, nombres con
traversal, tamaño máximo, metadatos/hash, originales autorizados, versiones, limpieza
ante error, asociación expresa a firma y vinculación posterior sin cambiar contrato.
Una prueba levanta dos procesos consecutivos reales de Uvicorn contra el esquema de
pruebas y verifica los mismos bytes del PDF después del reinicio; sin autorización
la descarga devuelve 401. No se colocaron documentos sintéticos en reservas reales.

Fechas: exacta, rango, mes, estado, orden/páginas sin omisiones en datos estables,
medianoche local frente a UTC, días de 23/24/25 horas al cambiar la zona configurada,
rangos inválidos y servicios todavía en curso desde el día anterior.

Clientes/CRM: captura ocasional atómica, idempotencia, rollback, coincidencias por
teléfono/correo y contacto antiguo sin reescribirlo; confirmación explícita para crear
otro contacto; interesados sin reserva/ocupación; versiones que conservan precio;
reserva desde versión anterior; aprobación y clasificación; reapertura expresa tras
cancelaciones; integridad de citas, búsqueda y transiciones.

## Comprobación de Windows

Se creó `Jordy Studio.lnk` mediante WScript.Shell. Se detuvo solamente el árbol de
procesos registrado del proyecto, comprobando su comando, y su cluster independiente
después de verificar que no había otros clientes. Abrir el acceso directo arrancó
PostgreSQL y FastAPI, alcanzó `/health/ready` y abrió el navegador. Un segundo arranque
conservó el mismo PID. Se compararon hashes y conteos de todas las tablas antes/después:
idénticos. El lanzador no ejecutó migraciones ni inicialización de datos.

Las pruebas automatizadas adicionales cubren reutilización de servidor listo, puertos
web/BD ajenos sin cerrarlos, configuración/frontend ausentes y limpieza del cluster
arrancado por un intento fallido. No se instalaron servicios permanentes.

## Comprobación del panel

Se revisó en navegador el inicio de sesión, búsqueda por fecha exacta con cinco
resultados para el 5 de noviembre, detalle con carga de documentos y contrato existente,
captura ocasional, búsqueda/selección de contacto existente, directorio con clasificación
real, oportunidades y formulario de citas. La revisión de 390 px confirmó filtros
adaptados y tabla con desplazamiento interno, sin desbordar la página. Se restauró el
tamaño normal. Los formularios de revisión no crearon datos ficticios en la base operativa.

Las pruebas de creación/subida/firma se ejecutaron sobre la base aislada; no se firmaron,
cancelaron ni modificaron reservaciones reales para probar los botones.

## Límites

No se ensayó un reinicio completo de Windows, una restauración sobre la base operativa
ni un análisis de malware. No se conectaron calendarios, WhatsApp, IA ni servicios de
correo. Los límites de cuentas, citas, documentos y apartados están descritos en
[la guía funcional](crm-documents.md).
