# Backend — Registro de horas

FastAPI + SQLModel + Alembic sobre PostgreSQL, Python 3.12 gestionado con [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env                      # configuración local
uv run fastapi dev app/main.py            # API en http://localhost:8000 (Swagger en /docs)
uv run pytest                             # tests
uv run ruff check .                       # lint
uv run python -m alembic upgrade head     # aplicar migraciones (necesita el Postgres de docker compose)
uv run python scripts/export_openapi.py   # regenerar specs/api/openapi.yaml
```

> En este equipo Smart App Control de Windows bloquea `alembic.exe`; por eso se usa
> `python -m alembic`, que es equivalente y funciona en cualquier sitio.

## Estructura

```
app/
├── main.py          crea la app, CORS y monta los routers bajo /api
├── core/
│   ├── config.py    Settings (pydantic-settings): lee la configuración de .env
│   ├── security.py  JWT de sesión (cookie) y tokens de invitación (se guarda su hash)
│   └── google.py    verificación del ID token de Google
├── db.py            engine de SQLAlchemy + get_session() (dependencia por petición)
├── schemas.py       cuerpos de petición y respuesta (Pydantic)
├── api/             un módulo por grupo de rutas (health, auth, workspaces, invitations, catalog)
│   └── deps.py      dependencias: usuario actual, MemberAccess y OwnerAccess de un espacio
├── services/        reglas que usan varias rutas (límite de espacios, estado de un link)
└── models/          tablas SQLModel; se importan en models/__init__.py para que Alembic las vea
alembic/             migraciones (env.py toma la URL y el metadata de la app)
scripts/             utilidades (export_openapi.py)
tests/               pytest, un archivo por grupo de rutas (conftest.py: BD de pruebas y login falso)
```

## Endpoints

"Dueño" = dueño del espacio; "Miembro" = cualquier miembro activo. Si no eres miembro de un
espacio, sus rutas responden 404 (no 403) para no revelar que existe.

| Método | Ruta | Uso | Rol |
| ------ | ---- | --- | --- |
| GET | `/api/health` | Comprueba que la API responde | Público |
| POST | `/api/auth/google` | Verifica el ID token de Google, crea el usuario la primera vez y pone la cookie | Público |
| POST | `/api/auth/logout` | Borra la cookie | Todos |
| GET | `/api/auth/me` | Usuario de la sesión (401 si no hay) | Todos |
| GET | `/api/workspaces` | Mis espacios (propios e invitados) | Todos |
| POST | `/api/workspaces` | Crear espacio (máx. 5 propios sin archivar) | Todos |
| PATCH | `/api/workspaces/{wid}` | Renombrar, archivar/desarchivar, transferir propiedad | Dueño |
| GET | `/api/workspaces/{wid}/members` | Miembros activos | Miembro |
| DELETE | `/api/workspaces/{wid}/members/{uid}` | Salir (uid = yo) o expulsar (dueño) | Miembro / Dueño |
| GET | `/api/workspaces/{wid}/invitations` | Links del espacio y su estado | Dueño |
| POST | `/api/workspaces/{wid}/invitations` | Crear link (10 días, `max_uses` opcional); el token solo sale aquí | Dueño |
| DELETE | `/api/workspaces/{wid}/invitations/{id}` | Revocar un link | Dueño |
| GET | `/api/invitations/{token}` | A qué espacio invita y si sigue valiendo | Público |
| POST | `/api/invitations/{token}/accept` | Unirse al espacio | Todos |
| GET | `/api/workspaces/{wid}/projects?include_archived=` | Proyectos (por defecto, solo activos) | Miembro |
| POST | `/api/workspaces/{wid}/projects` | Crear proyecto (`name`, `color` #RRGGBB) | Dueño |
| PATCH | `/api/workspaces/{wid}/projects/{id}` | Renombrar, cambiar color, archivar/desarchivar | Dueño |
| GET | `/api/workspaces/{wid}/categories?include_archived=` | Labels con sus sublabels anidadas | Miembro |
| POST | `/api/workspaces/{wid}/categories` | Crear label | Dueño |
| PATCH | `/api/workspaces/{wid}/categories/{id}` | Renombrar, archivar/desarchivar label | Dueño |
| POST | `/api/workspaces/{wid}/categories/{cid}/subcategories` | Crear sublabel | Dueño |
| PATCH | `/api/workspaces/{wid}/categories/{cid}/subcategories/{sid}` | Renombrar, archivar/desarchivar sublabel | Dueño |

En el código las labels son `categories` (tipologías) y las sublabels `subcategories`.
Las escrituras en un espacio archivado devuelven 409; un nombre repetido, también 409.

El contrato completo está en [`specs/api/openapi.yaml`](../specs/api/openapi.yaml).

## Decisiones

- **pydantic-settings**: un único objeto `settings` tipado; los valores salen de `.env` (nunca del repo).
- **psycopg 3** como driver (`postgresql+psycopg://`): funciona igual con el Postgres local y con Supabase.
- **`pool_pre_ping`**: descarta conexiones cortadas por Supabase o Cloud Run antes de usarlas.
- **Alembic lee la URL de `settings`** y no de `alembic.ini`, para no duplicar credenciales.
  La plantilla de migraciones importa `sqlmodel` porque los modelos usan sus tipos (`AutoString`).
- **httpx2** en dev: Starlette marca `httpx` como obsoleto para `TestClient`.
- **Login con Google, sesión propia**: Google solo nos dice quién eres (ID token); a partir de ahí
  la sesión es un JWT nuestro en una cookie `httpOnly` (JavaScript no puede leerla).
- **El usuario se identifica por `google_sub`**, no por email: el email de una cuenta de Google puede cambiar.
- **Tokens de invitación**: aleatorios de 256 bits; en la BD solo su SHA-256. Basta SHA-256 (y no
  argon2 como con contraseñas) porque un token aleatorio tan largo no se puede adivinar por fuerza bruta.
- **Límites con `SELECT ... FOR UPDATE`**: crear espacio bloquea la fila del usuario, y aceptar un
  link bloquea la invitación. Así dos peticiones simultáneas no se saltan el límite de 5 ni `max_uses`.
- **Nada se borra**: salir/expulsar rellena `memberships.removed_at`; archivar marca `archived`.
- **Nombres únicos los decide la BD**: el catálogo no comprueba con un SELECT antes de insertar
  (dos peticiones a la vez pasarían las dos); se captura el `IntegrityError` de la restricción
  única y se devuelve 409.
- **Tests sobre Postgres real** (BD `clockify_test`, se crea sola): cada test corre en una
  transacción que se deshace al acabar, y el login de Google se sustituye por uno falso.
