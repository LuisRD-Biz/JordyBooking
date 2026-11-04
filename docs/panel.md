# Panel administrativo local

React + TypeScript + Vite. El resultado compilado se sirve en el mismo origen que
FastAPI; no se expone la clave administrativa al JavaScript ni se guarda en localStorage.
Toda la información procede de PostgreSQL, sin datos ficticios o métricas simuladas.

## Uso

- Vista general: próximos eventos, pendientes y accesos rápidos.
- Agenda: calendario mensual, detalle del día y bloqueos de recursos.
- Reservaciones: crear, filtrar, consultar asignaciones/contrato, aprobar, cancelar,
  completar y reprogramar dentro de las reglas del backend.
- Clientes: altas, clasificación verificable, destacados, búsqueda paginada e historial.
- Oportunidades: interesados, cotizaciones versionadas y solicitudes vinculadas.
- Citas y firmas: reuniones/citas administrativas, búsqueda y cambio de estado.
- Paquetes: alta/edición de precios, condiciones, tiempos y requisitos.
- Equipo y personal: altas, edición y bloqueos. No se permite quitar una capacidad
  utilizada en una reserva vigente.
- Temporada navideña: seis horarios diarios según el motor de disponibilidad.
- Actividad: auditoría y estado real de operaciones externas pendientes/simuladas.
- Configuración: zona horaria, sesión y estado de integración del calendario.

Las fechas de entrada se interpretan en la zona del estudio, independientemente de la
zona del navegador. Reservas, clientes, CRM, citas y documentos se filtran en PostgreSQL
y muestran páginas de 25 registros; actividad muestra los últimos 200 movimientos.
Recursos, paquetes y bloqueos mantienen el cargador de catálogos anterior.
Los errores de validación/conflicto
se muestran dentro del formulario. El backend siempre vuelve a validar.

## Iniciar de nuevo en Windows

Haz doble clic en **Jordy Studio** en el escritorio. Espera a que se abra el navegador
y pulsa **Entrar al estudio** si no tienes una sesión activa. El acceso directo ya fue
creado en esta computadora. Si el panel está abierto, se reutiliza el servidor.

El arranque valida `.env`, dependencias, frontend y cluster independiente
`.local/panel-pgdata`, puerto 55433, base `jordy_panel`. Busca PostgreSQL compatible con
`PG_VERSION` en `PG_BIN`, Program Files y registro de instalaciones. No necesita
administrador, no instala servicios y solo escucha en `127.0.0.1:8000`.
Verifica conexión, directorio de datos y revisión Alembic antes de abrir el navegador.
Un bloqueo de archivo serializa dobles clics simultáneos. Si el puerto corresponde a
otra aplicación, se informa y no se cierra. Un fallo parcial detiene únicamente los
procesos que ese intento arrancó. No inicializa, borra, reinicializa ni migra bases.

Ante un error se muestra un mensaje y se guarda `.local/launcher.log`; los detalles del
servidor/PostgreSQL quedan en `.local/panel-server-error.log` y los registros de PostgreSQL.
No compartas credenciales. No borres `.local`: contiene base, documentos y contraseñas.

### Instalación y mantenimiento técnico

1. `uv sync --locked`.
2. En `frontend`: `pnpm install --frozen-lockfile` y `pnpm run build`.
3. En una instalación nueva únicamente, `python scripts/setup_local.py` prepara el
   cluster independiente y genera secretos locales. No usarlo como restauración ni
   sobre una configuración desconocida. La instalación actual ya está preparada.
4. Para actualizaciones: respaldar base y documentos, revisar las migraciones y ejecutar
   `.venv/Scripts/alembic.exe upgrade head`; las destructivas requieren autorización.
5. Desde la raíz: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install-shortcut.ps1`.
   Usa la ruta de escritorio de Windows; solo actualiza un acceso directo si identifica
   este proyecto. Si se mueve la carpeta, el acceso anterior debe revisarse explícitamente.
6. Para diagnóstico sin navegador: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-panel.ps1 -NoBrowser`.

ExecutionPolicy Bypass se aplica exclusivamente a ese proceso del acceso directo; no
cambia la política del sistema. No se añadieron tareas de inicio ni servicios permanentes.
Cerrar el navegador no apaga la base ni el servidor; se reutilizan hasta apagar Windows.

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

El acceso directo se probó con el panel y su cluster detenidos, tras verificar que no
había otros clientes de PostgreSQL. Arrancó ambos y abrió el navegador; el segundo
arranque reutilizó el mismo PID. Todas las tablas conservaron idénticos hashes y conteos.
Pruebas de fallo cubren puertos ajenos, configuración/frontend ausentes y limpieza de
un arranque parcial. [Guía de funciones y límites](crm-documents.md).
