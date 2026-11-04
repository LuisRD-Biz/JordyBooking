# Reorganización Git/CI — 3 de noviembre de 2026

Árbol inicial limpio; web ya publicada en GitHub en `543b1dd`.
Ramas publicadas en GitHub con autorización explícita del usuario.
[PR #1 — base](https://github.com/LuisRD-Biz/JordyBooking/pull/1), commit `ac45671`;
[PR #2 — web, borrador dependiente](https://github.com/LuisRD-Biz/JordyBooking/pull/2),
commit funcional `22ab5c2` sobre web original `543b1dd`. CI remoto de #1 correcto
(frontend, test, security); consultar #2 para el resultado de su ejecución vigente.
`main` verificada sin protección (`protected: false`), sin modificar reglas.

Ramas preparadas: `feature/project-baseline` desde `0d9d1e2` y `feature/website`
desde `543b1dd`. Primero revisar/integrar base con merge commit, después cambiar
el destino del PR web a `main` y revisar/integrar. No se fusiona en esta tarea.
Backend: 136 pruebas locales correctas con PostgreSQL aislado, Ruff y build del panel.
CI web: instalación congelada, TypeScript, build, auditoría y rutas de Workers local.
No se modifican migraciones ni servicios WhatsApp. No se despliega producción.
Cloudflare: rama de producción `main`, raíz `website`, assets `dist`; conexión
y protección de main pendientes de aprobación/configuración. No crear develop.
Ver `website-deployment.md` y los PR para resultados remotos; estados anteriores
a continuación se conservan como antecedentes, no instrucciones actuales.

---

# Recuperación — 3 de noviembre de 2026

Página pública implementada en `website/`, sobre `whatsapp-cloud-api`, sin tocar
el CRM ni sus servicios. Build y comprobaciones locales correctos. Cambios sin
commit/push; revisar `git status`. Wrangler no autenticado; **no desplegado**.
`https://jordyflores.com` continúa con Hello World (200 HTTPS).

Siguiente paso: seguir [website-deployment.md](website-deployment.md) para conectar
GitHub al Worker existente `young-moon-14a9`, raíz `website`, rama indicada.
También admite login y despliegue manual. No cambiar DNS ni publicar `frontend/`.
Faltan fotografías autorizadas, contactos oficiales y revisión del aviso integral.
La vista previa se inicia desde `website/` con `pnpm preview` (4174), después del build.
El estado de servicios/credenciales de WhatsApp descrito abajo es histórico y no
se ha vuelto a validar en esta sesión.

---

# Recuperación anterior — miércoles 21 de octubre de 2026

Última revisión: cierre del 20/10, zona America/Mexico_City.
Repositorio: `C:\Users\PC\Desktop\Jordy Booking\JordyBooking`.
Cambios guardados localmente; no se hizo push. Revisar `git status` antes de editar:
puede haber cambios de sesiones anteriores que deben conservarse.

## 1. Estado real

Panel local operativo en `http://127.0.0.1:8000/`, con frontend compilado y migración
de fase 5 `9c51e760ab12` aplicada. No hubo migración adicional al cerrar.

Al revisar: una instancia raíz del panel, una del receptor, una del worker y un
túnel ngrok existente. No se dejaron pruebas ni scripts de comprobación ejecutándose.
Los subprocesos Python hijos de una misma instancia Windows no son workers duplicados.

WhatsApp: recepción real previamente informada por el usuario y mensajes almacenados.
Existe un estado entregado en historial, pero **no se probó una nueva entrega real**
durante el cierre. El último intento de la configuración actual falló con
`http_401_meta_190`. Vigencia de credencial pendiente de revisión humana.

## 2. Arquitectura y servicios

| Componente | Responsabilidad | Requisitos |
| --- | --- | --- |
| FastAPI `jordy.main` + React/Vite | Panel, sesión, CRM, reservas, documentos, señales, reportes | PostgreSQL local; puerto 8000 |
| Motor de reservas | Disponibilidad, recursos, aprobación, contratos, reprogramación | Validaciones actuales; no alterarlas desde mensajes |
| `jordy.messaging.webhook` | GET de verificación y POST firmado; guarda cola entrante | Puerto 8001, App Secret, Verify Token, cuenta/emisor |
| `jordy.messaging.worker` | Procesa entrada y envíos manuales confirmados | PostgreSQL; para envío, credencial/allowlist/ventana o plantilla |
| ngrok | Entrada pública temporal a webhook | Autorización de exposición; solo puerto 8001 |
| `commercial_rules/models/commercial` | Reglas sin IA, propuestas y resúmenes | Texto almacenado y PostgreSQL; no necesita Meta |
| Recuperación de resúmenes | Día anterior a hora local optativa, recuperación al arrancar | Panel activo; horario guardado en base |

El panel y la información histórica funcionan sin ngrok. Recibir WhatsApps nuevos
requiere receptor + túnel + worker + suscripción Meta. Enviar manualmente requiere
panel + worker y credenciales válidas; los recibos de entrega requieren webhook.

## 3. Funcionalidades y acceso

- CRM: clientes, oportunidades, cotizaciones versionadas, citas y documentos.
- Reservas: solicitud, aprobación, contrato para eventos, recursos, bloqueos,
  cancelación y reprogramación mediante flujos explícitos.
- Mensajes: conversación, confirmación de envío, estado, vínculo con cliente.
- Pestañas **Mensajes / Señales / Notas / Fechas**; teclas flecha, Inicio y Fin.
- **Señales → Analizar mensajes guardados**; revisar/descartar y ver mensaje original.
- **Notas** registra contexto manual de llamada/audio/persona.
- **Fechas** registra consulta, tentativa, apartado por revisar o propuesta de cambio.
  Una propuesta no ocupa recursos ni modifica reserva/contrato.
- **Ver Resumen diario** en cabecera o **Resumen diario** en menú. Seleccionar fecha,
  generar o actualizar; revisar señales y abrir la conversación.
- Pantalla pequeña: **← Conversaciones** vuelve a la lista.

El análisis **no se ejecuta al recibir cada WhatsApp**. Ocurre por botón o al generar
un resumen (manual o recuperación nocturna configurada en fase 5).
Consultar un resumen guardado no lo regenera. No se añadió automatización al cierre.
El horario seguía sin configurar en la última revisión; no inventar una hora.
Los borradores de texto/notas sobreviven al cambio de pestaña dentro de la misma
conversación, pero no al cambio de contacto o recarga.

## 4. Errores actuales y antecedentes

- **Revisión pendiente:** `http_401_meta_190` del último intento con la configuración
  actual. Posible credencial inválida/caducada/revocada. No afirmar la causa exacta.
  No se modificó ni mostró el valor del secreto; tampoco se validó
  con Graph. La configuración local no declaraba faltantes.
- Historial conservado: cinco operaciones fallidas, incluidos `http_400`,
  `send_policy_blocked` y errores de autorización. Ninguna se reenvió.
- La alerta del último intento compara la revisión de configuración guardada.
  Históricos sin revisión no se usan como prueba del estado actual. Un intento
  posterior exitoso con la misma revisión sustituye el aviso.
- No había trabajos pending/sending/unknown en la lectura de cierre.
- Warning de pruebas existente: Starlette/TestClient/httpx obsoleto; no impidió pruebas.
- La referencia oficial Meta devolvió 429 al intentar consultarla; no declarar
  documentación actualizada verificada. Diagnósticos conservadores.
- El navegador tenía una versión anterior del frontend abierta. Se recargó para
  mostrar la nueva compilación; una pestaña vieja puede necesitar recarga.

## 5. Cambios de cierre

- `frontend/src/messages.tsx`: pestañas, acceso al resumen, navegación móvil,
  indicadores, diagnóstico desplegable y respuesta compacta.
- `frontend/src/commercial.tsx`: secciones por pestaña, consulta del mensaje original,
  confirmaciones y error visible al fallar la carga de reservas.
- `frontend/src/api.ts`: fallo de conexión comprensible; avisos de lectura separados
  de errores de acciones, se limpian al recuperarse.
- `frontend/src/main.tsx`, `style.css`: distribución acotada a pantalla y foco visible.
- `backend/jordy/messaging/api.py`: consulta de mensaje original validando conversación,
  indicadores de respuesta/señales y diagnóstico del último intento de la revisión.
- `backend/jordy/messaging/policy.py`: traducciones seguras de errores.
- `tests/test_messaging_diagnostics.py`: regresiones de diagnóstico, alcance y sesión.
- Documentos: `project-status.md`, `commercial-followup.md`, `whatsapp.md`, este archivo.

No se cambió la lógica de aprobación, ocupación, firmas ni envío de WhatsApp.

## 6. Validación realizada

- 26 casos aprobados: `test_messaging_diagnostics.py`, `test_commercial.py` y
  `test_messaging.py::test_reply_idempotency_and_authenticated_routes`.
- PostgreSQL de pruebas, esquema único y limpieza únicamente de ese esquema.
  No mensajes reales ni modificaciones a reservas de producción.
- Compilación TypeScript/Vite correcta. Compilaciones adicionales solo tras corregir
  el defecto visual del espacio de historial y el aviso de conexión que quedaba obsoleto; no se repitieron tests aprobados.
- GET 200: `/health/ready`, `/api/messaging/config`, `/api/messaging/conversations`,
  `/api/commercial/schedule`, `/api/commercial/summaries/2026-10-20`,
  `/api/commercial/plans`, `/api/search/bookings`, `/api/dashboard`.
- Receptor: POST sin firma devuelve 401. No se abrió/renovó el túnel.
- Navegador integrado 697×672: distribución, pestañas, notas, propuestas, análisis,
  acceso al resumen. Se corrigió y volvió a observar solamente el defecto visual.

No ejecutado: suite completa, envío real, validación remota del token, arranque en frío
de Windows/PostgreSQL, prueba visual exhaustiva de escritorio o todas las acciones
de escritura sobre datos reales. La consulta original se comprobó en datos aislados;
no había señales del día visibles para recorrer ese botón sobre datos reales.

## 7. Arranque en Windows

Primero comprobar si el panel ya responde: no iniciar instancias duplicadas.
En PowerShell, desde la raíz del repositorio:

```powershell
.\scripts\start-panel.ps1 -NoBrowser
```

El lanzador reutiliza la instancia preparada y gestiona PostgreSQL local ya
configurado. No inicializa ni migra automáticamente. Consultar `.local/launcher.log`
si falla. En esta sesión el servidor se reinició directamente con PostgreSQL ya
activo; no se validó arranque en frío. Alternativa de diagnóstico, **solo si no hay
panel activo y la base ya responde**:

```powershell
.\.venv\Scripts\python.exe -m uvicorn jordy.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Receptor y worker, cada uno en su propia terminal, solo si no están activos:

```powershell
.\scripts\start-whatsapp.ps1 -Mode receiver
.\scripts\start-whatsapp.ps1 -Mode worker
```

Ngrok, únicamente con autorización de exposición vigente y sin túnel duplicado:

```powershell
.\scripts\start-webhook-tunnel.ps1 -AuthorizeTemporaryExposure
```

El script comprueba aislamiento y fija destino 8001. **Nunca exponer 8000**.
No guardar URL temporal como contrato permanente: puede cambiar al reiniciar ngrok.
Actualizar callback/suscripción en Meta requiere intervención autorizada.
Ctrl+C detiene componentes iniciados en terminal. Para procesos ocultos, verificar
PID y línea de comando del repositorio antes de detenerlos; no matar todos los Python.

Logs de cierre: `.local/panel-closing.log`, `.local/panel-closing-error.log`.
Archivo de PID del panel: `.local/panel-server.pid`. Otros registros/PID pueden
proceder de arranques anteriores: un archivo PID por sí solo no confirma propiedad.

## 8. Configuración externa y límites

- `.env`: conexión PostgreSQL, clave administrativa y configuración local/zona.
- `.env.whatsapp`: access token, Phone Number ID, WABA ID, App Secret, Verify Token,
  versión Graph, allowlist, asociaciones explícitas, plantillas y banderas de envío.
- Cuenta/agente ngrok y configuración de webhook/suscripción Meta.
- No copiar valores privados a documentación, logs, capturas o commits.
- Mantener identidad entrante `521…` separada del destinatario `52…` autorizado;
  asociación explícita por cuenta/emisor, nunca transformación global del número.
- Acceso administrativo único, sin roles individuales ni multiestudio.
- Calendario externo sin conectar. Portal, IA y transcripción no implementados.
- Reglas conservadoras: fechas ambiguas requieren revisión; no comprenden todos
  los giros ni cambios de intención entre mensajes.
- Propuestas parciales: sin política de anticipo, apartados o vencimiento, no bloquean.
- Sin trabajo con PC apagada; recuperación al arrancar el panel.
- Respaldo/restauración, despliegue público endurecido y retención siguen pendientes.
- Propuestas cargan hasta 100 reservas por contacto en el selector; historiales
  mayores requieren ampliar la paginación. No afirmar que no existen más.

## 9. Próximos tres objetivos

1. Con el usuario, revisar la credencial de Meta y autorizar **un mensaje nuevo**
   controlado si quiere comprobar entrega; nunca reutilizar/reintentar fallos.
2. Validar con Jordy las señales reales y las políticas de apartados, anticipos,
   vencimientos y cambios contractuales. No deducir políticas de conversaciones.
3. Verificar respaldo/restauración y arranque en frío; completar revisión visual
   de escritorio antes de decidir calendario externo o despliegue.

## 10. Autorizaciones y disciplina

No hacer push, PR, despliegue, envío real ni exposición nueva por iniciativa propia.
No cambiar secretos, permisos, destinatarios autorizados o políticas comerciales sin
instrucción específica. No generar tokens. No modificar contratos ni reservas
confirmadas desde detecciones. No borrar historial, auditoría o fallos.

Preferir inspección enfocada, cambios agrupados y una sola pasada de pruebas
dirigidas. Repetir solo lo afectado por una corrección. No reconstruir módulos.
