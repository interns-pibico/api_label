# api_label — Documentación

Sistema de generación de etiquetas de producto conforme a normativa legal.

## Descripción General

`api_label` es una aplicación FastAPI especializada en la generación automática de etiquetas de producto conforme a normativas regulatorias. Soporta múltiples categorías de productos (nutrición, cosmética, ferretería, electrónica) con campos obligatorios definidos por JSON schema.

## Características

- **Generación de etiquetas PDF**: Usando ReportLab para renderizado de alta calidad
- **Soporte multiidioma**: Español (ES) e Inglés (EN) con Babel
- **Integración con códigos de barras**: Cliente async a `api.pibico.es/barcode`
- **Tareas asincrónicas**: Celery para procesamiento en background
- **Mobile-first UI**: Interfaz web responsive
- **Rate limiting**: Slowapi para protección contra abuso

## Estructura del Proyecto

```
api_label/
├── src/
│   ├── core/           # Configuración, seguridad, dependencias
│   ├── db/             # Sesiones, repositorios
│   ├── models/         # Modelos SQLAlchemy
│   ├── schemas/        # Esquemas Pydantic
│   ├── services/
│   │   ├── label_engine/      # Lógica de generación
│   │   └── integrations/      # Integraciones externas
│   ├── api/v1/         # Endpoints
│   └── workers/        # Celery tasks
├── frontend/           # Templates HTML + static
├── alembic/           # Migraciones BD
├── docs/              # Documentación (este archivo)
└── locales/           # Archivos de traducción i18n
```

## Stack Tecnológico

- **FastAPI**: Framework web async
- **SQLAlchemy**: ORM async con asyncpg
- **PostgreSQL**: Base de datos principal (DB `api_label_psql`)
- **Redis**: Cache y broker de Celery (DB 3)
- **ReportLab**: Generación de PDF
- **Babel**: Internacionalización
- **httpx**: Cliente HTTP async
- **Celery**: Tareas en background
- **slowapi**: Rate limiting

## Desarrollo

Este documento forma parte del scaffolding inicial (Phase 1). Consulta `CLAUDE.md` en el raíz del proyecto para patrones de desarrollo, convenciones y guías de contribución.

## Próximos Pasos

- Phase 2: Implementar modelos ORM, autenticación, CRUD base
- Phase 3: Endpoints específicos de generación de etiquetas
- Phase 4: Integración con barcode API
- Phase 5: Frontend UI mobile-first
