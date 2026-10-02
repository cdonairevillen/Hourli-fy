# Specs

Contratos compartidos entre backend y frontend.

```text
specs/
├── api/
│   └── openapi.yaml   generado desde FastAPI (no editar a mano)
└── workflows/         flujos de usuario (listas de pasos o diagramas Mermaid)
```

`openapi.yaml` se regenera con:

```bash
cd backend && uv run python scripts/export_openapi.py
```

Se genera desde el código en vez de escribirse a mano (design-first) porque somos un solo autor:
así el contrato nunca se desincroniza de la API real. El diff del archivo en cada commit muestra
qué cambió en la API.
