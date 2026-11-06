# Guía de documentación

| Para trabajar en… | Leer |
| --- | --- |
| Estructura del sistema y cambios que requieren otro PR | [Mapa, auditoría y decisiones](architecture.md) |
| Reservas, contratos, ocupaciones y esquema PostgreSQL | [Reglas de negocio](business-rules.md) y [modelo de datos](database.md). La secuencia completa de cambios está en `migrations/versions/`. |
| Panel Windows, contactos, oportunidades y archivos privados | [Arranque del panel](panel.md) y [CRM y documentos](crm-documents.md) |
| Consultas administrativas por Telegram | [Comandos, permisos y prueba local](telegram.md) |
| Recepción, bandeja y envío manual por WhatsApp | [Operación](whatsapp.md) y [plantilla de configuración](whatsapp.env.example) |
| Señales, propuestas de fechas y resúmenes | [Seguimiento comercial](commercial-followup.md) |
| Página pública, compilación y contribuciones | [Web pública](website-deployment.md), [CI](ci-cd.md) y [flujo de PR](../CONTRIBUTING.md) |

## Antecedentes y alcance

- [Requisitos originales](requirements.md) y [roadmap por entregables](roadmap.md) recogen decisiones del propietario y trabajo propuesto.
- [Estado por sesión](project-status.md) y [traspaso entre sesiones](NEXT_SESSION.md) describen máquinas, procesos y ramas en las fechas indicadas. Para arrancar hoy, usar las guías de operación anteriores.
- [Integración Git inicial](git-integration.md), [curación del portafolio](portfolio-curation.md) y [revisión web V2](website-v2.md) conservan los motivos y las verificaciones de cambios anteriores.
- [Verificación CRM](verification-crm.md), [verificación WhatsApp](verification-whatsapp.md) y [corrección de destinatarios](whatsapp-routing-fix.md) documentan pruebas concretas. Para saber qué pasó en otro commit, consultar los checks de ese PR.
