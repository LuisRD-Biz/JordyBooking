# Reglas del primer entregable

1. Una solicitud nace `pending_approval`; no reserva capacidad.
2. Confirmar requiere credencial administrativa de Jordy, lugar y recursos suficientes.
   Para `event` requiere además referencia de contrato firmado y fecha no futura.
3. Solo `pending_approval → confirmed/cancelled` y
   `confirmed → cancelled/completed` están permitidos. Completar exige haber terminado.
4. Cambiar hora de sesión confirmada revalida y reasigna recursos atómicamente. Si falla,
   conserva el horario anterior. Eventos con contrato requieren un flujo de revisión
   contractual futuro: se rechaza su reprogramación para no invalidar una firma.
5. La duración y necesidades de una solicitud son el snapshot original del paquete.
   Actualizar catálogo no cambia acuerdos previos. Cambiar precio requiere un flujo futuro.
6. Ocupación: `[inicio - preparación, fin + margen posterior)`. Los límites adyacentes
   son compatibles; todos los tiempos entrantes requieren zona/desplazamiento explícito.
7. Una persona no ocupa dos puestos del mismo paquete. El matching busca asignaciones
   viables y puede reasignar candidatos con más de una capacidad. Equipos se modelan
   como unidades individuales con capacidades; incluirlos en el paquete limita su uso.
8. Bloqueos y reservas comparten la misma tabla y restricción de no solapamiento.
9. Cancelar libera ocupaciones conservando su historial. Reprogramar reemplaza las
   ocupaciones; el registro de acción queda auditado. El historial detallado anterior/
   posterior queda pendiente antes de abrir edición contractual e integración externa.
10. Navidad: margen posterior de 30 minutos, no 30 minutos a cada lado. La última sesión
    empieza 20:00, termina 21:30 y libera recursos a las 22:00. La plantilla no bloquea
    domingos ni otros días globalmente: los eventos normales siguen operando.
11. La clave `Idempotency-Key` identifica una creación; repetir el mismo contenido devuelve
    la misma reserva. Reutilizarla para otros datos genera conflicto. Alcance administrativo
    único; cuando haya usuarios deberá incluirse la identidad en su ámbito.
