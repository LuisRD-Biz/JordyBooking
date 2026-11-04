# Corrección de destinatarios — 19 de octubre de 2026

## Diagnóstico comprobado

Se inspeccionó configuración y metadatos de PostgreSQL sin imprimir credenciales ni
cuerpos de mensajes. El usuario ya comprobó recepción real; no se reconstruyó el receptor.

- `WHATSAPP_PHONE_NUMBER_ID` estaba vacío tanto en `.env` como en `.env.whatsapp`.
  El panel activo también devolvía el bloqueo de configuración del emisor.
- La conversación de prueba estaba en `human`, su WABA coincidía, pero el ID de emisor
  guardado no podía coincidir con el valor vacío de configuración.
- La lista permitía el destinatario de salida indicado por el usuario, pero no la
  identidad entrante distinta. El código anterior comparaba directamente esta última.
- Había cuatro salidas fallidas: un `http_401`, un `http_400` y dos
  `send_policy_blocked`. No había trabajos salientes pendientes ni en curso al diagnosticar.

En la configuración inspeccionada, la primera condición que fallaba era `send_blockers()`
por emisor vacío. Tras corregirlo, también habría fallado la comparación directa del
destinatario. No puede reconstruirse con certeza cuál condición falló en cada intento
histórico: se conservaba únicamente el código genérico y los procesos tienen cachés
independientes. `http_401` no demuestra por sí solo que un token concreto estuviera
expuesto o vencido. El código `131030` lo aportó el usuario desde Graph API Explorer.

## Solución aplicada

`external_contact` conserva exactamente la identidad recibida. El nuevo
`send_recipient` es un dato de enrutamiento validado, no una modificación del contacto.
La asociación privada se limita a la WABA y al número emisor observados para la
conversación de prueba, con el destino que ya figuraba en la lista autorizada.
No se amplió la lista ni se quitaron dígitos de otros números.

La asociación usa este formato en `.env.whatsapp`:

```dotenv
WHATSAPP_RECIPIENT_BINDINGS=[]
```

Cada elemento de la lista tiene `account_id`, `phone_number_id`, `external_contact`
y `send_recipient`. Los dos primeros delimitan dónde es válida la relación. No pegar
tokens ni números privados en documentación/Git. En esta computadora la asociación
del contacto solicitado ya quedó escrita en el archivo privado.

El emisor vacío se recuperó del metadato guardado en la conversación recibida, comprobando
WABA única y formato numérico. Se respaldó el archivo completo en `.local/backups/`
antes de editarlo. Se conservaron la lista autorizada, token, App Secret y Verify Token.
Se dejaron **WHATSAPP_SEND_ENABLED=false** y **WHATSAPP_TOKEN_ROTATED=false**, porque
el usuario indicó que varios tokens temporales aparecieron en capturas.
Los tokens existentes no se usaron para ninguna llamada de salida a Meta.

No se modificaron filas históricas, contactos, reservaciones ni contratos. No se
ejecutó ninguna migración ni reintento de los cuatro mensajes fallidos.

## Diagnósticos seguros

| Código | Significado |
|---|---|
| `send_disabled` | Envíos apagados |
| `token_rotation_required` | Falta confirmar sustitución del token expuesto |
| `access_token_missing` | Token no configurado |
| `sender_config_invalid` | WABA o ID de emisor vacío/no válido |
| `graph_version_invalid` | Formato de versión inválido |
| `recipient_unresolved` | Falta asociación válida o existe ambigüedad |
| `recipient_not_authorized` | Destino fuera de la lista permitida |
| `human_attention_required` | Conversación cerrada/no humana |
| `sender_account_mismatch` | Emisor/cuenta de otra conversación |
| `service_window_expired` | Ventana de texto vencida |
| `template_not_authorized` | Plantilla/idioma no aprobado localmente |
| `send_recipient_changed` | Destino diferente al confirmado/encolado |
| `send_config_changed` | Panel y worker procesan configuraciones diferentes |
| `http_400_meta_131030` | Rechazo HTTP 400 con código numérico Meta 131030 |

Los fallos antiguos mantienen sus códigos originales. No se inventó una causa histórica.
React muestra etiquetas legibles para las categorías internas y el código seguro del
proveedor cuando existe. No se guarda `error.message`, trazas ni contenido privado.

## Configuración y arranque

