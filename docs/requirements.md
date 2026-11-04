# Requisitos y alcance

Jordy Flores Fotografía necesita gestionar clientes, paquetes, disponibilidad y
contrataciones, conservando la decisión final de Jordy. El primer entregable es una
API administrativa verificable de disponibilidad y reservaciones; no es todavía
el MVP web completo ni un sistema listo para producción.

## Confirmado con el propietario

- Jordy es uno de los dos fotógrafos. Los dos videógrafos, dos asistentes y dos
  operadores de dron son personas distintas. Los asistentes pueden cubrir segunda
  cámara: dos capacidades asociadas a una única identidad por persona.
- Sesiones: aprobación explícita de Jordy y lugar acordado; sin contrato obligatorio.
- Bodas/XV: contrato firmado y aprobación explícita antes de confirmar.
- Varias personas pueden preguntar por una fecha. Las solicitudes pendientes no
  ocupan recursos; gana la confirmación que consigue recursos transaccionalmente.
- No hay máximo fijo de eventos por día. Cada paquete declara sus necesidades.
- Navidad: reservas desde septiembre, sets instalados en septiembre, sesiones entre
  semana en octubre y noviembre, entregas en diciembre. Seis inicios diarios:
  10, 12, 14, 16, 18 y 20. Sesión de 90 minutos y 30 posteriores de margen.
- El proveedor real del calendario no está confirmado; iCloud es una posibilidad.

## Implementado en este entregable

Clientes; recursos y capacidades; paquetes configurables; requisitos normalizados;
snapshot comercial; consultas de disponibilidad; solicitudes idempotentes;
registro administrativo de contrato; aprobación; cancelación; finalización;
reprogramación de sesiones y solicitudes sin contrato; bloqueos; asignaciones;
auditoría; outbox y worker explícitamente simulado; plantilla de horarios navideños.

## Límites explícitos

La API solo tiene acceso administrativo mediante una clave secreta. No hay usuarios
individuales, portal de clientes, panel React, firma electrónica ni carga de archivos.
El registro de contrato es una declaración administrativa de firma existente.
No se envían mensajes ni se sincroniza un calendario real. El worker marca operaciones
como `simulated`, nunca como enviadas o sincronizadas. No hay recordatorios aún.
No se han creado trabajadores ficticios ni precios de negocio.

La plantilla navideña consulta los seis horarios y comparte disponibilidad con todos
los eventos normales. No impone una campaña a todo paquete ni crea apartados: falta
definir qué bloquea un apartado, si exige anticipo y cuándo vence. La apertura comercial
en septiembre y entregas de diciembre están documentadas, no automatizadas.

## Pendiente de negocio

Nombres/capacidades definitivos, paquetes/precios, equipo limitante y sets compartidos,
tiempos de traslado, política de apartados, reprogramación contractual, autenticación
de clientes, zona horaria de operación (provisional America/Mexico_City) y calendario real.
