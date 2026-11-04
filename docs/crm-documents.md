# CRM, documentos y búsqueda

## Auditoría y alcance del corte

Se partió de `6c06fae` en `booking-mvp`: ya existían reservas transaccionales,
matching de capacidades, exclusión de recursos en PostgreSQL, contratos administrativos,
sesión local, panel React, auditoría y outbox simulado. No existían archivos privados,
oportunidades, cotizaciones versionadas, citas ni acceso directo. El panel descargaba
todas las reservas/clientes para filtrar en memoria. Se conservaron los módulos previos.

La migración es aditiva. Antes de aplicarla se creó un respaldo de PostgreSQL en
`.local/backups/20261016-022838/before-crm.dump`. Se verificaron por hash todos los
valores originales: 8 reservas, 3 clientes, 5 contratos, 3 paquetes, 11 recursos y
sus relaciones, auditoría y outbox. No se insertaron clientes de ejemplo en la base operativa.

## Cómo comprobar las funciones

1. **Reservaciones → Nueva reservación**: elige cliente existente, registro ocasional
   o nuevo contacto; captura nombre/teléfono sin salir del formulario. La solicitud y
   el cliente se guardan en una transacción. Sigue pendiente de aprobación y no bloquea.
2. **Reservaciones → filtros**: elige fecha exacta, rango o mes/año; combina estado,
   servicio y nombre. En filtros adicionales busca fechas de subida/firma. El filtro
   contrato adjunto significa archivo de tipo contrato, no firma registrada.
3. **Detalle → Documentos y contratos**: selecciona o arrastra PDF/JPG/PNG, clasifica,
   añade observaciones y guarda. Descarga el original o abre la vista de imagen. Para
   sustituirlo elige su versión vigente; la anterior permanece descargable.
4. **Registrar contrato** registra expresamente folio/fecha de firma y, opcionalmente,
   archivo. Si el contrato ya existía, **Vincular documento al contrato** asocia el archivo
   sin cambiar sus condiciones ni fecha. Subir o vincular nunca confirma la reservación.
5. **Clientes** muestra inicialmente personas con contrataciones. Usa la clasificación
   para consultar todos, interesados, ocasionales, recurrentes o destacados. **Historial**
   abre sus reservas paginadas; **Editar** permite observaciones y destacado manual.
6. **Oportunidades → Nuevo interés** guarda contacto, servicio, canal y fecha opcional.
   Abre su historial, crea versiones desde un paquete y elige **Crear solicitud con esta
   cotización**. La reserva conserva precio/condiciones de esa versión. El historial
   permite abrir la reserva y consultar las citas vinculadas. Si todas sus reservas
   fueron canceladas, **Volver a cotizar** reabre explícitamente el seguimiento y permite
   crear una nueva versión; no borra ni reutiliza la reserva anterior.
7. **Detalle de reserva → Programar cita** agenda firma o reunión con lugar e inicio/fin.
   **Citas y firmas** permite buscar y cancelar/completar citas. Una cita de firma no
   registra la firma ni aprueba. Completar exige que haya pasado su final.

## Clasificación y duplicados

- Interesado: tiene oportunidad y ninguna reserva confirmada/completada.
- Ocasional: contacto sin contrataciones ni oportunidad.
- Cliente: una reserva confirmada/completada.
- Recurrente: al menos dos reservas confirmadas/completadas.
- Destacado: selección administrativa independiente de esos conteos.

El tipo de evento no define recurrencia. El contacto se comparte mediante claves
foráneas, no copias de datos personales. Se avisa por teléfono normalizado o correo sin
distinción de mayúsculas; nunca se vincula o fusiona automáticamente por nombre.
El usuario selecciona la coincidencia o confirma que se trata de otra persona.
Los campos libres antiguos que mezclan varios datos deben revisarse manualmente;
solo se interpretan como identificador cuando contienen únicamente teléfono o correo.

## Documentos privados

`DOCUMENT_ROOT` usa por defecto `.local/documents`, fuera de `frontend/dist`.
`DOCUMENT_MAX_BYTES` predeterminado: 10 MiB, configurable entre 1 KiB y 50 MiB.
Nombre interno UUID, SHA-256, tipo validado, tamaño, fecha, observaciones, actor,
grupo/versión y estado vigente se guardan como metadatos. No se sirven rutas físicas.
La identidad actual es el administrador único `jordy-admin`, no cuentas individuales.

La subida usa un temporal exclusivo, límite durante streaming, fsync, validación por
parser, bloqueo de reserva, metadatos y renombrado dentro del mismo directorio antes
de confirmar la transacción. Los errores limpian solo los archivos de esa operación.
Un apagón justo entre renombrado y commit puede dejar un archivo huérfano; no se borra
automáticamente. Para mantenimiento, detener subidas, respaldar, comparar nombres
contra `booking_documents.storage_key` y revisar cualquier sobrante antes de eliminarlo.

Los PDF cifrados, sin páginas o con ciertas acciones automáticas/adjuntos se rechazan.
Las imágenes se decodifican y se limitan a 25 millones de píxeles. PDF se descarga como
adjunto octet-stream con nosniff; no se interpreta en el panel. Solo imágenes admiten
vista previa. Descarga y vista requieren autorización, con no-store. No hay antivirus:
la validación de formato no garantiza ausencia de malware. No hay borrado definitivo
ordinario; sustituir añade versión y conserva el original.

**Respaldo:** conservar juntos PostgreSQL, el directorio privado de documentos y la
configuración local protegida. Un pg_dump por sí solo no contiene archivos. Hacer el
respaldo sin subidas concurrentes o con una instantánea coordinada. No publicar `.env`,
`.local`, originales ni backups. La restauración debe probarse en una copia independiente;
no ejecutar pg_restore sobre datos operativos sin revisión y autorización.

## Filtros

`/api/search/{bookings,customers,leads,appointments}` y el listado de documentos aceptan
`page`, `page_size` (1–100), texto, orden y una modalidad de fecha: `day`, `date_from`/
`date_to`, o `month`+`year`. La interfaz usa 25 resultados por página; la agenda diaria 10.
PostgreSQL aplica WHERE, COUNT, ORDER BY, OFFSET y LIMIT. Los clientes se ordenan por
nombre/ID; los demás por su fecha/ID. Los resúmenes mensuales se agregan en PostgreSQL.

Los días se interpretan en `STUDIO_TIMEZONE`: desde medianoche local inclusiva hasta
medianoche del día siguiente exclusiva, convertidas a UTC. Se incluyen completos los
días finales. Rango invertido, combinaciones incompatibles y meses inválidos se rechazan.
Registro, actividad o fecha solicitada se seleccionan en clientes/oportunidades. Las
fechas históricas desconocidas permanecen nulas y no coinciden con filtros de registro.

## Límites deliberados

No hay firma electrónica, negociación de cotizaciones fuera del catálogo, antivirus,
usuarios individuales, mensajería ni sincronización real. Las citas son administrativas:
si ocupan tiempo de producción, registrar además un bloqueo del recurso. No se inventó
una regla automática de asignación para citas. No hay vencimiento de apartados navideños
porque sigue pendiente la decisión comercial. Las citas no envían avisos al cliente.

La auditoría registra acciones y actor; no es un historial detallado de cada valor editado.
Los contratos existentes mantienen las restricciones previas sobre cambios/reprogramación.