Los archivos se cargan desde rutas absolutas del repositorio; `.env.whatsapp` prevalece
sobre `.env`, y variables del proceso prevalecen sobre ambos. Panel y worker tienen
cachés independientes: editar un archivo no actualiza procesos ya iniciados.
La revisión de configuración en `/api/messaging/config` debe empezar con el mismo
prefijo que imprime el worker al arrancar. Se compara además la revisión completa
del trabajo al despacharlo. No es una consulta de vigencia del token a Meta.

Para activar una prueba futura:

1. Revocar/sustituir los tokens temporales expuestos y guardar uno nuevo privadamente.
   No compartir capturas del token. La bandera de rotación no revoca nada por sí sola.
2. Autorizar expresamente un mensaje nuevo al contacto de prueba; no reintentar los
   anteriores. Revisar cuenta, emisor y destinatario que muestra la bandeja.
3. Solo entonces establecer ambas banderas de envío/rotación en `true`.
4. Reiniciar **panel y worker** para cargar exactamente los mismos ajustes. Si solo
   cambia token/asociación de salida, no hace falta reiniciar el receptor ni el túnel.
   Si se cambia App Secret, Verify Token, WABA o emisor de recepción, sí requiere
   coordinación del receptor; no cambiar esos valores para resolver un alias de salida.
5. Preparar respuesta → revisar destino → confirmar una sola vez. `accepted` prueba
   aceptación, no entrega: comprobar el teléfono y el callback `delivered`/`read`.

Mientras los envíos están apagados se puede escribir un borrador en React dentro de la
ventana de atención, pero el botón de envío permanece deshabilitado.
La recepción no requiere Access Token de salida; utiliza firma y configuración propias.

## Evidencia y límites

Las pruebas nuevas usan identidades sintéticas equivalentes `521…`/`52…` en PostgreSQL
de pruebas y transporte HTTP simulado. Cubren asociación, ámbito de cuenta/emisor,
no transformación por país, ambigüedad, destino exacto en el proveedor, doble validación,
configuración/token cambiados, ventana/plantillas, UUID idempotente, callbacks y fallos
terminales sin reenvío. Toda la suite de reservas/CRM/autenticación/concurrencia se conserva.

La diferencia observada entre `wa_id` y `to` es evidencia válida para esta asociación
particular, no una regla universal. La respuesta oficial de Cloud API distingue
`contacts[].input` de `contacts[].wa_id`; no puede deducirse de ello el algoritmo interno
de normalización de Meta. [Colección oficial de Meta](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api?entity=request-13382743-2ec98f2a-93d4-465b-a52e-2eb0ee21cf11).

Pendiente: prueba autorizada de salida desde Jordy Studio, recepción en el teléfono y
callback de entrega. El envío directo del usuario en Explorer no verifica este recorrido.
No hay publicación en GitHub ni envío real durante esta corrección.


## Resultado local de esta corrección

- Suite completa: **111 pruebas aprobadas** (21 casos nuevos); compilación React/TypeScript
  correcta y Ruff sin hallazgos. Se conserva la advertencia previa de Starlette/TestClient.
- Panel y worker reiniciados; sus revisiones efectivas de configuración coinciden.
- El receptor activo también retenía configuración incompleta y respondía 503. Se reinició
  únicamente ese proceso, conservando puerto, secretos y túnel. Después se comprobó por
  HTTP local: challenge correcto y rechazo 401 de eventos sin firma. No se abrió otro túnel.
- Cinco mensajes entrantes existentes y los cuatro fallidos conservados; ninguna salida
  pendiente ni en curso al verificar. No se enviaron mensajes ni se reintentaron fallos.
- React mostró el destinatario autorizado correcto y el botón de envío deshabilitado.
- Pendiente exclusivamente la prueba real autorizada con un token nuevo. No se afirma
  entrega ni recepción nueva desde un teléfono durante esta corrección.

Archivos de código modificados: `messaging/config.py`, `service.py`, `worker.py`,
`provider.py`, `api.py`, nuevo `policy.py`, `frontend/src/messages.tsx` y nuevo
`tests/test_messaging_recipients.py`. Documentación: ADR 008, esta guía, `whatsapp.md`
y `whatsapp.env.example`. El ajuste privado de `.env.whatsapp` y su respaldo no entran en Git.
