# Panel administrativo local

React + TypeScript + Vite. El resultado compilado se sirve en el mismo origen que
FastAPI; no se expone la clave administrativa al JavaScript ni se guarda en localStorage.
Toda la información procede de PostgreSQL, sin datos ficticios o métricas simuladas.

## Uso

- Vista general: próximos eventos, pendientes y accesos rápidos.
- Agenda: calendario mensual, detalle del día y bloqueos de recursos.
- Reservaciones: crear, filtrar, consultar asignaciones/contrato, aprobar, cancelar,
  completar y reprogramar dentro de las reglas del backend.
- Clientes: altas, búsqueda y edición de contacto.
- Paquetes: alta/edición de precios, condiciones, tiempos y requisitos.
- Equipo y personal: altas, edición y bloqueos. No se permite quitar una capacidad
  utilizada en una reserva vigente.
- Temporada navideña: seis horarios diarios según el motor de disponibilidad.
- Actividad: auditoría y estado real de operaciones externas pendientes/simuladas.
- Configuración: zona horaria, sesión y estado de integración del calendario.

Las fechas de entrada se interpretan en la zona del estudio, independientemente de la
zona del navegador. Todas las listas de negocio se cargan por páginas de 200 registros;
actividad muestra los últimos 200 movimientos. Los errores de validación/conflicto
se muestran dentro del formulario. El backend siempre vuelve a validar.

## Iniciar de nuevo en Windows

1. `uv sync --locked`
2. Dentro de `frontend`: `pnpm install --frozen-lockfile` y `pnpm run build`.
3. Desde la raíz: `powershell -ExecutionPolicy Bypass -File scripts/start-panel.ps1`.
4. Abrir `http://127.0.0.1:8000` y pulsar **Entrar al estudio**.

El helper usa PostgreSQL 18 instalado en `C:\Program Files\PostgreSQL\18\bin`
(se puede indicar otra ruta con `PG_BIN`). Crea un cluster independiente en
`.local/panel-pgdata`, puerto 55433, y bases `jordy_panel` y `jordy_panel_test`.
Solo crea `.env` cuando no existe; no sobrescribe configuraciones anteriores.
La contraseña y la clave se generan aleatoriamente en archivos ignorados por Git.
No borres `.local` ni sus contraseñas: contiene los datos persistentes del panel.

## Seguridad y límites

El acceso de escritorio es opt-in (`LOCAL_PANEL_ACCESS=true`), exclusivamente loopback,
con Host y Origin exactos. Se confía en quienes tienen acceso a esta computadora.
No sirve como autenticación multiusuario ni debe exponerse a la red. Si se deshabilita,
se requiere la clave administrativa para iniciar sesión. Sesión firmada de ocho horas,
cookie HttpOnly/SameSite=Strict y Secure cuando el origen utiliza HTTPS.
Las mutaciones con cookie exigen Origin válido, evitando solicitudes desde otros sitios.
Cerrar sesión elimina la cookie del navegador; no hay registro de revocación por
dispositivo todavía. Antes de producción: cuentas individuales, revocación, rate limiting,
HTTPS y revisión de despliegue. Cambiar la clave invalida todas las sesiones firmadas.

No hay sincronización de calendario, envío de mensajes, IA ni reglas de vencimiento de
apartados habilitadas. El panel muestra esos límites y no ofrece botones falsos de conexión.
No hay eliminación permanente de datos desde la interfaz.

## Verificación

`pnpm run build` comprueba TypeScript y compila. `pytest` incluye sesión, rechazo de
cookies falsificadas, origen no autorizado, acceso local, edición de cliente/recurso y
todos los casos de reservas/concurrencia. La prueba de navegador verifica navegación,
sesión, diseño responsive y formularios; no se insertan clientes o paquetes ficticios
en la base del panel.
