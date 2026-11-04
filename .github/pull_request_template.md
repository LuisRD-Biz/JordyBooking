## Cambio y motivo

Describe el comportamiento antes y después y el componente afectado.

## Verificación

- [ ] Pruebas aplicables y CI revisados (indicar resultados reales).
- [ ] Sin credenciales, datos de clientes ni archivos privados.
- [ ] Migraciones y compatibilidad revisadas, si corresponde.
- [ ] Documentación y recuperación actualizadas.

## Publicación y riesgos

Indicar dependencias entre PR, riesgos y recuperación. Integrar no autoriza
publicar el CRM/backend. Solo `website/` en `main` podrá activar producción,
cuando la conexión de Cloudflare haya sido aprobada y configurada.
