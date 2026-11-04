# Fase 5 — seguimiento comercial y agenda flexible

## Uso

1. En **Mensajes**, abre una conversación, selecciona **Señales** y pulsa
   **Analizar mensajes guardados**.
   Cada señal conserva el mensaje original, fragmento, certeza, contexto y revisión.
   Marcar revisado o descartar no confirma operaciones.
2. Vincula primero la ficha correcta del cliente con el control existente. Las
   oportunidades de ese contacto aparecen en Mensajes; se crean en **Oportunidades**.
3. En **Notas**, registra llamadas, audios que escuchaste o acuerdos en persona.
   Se guardan como notas manuales de Jordy, nunca como transcripciones automáticas.
4. Abre la pestaña **Fechas**. Basta un día:
   hora, alternativas, tentativa y vínculo con oportunidad son opcionales.
   Una reprogramación propuesta sí requiere identificar la reserva del mismo cliente.
5. En **Agenda** y **Reservaciones** aparecen las propuestas separadas de la ocupación.
   Para ejecutar un cambio usa el flujo existente **Reserva → Reprogramar**. Revisar
   una propuesta no ejecuta ese cambio ni modifica contratos.
6. En **Resumen diario**, selecciona el día y pulsa **Generar / actualizar resumen**.
   Los enlaces abren la conversación original y cada observación puede revisarse.
   Regenera un resumen guardado para incorporar mensajes tardíos o revisiones nuevas.

Las pestañas **Mensajes / Señales / Notas / Fechas** mantienen los borradores al
cambiar de área dentro de la misma conversación. Cambiar de conversación o recargar
el navegador no guarda borradores. En pantallas pequeñas, **← Conversaciones**
regresa a la lista. **Ver Resumen diario** está en la cabecera de la bandeja.

**Ver mensaje original** abre el texto almacenado de la señal, incluso si está fuera
de la página reciente del historial. La ruta comprueba que sea de esa conversación.
No se descarga contenido multimedia.

## Cuándo se analiza

La llegada de un WhatsApp **no dispara el análisis comercial**. El worker existente
almacena mensajes y procesa únicamente envíos manuales confirmados.

El análisis ocurre al pulsar **Analizar mensajes guardados**, al generar/regenerar
un resumen, o al recuperar resúmenes con el horario optativo de fase 5. Consultar un
resumen guardado o abrir una conversación no ejecuta un nuevo análisis. El cierre
del 20/10 no añadió automatizaciones.

## Reglas y límites

- Solo texto almacenado: sin IA, embeddings, descargas de audio ni llamadas externas.
- Los mensajes salientes fallidos, pendientes o inciertos no se analizan como acuerdos
  comunicados. La aceptación por Meta tampoco demuestra entrega; los estados originales
  siguen visibles en Mensajes.
- Preguntas, negaciones, hipótesis y correcciones se conservan como contexto.
  «¿Entonces confirmamos la boda?» es un posible acuerdo en forma de pregunta.
- «15 de mayo» no tiene año: se conserva ambiguo. Fechas numéricas como 03/04/2027
  también requieren revisión. Fechas completas en español o ISO se validan.
- Hoy, mañana y pasado mañana usan la fecha del mensaje en la zona del estudio.
  «Próximo sábado» se marca ambiguo por sus dos interpretaciones habituales.
- Las reglas léxicas no comprenden sarcasmo, todas las negaciones compuestas ni
  referencias entre mensajes. Ninguna señal es prueba de contratación.
- La clave única mensaje + señal impide duplicados. Reanalizar conserva revisiones.
  Las fechas anteriores no se sobrescriben; las propuestas son registros adicionales.
- La certeza explícita describe el texto, no la validez de un acuerdo.
- La cuenta de nuevos interesados usa identidades de conversación, no deduce que dos
  números pertenezcan a la misma persona. Los servicios/temas cuentan menciones
  entrantes, excluyen negaciones y señales descartadas.
- «Sin respuesta al cierre» significa que no hubo una respuesta saliente aceptada,
  enviada, entregada o leída posterior al último mensaje entrante de ese día.
  No equivale a abandono, no incluye conversaciones inactivas de días anteriores
  y no impone un plazo comercial inventado.
- Los cambios registrados proceden de auditoría; las confirmaciones de Jordy son
  acciones `booking.confirmed` y `booking.rescheduled` del administrador existente.
  Una nota manual o una señal revisada no se incluye como reserva confirmada.
- El reporte guardado es una fotografía del día y puede regenerarse sin duplicados.
  Su hora de generación cambia; con fuentes iguales, el contenido se reproduce.

## Ejecución nocturna en Windows

No se eligió una hora por defecto. La configuración se guarda en PostgreSQL, sin
cambiar `.env`: hora local opcional y primer día a recuperar. A la hora seleccionada
se genera el **día anterior completo**. Antes de esa hora se recuperan días previos.

El servidor del panel comprueba lo pendiente al arrancar y cada minuto. Procesa
un día por comprobación, con bloqueo transaccional para evitar ejecuciones simultáneas.
Si Windows o el panel están apagados, no hay ejecución; se recupera al volver.
La hora vacía desactiva este proceso. La ejecución manual permanece disponible.
No se instala una tarea de Windows ni se envían reportes por WhatsApp.

El error `SUMMARY_RECOVERY_FAILED` indica recuperación pendiente. Se conserva el
último día completado y se reintenta. `STORAGE_UNAVAILABLE` es un error seguro de
persistencia; no se muestra SQL, credenciales ni trazas al usuario.

## Persistencia y autorización

Migración aditiva `9c51e760ab12`: `commercial_signals`, `commercial_notes`,
`commercial_plans`, `daily_summaries`, `summary_schedule`. No cambia tablas
operativas. Reversión destructiva deshabilitada para conservar el historial.

Las rutas `/api/commercial` reutilizan autenticación administrativa y protección de
origen existente. Las revisiones validan la conversación y las propuestas comprueban
que oportunidad/reserva pertenezcan al cliente vinculado. No hay endpoints de envío
ni aprobación operativa en este módulo. La instalación sigue siendo de un estudio,
con una identidad administrativa; no hay cuentas independientes por empleado.

## Decisiones comerciales pendientes

- Política explícita para apartados, anticipo y liberación/vencimiento.
- Hora nocturna y fecha de inicio de recuperación que prefiera Jordy.
- Criterio humano de seguimiento de conversaciones sin respuesta.
- Definir política para cambios que afecten a un contrato firmado.

Hasta definirlas, el apartado queda como **por revisar, sin bloquear recursos**.
No se automatizan pagos, caducidades, confirmaciones, cancelaciones ni cambios.
