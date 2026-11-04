# Integración inicial — 3 de noviembre de 2026

## Auditoría inicial

Árbol de trabajo limpio. `origin` apunta a `LuisRD-Biz/JordyBooking`, público.
Referencias actualizadas desde GitHub antes de trabajar:

| Rama local/remota | Commit | Contenido |
| --- | --- | --- |
| main | 07d21c0 | Inicial |
| booking-mvp | 6c06fae | Motor de reservas y API |
| crm-documents | d21bf2f | CRM, documentos y panel |
| whatsapp-cloud-api | 543b1dd | Aplicación avanzada + página pública |

Historial lineal: main → MVP → CRM → WhatsApp/comercial (`0d9d1e2`) → web
(`543b1dd`). La web ya estaba guardada y publicada al iniciar esta reorganización.
Se conserva también el stash previo de GitHub Desktop. No se elimina ni reescribe nada.

## Dos entregas para revisión

1. `feature/project-baseline`, creada desde `0d9d1e2`, integra la aplicación y sus
   ancestros hacia main. Añade controles CI, auditoría de secretos y procedimiento
   de contribución. Ajuste de formato Ruff sin cambio funcional. Se actualiza una
   prueba obsoleta de migraciones: verifica rollback de revisiones reversibles y
   rechazo del downgrade comercial, conservando una fila y la revisión de Alembic.
   No se modifican migraciones ni servicios de WhatsApp.
2. `feature/website`, creada desde `543b1dd`, conserva exactamente el commit original
   de la página y añade su CI y preparación para producción desde main. Inicialmente
   PR dependiente contra la rama base para mostrar solo cambios web. Después de
   integrar la base mediante merge commit, cambiar el destino de este PR a main.
   No fusionarlo en la rama temporal. Revalidar CI y revisión antes de integrar.

No se hacen merges ni se despliega producción en esta tarea. Evitar squash de la
base inicial: perdería los ancestros comunes del PR web y duplicaría el diff.

## Evidencia local

- Auditoría de 745 blobs históricos: cero patrones de credenciales detectados.
- Ruff check y format correctos (49 archivos).
- Pytest con PostgreSQL 18 nuevo, puerto 55439, base `jordy_audit_test`: **136 passed**.
  Un aviso de deprecación de Starlette/httpx; no fallo funcional.
- Compilación TypeScript/Vite del administrador correcta.
- CI remoto y web se registran en los PR; un resultado local no sustituye GitHub Actions.

El servicio de prueba es exclusivo de esta tarea y se detiene al finalizar.
No se leen ni alteran datos de la base del estudio. Ninguna credencial real se imprime.
La inspección cubre archivos versionados y patrones conocidos; no certifica seguridad
para publicar el backend. La autenticación actual de clave compartida es local y
requiere endurecimiento, cuentas/permisos y operación revisada antes de exponerlo.

Las reglas de protección no se aplican sin aprobación adicional. Propuesta y
recuperación en [CI/CD](ci-cd.md); flujo diario en [CONTRIBUTING](../CONTRIBUTING.md).
