# Forma de trabajar

Versión para un solo autor del flujo de `ft_trascendance`: mismos prefijos de rama y carpetas,
sin las ramas por equipo (`develop-backend` / `develop-frontend`).

## Carpetas

```
/backend    API (FastAPI)
/frontend   web (React)
/docs       documentación compartida: este archivo, CHANGELOG, guías
/specs      contratos: api/openapi.yaml y workflows/ (flujos de usuario)
```

## Ramas

- `main` — estable, siempre funciona. Solo recibe merges.
  - `feature/<descripcion>` — una tarea o fase del plan (p. ej. `feature/fase-1-auth`). Merge a `main` al terminar.
  - `fix/<descripcion>` — errores encontrados durante el desarrollo.
  - `poc/<descripcion>` — experimentos. **No se mergean**: si funcionan, la idea se rehace en un `feature/*`.
  - `hotfix/<descripcion>` — desde `main`, para un error ya en producción.

## Ciclo de cada tarea

1. Una tarea del plan por sesión, empezando en modo plan.
2. Orden: modelo → endpoint → test con pytest → pantalla.
3. Antes de dar algo por terminado: `uv run pytest`, `npm run lint && npm run build`.
4. Cada commit documenta lo que cambia: entrada en [CHANGELOG.md](CHANGELOG.md) y README del área tocada.
5. Si cambia la API, regenerar el contrato: `cd backend && uv run python scripts/export_openapi.py`.
6. Los commits los revisa y los hace el autor; mensajes claros en español.
