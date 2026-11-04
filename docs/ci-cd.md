# Integración y publicación controlada

## Entornos

- Local: panel/backend/PostgreSQL locales y vista previa de la web.
- Integración: GitHub Actions con PostgreSQL efímero, credenciales ficticias y
  esquemas de prueba. PR revisable sin despliegue ni acceso a datos reales.
- Producción: solo página pública en `jordyflores.com`, desde `main` tras aprobación.
  `admin.jordyflores.com` y `api.jordyflores.com` son planes futuros, no servicios
  configurados. FastAPI no se convierte automáticamente en un Worker.

## Comprobaciones

El workflow `Backend checks` mantiene la compilación del administrador y toda la
suite existente. PostgreSQL 18 es un servicio desechable de GitHub Actions.
Ruff verifica estilo; Pytest cubre autenticación, reservas, contratos, mensajería,
idempotencia y migraciones. `tests/conftest.py` exige sufijo `_test` y crea un esquema
aislado. No establecer `TEST_DATABASE_URL` a la base operativa.

```powershell
uv sync --locked
uv run ruff check backend scripts tests migrations
uv run ruff format --check backend scripts tests migrations
uv run pytest -q
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
python scripts/check_repository_secrets.py --history
```

Pytest necesita `TEST_DATABASE_URL` de una instancia de pruebas para las pruebas
de integración; sin ella hay pruebas omitidas, no una validación completa.
La auditoría de secretos detecta patrones conocidos y archivos privados comunes;
no sustituye revisión humana ni garantiza detectar cualquier credencial o dato personal.

La web tendrá su workflow separado con Node/pnpm declarados, TypeScript, build y
auditoría estática. Ningún workflow de Actions despliega ni recibe tokens de producción.
Los checks se ejecutan en PR y pushes a main; no usamos `pull_request_target` ni
runners locales. Permisos del token: solo lectura. No se reduce la suite para pasar CI.

## Protección propuesta de main (pendiente de aprobación)

Repositorio verificado público; la conexión tiene permisos de administrador.
GitHub permite protección de ramas en repositorios públicos con Free. No se
modificaron reglas ni permisos. Configurar después de ver los primeros checks:

- Exigir PR, conversaciones resueltas y checks `frontend`, `test`, `security`
  y `Website checks` cuando este último workflow esté integrado.
- Bloquear force push y eliminación; no exigir historial lineal durante la integración
  inicial, que conserva los commits originales mediante merge commit.
- Con un solo autor, no exigir una aprobación independiente imposible de emitir.
  Mantener revisión humana del diff y autorización de integración. Cuando haya un
  segundo revisor, activar una aprobación y descartar aprobaciones obsoletas.
- Conservar recuperación administrativa documentada: propietario → Settings →
  Branches/Rules → editar regla ante un check obsoleto, registrar motivo en PR y
  restaurar la protección. No aplicar bloqueo total al único administrador.

La aplicación de estas reglas es una configuración crítica pendiente de aprobación,
no un bloqueo para crear ramas, commits y PR. El acceso de administrador no confirma
que las reglas estén activadas; revisar la pantalla antes de configurar.

Fuentes: [protección de ramas](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[ramas de Cloudflare Builds](https://developers.cloudflare.com/workers/ci-cd/builds/build-branches/),
[filtros de archivos](https://developers.cloudflare.com/workers/ci-cd/builds/build-watch-paths/).
