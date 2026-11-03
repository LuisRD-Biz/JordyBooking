# Flujo de contribución

Usamos ramas cortas y Pull Requests hacia `main`; no necesitamos `develop`.
`feature/*` añade funcionalidades, `fix/*` corrige errores y `hotfix/*` atiende
incidentes de producción con las mismas comprobaciones y revisión.

1. Actualizar referencias (`git fetch origin`) y crear la rama desde `origin/main`.
2. Implementar únicamente el cambio previsto. No guardar credenciales ni datos reales.
3. Ejecutar las comprobaciones del componente descritas en [CI/CD](docs/ci-cd.md).
4. Revisar diff, seguridad y documentación; crear commits claros y publicar la rama.
5. Abrir PR hacia `main`, describir resultados y revisar CI antes de solicitar aprobación.
6. El propietario autoriza e integra; los agentes no fusionan sin autorización.
7. Publicar solo el componente afectado. Cloudflare producción: únicamente `main`
   y `website/dist`. CRM/API/base de datos siguen locales y privados en ejecución.

Ejemplos: `feature/ai-assistant`, `feature/client-portal`, `feature/payments`.
La IA deberá usar las validaciones del dominio: nunca cambiar reservas o pagos
directamente ni saltarse aprobación, contratos, permisos o idempotencia.

Durante la integración inicial: primero PR `feature/project-baseline` → `main`;
después retargetear PR `feature/website` a `main`. Usar merge commit para esta
base histórica, conservando ancestros compartidos; no squash/rebase de esa base.
No borrar ramas históricas ni el stash existente. Las ramas ya publicadas no
se reescriben. `whatsapp-cloud-api` queda como antecedente, no como producción.
