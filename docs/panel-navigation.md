# Panel: navegación, calendario y hoja de reservación

El panel está pensado primero para el celular. El calendario es la pantalla de inicio y desde ahí se llega a todo.

## Rutas

El panel usa rutas por hash con historial real (`frontend/src/app/router.ts`), sin librerías.

| Ruta | Pantalla |
|---|---|
| `#/calendario[/AAAA-MM-DD]` | Calendario con la agenda del día seleccionado. Inicio tras entrar. |
| `#/reserva/:id` | Hoja de una reservación, sobre la pantalla desde la que se abrió. |
| `#/clientes`, `#/oportunidades`, `#/mas` | Secciones de la barra inferior. |
| `#/reservaciones[/por-aprobar]`, `#/citas`, `#/paquetes`, `#/equipo`, `#/temporada`, `#/actividad`, `#/configuracion` | Secciones dentro de «Más» (menú lateral en escritorio). |

Reglas del historial:

- El calendario siempre es la entrada inferior, incluso si se abre un enlace directo. Las secciones se reemplazan entre sí y las vistas de detalle se apilan. «Atrás» nunca sale del panel desde una vista interna.
- Cada diálogo u hoja agrega su propia entrada: «atrás» cierra el de arriba.
- Los datos se recargan al volver a la pestaña si pasaron más de 30 segundos.

## Calendario

- Vista Mes o Semana, botón «Hoy» y deslizamiento lateral. Un punto por tipo de evento: por aprobar, confirmada, cita y bloqueo.
- Debajo (o al lado, en escritorio) está la agenda del día con todos los tipos juntos y en orden.
- Un día libre ofrece «Nueva reservación el {fecha}» y «Bloquear». El botón «+» pregunta qué crear y para qué día.
- La franja superior («N por aprobar», «N firmas hoy») lleva a la lista correspondiente.
- Una sola llamada por mes visible: `GET /api/agenda?from=AAAA-MM-DD&to=AAAA-MM-DD[&include_cancelled=true]`.

### `GET /api/agenda`

Devuelve una lista ordenada por inicio. Los días se interpretan en `STUDIO_TIMEZONE`, el rango máximo es de 62 días y requiere una cuenta de administración.

```json
{
  "type": "booking | appointment | block",
  "id": 12,
  "starts_at": "2026-11-14T19:00:00Z",
  "ends_at": "2026-11-15T03:00:00Z",
  "title": "Nombre del cliente o del recurso",
  "subtitle": "Paquete, motivo de la cita o motivo del bloqueo",
  "status": "pending_approval | confirmed | completed | cancelled | scheduled | active",
  "kind": "session | event | contract | meeting | staff | equipment",
  "customer_id": 7,
  "booking_id": 12,
  "resource_id": null,
  "location": "Lugar acordado"
}
```

No contiene lógica de presentación, para que también sirva como herramienta de lectura de un operador automatizado.

## Hoja de reservación

`GET /api/bookings/{id}/summary` reúne en una lectura la reservación, el cliente, el contrato, las asignaciones, las citas y los conteos de notas y documentos.

- **Acciones fijas según el estado:** Aprobar, Editar, Reprogramar, Completar y Cancelar (con confirmación).
- **Editar** cambia fecha, hora y lugar. Solo se envía lo que cambió: `POST /api/bookings/{id}/reschedule` (el lugar es opcional y se conserva si se omite) o `POST /api/bookings/{id}/location`.
- **Notas:** `GET` y `POST /api/bookings/{id}/notes`. Solo se agregan; no se editan ni se borran. Cada nota guarda la cuenta que la escribió. `POST` acepta un encabezado `Idempotency-Key` (UUID) para que un reintento no la duplique.
- **Contrato:** un solo estado visible, Sin contrato → Archivo subido → Firmado → Vinculado, con un único botón para el siguiente paso. Subir un archivo nunca equivale a firmar.
- **Citas:** las de esa reservación, con acceso para programar otra.

## Quién hizo qué

Cada cambio queda en `audit_logs.actor` con el correo de la cuenta que lo hizo, o `local` para el acceso local de escritorio. Los procesos automáticos y el acceso con `X-Admin-Key` conservan el actor histórico `jordy-admin`. La pantalla Actividad muestra ese dato.

## WhatsApp y seguimiento comercial

Están apagados con `MESSAGING_ENABLED=false` (valor por defecto). Ver `docs/docker.md`.

## Instalación en el celular

El panel incluye `manifest.webmanifest` e iconos. En Android (Chrome) o iOS (Safari) se puede agregar a la pantalla de inicio y se abre a pantalla completa. No hay modo sin conexión: el panel siempre trabaja contra el servidor.

Para regenerar los iconos tras cambiar la marca o la paleta:

```powershell
uv run --no-project --with pillow python scripts/make_panel_icons.py
```
