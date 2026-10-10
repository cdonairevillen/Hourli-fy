# Backend — Registro de horas

FastAPI + SQLModel + Alembic sobre PostgreSQL, Python 3.12 gestionado con [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env                      # configuración local (DATABASE_URL usa 127.0.0.1, no localhost)
uv run fastapi dev app/main.py            # API en http://localhost:8000 (Swagger en /docs)
uv run python -m pytest                   # tests (pytest.exe lo bloquea a veces Windows)
uv run ruff check .                       # lint
uv run python -m alembic upgrade head     # aplicar migraciones (necesita el Postgres de docker compose)
uv run python scripts/export_openapi.py   # regenerar specs/api/openapi.yaml
```

> En este equipo Smart App Control de Windows bloquea a veces `alembic.exe`, `pytest.exe` y
> `uvicorn.exe`; por eso se usan con `python -m …`, que es equivalente y funciona en cualquier sitio.

## Estructura

```
app/
├── main.py          crea la app, CORS y monta los routers bajo /api
├── core/
│   ├── config.py    Settings (pydantic-settings): lee la configuración de .env
│   ├── security.py  JWT de sesión (cookie) y tokens de invitación (se guarda su hash)
│   ├── google.py    verificación del ID token de Google
│   └── passwords.py hash y verificación de contraseñas (argon2)
├── admin.py         panel /admin (SQLAdmin) y su control de acceso (ADMIN_EMAILS)
├── db.py            engine de SQLAlchemy + get_session() (dependencia por petición)
├── schemas.py       cuerpos de petición y respuesta (Pydantic)
├── api/             un módulo por grupo de rutas (health, auth, workspaces, invitations, catalog, entries, reports)
│   └── deps.py      dependencias: usuario actual, MemberAccess y OwnerAccess de un espacio
├── services/        reglas que usan varias rutas (espacios, registros, panel, cuentas, contraseñas,
│                    emails, freno a la fuerza bruta)
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
| POST | `/api/auth/register` | Crear cuenta con email y contraseña (mín. 8); abre sesión. 409 si el email ya existe | Público |
| POST | `/api/auth/login` | Entrar con email y contraseña. 401 genérico; 429 tras 10 intentos en 15 min | Público |
| POST | `/api/auth/password/forgot` | Envía el link de recuperación (siempre 202; máx. 3 por hora) | Público |
| POST | `/api/auth/password/reset` | Contraseña nueva con el token del link; abre sesión. 410 si caducó o se usó | Público |
| POST | `/api/auth/password` | Cambiar la contraseña (pide la actual) o ponerla si la cuenta es de Google | Todos |
| POST | `/api/auth/google` | Verifica el ID token de Google; crea la cuenta o la une a una con el mismo email (borrando su contraseña) | Público |
| POST | `/api/auth/logout` | Borra la cookie | Todos |
| GET | `/api/auth/me` | Usuario de la sesión (401 si no hay) | Todos |
| DELETE | `/api/auth/me` | Eliminar mi cuenta: anonimiza mis datos (409 si soy dueño de espacios activos) | Todos |
| GET | `/api/workspaces` | Mis espacios (propios e invitados) | Todos |
| POST | `/api/workspaces` | Crear espacio (máx. 5 propios sin archivar) | Todos |
| PATCH | `/api/workspaces/{wid}` | Renombrar, archivar/desarchivar, transferir propiedad | Dueño |
| DELETE | `/api/workspaces/{wid}` | Borrar el espacio con todo lo suyo (409 si tiene horas: archivarlo) | Dueño |
| GET | `/api/workspaces/{wid}/members` | Miembros activos, con su acceso (`all_projects`, `project_ids`) | Miembro |
| PUT | `/api/workspaces/{wid}/members/{uid}/access` | Permisos: `{all_projects, project_ids}` | Dueño |
| DELETE | `/api/workspaces/{wid}/members/{uid}` | Salir (uid = yo) o expulsar (dueño) | Miembro / Dueño |
| GET | `/api/workspaces/{wid}/invitations` | Links del espacio y su estado | Dueño |
| POST | `/api/workspaces/{wid}/invitations` | Crear link (10 días, `max_uses` y `project_id` opcionales: sin proyecto = al espacio entero); el token solo sale aquí | Dueño |
| DELETE | `/api/workspaces/{wid}/invitations/{id}` | Revocar un link | Dueño |
| GET | `/api/invitations/{token}` | A qué espacio invita y si sigue valiendo | Público |
| POST | `/api/invitations/{token}/accept` | Unirse al espacio | Todos |
| GET | `/api/workspaces/{wid}/projects?include_archived=` | Proyectos (por defecto, solo activos) | Miembro |
| POST | `/api/workspaces/{wid}/projects` | Crear proyecto (`name`, `color` #RRGGBB) | Dueño |
| PATCH | `/api/workspaces/{wid}/projects/{id}` | Renombrar, cambiar color, archivar/desarchivar | Dueño |
| DELETE | `/api/workspaces/{wid}/projects/{id}` | Borrar el proyecto (409 si tiene horas: archivarlo) | Dueño |
| GET | `/api/workspaces/{wid}/categories?include_archived=` | Labels con sus sublabels anidadas | Miembro |
| POST | `/api/workspaces/{wid}/categories` | Crear label | Dueño |
| PATCH | `/api/workspaces/{wid}/categories/{id}` | Renombrar, archivar/desarchivar label | Dueño |
| POST | `/api/workspaces/{wid}/categories/{cid}/subcategories` | Crear sublabel | Dueño |
| PATCH | `/api/workspaces/{wid}/categories/{cid}/subcategories/{sid}` | Renombrar, archivar/desarchivar sublabel | Dueño |

| GET | `/api/workspaces/{wid}/entries?from=&to=&project_id=` | Mis registros (días en hora de España, ambos incluidos) | Miembro |
| POST | `/api/workspaces/{wid}/entries` | Registro manual (inicio y fin con zona horaria) | Miembro |
| PATCH | `/api/entries/{id}` | Editar un registro propio | Propio |
| DELETE | `/api/entries/{id}` | Borrar un registro propio (o descartar el cronómetro) | Propio |
| POST | `/api/workspaces/{wid}/timer/start` | Arrancar el cronómetro (para el anterior si lo hay) | Miembro |
| POST | `/api/timer/stop` | Parar mi cronómetro, esté en el espacio que esté | Todos |
| GET | `/api/timer/current` | Mi cronómetro en marcha, o null | Todos |
| GET | `/api/workspaces/{wid}/reports/summary` | Panel: total y desglose por persona, proyecto, label y día | Dueño |
| GET | `/api/workspaces/{wid}/reports/entries?limit=&offset=` | Panel: tareas que cumplen los filtros, paginadas | Dueño |

Filtros del panel (comunes a las dos rutas): `period=AAAA-MM-A|B` **o** `from` + `to` (por defecto,
la quincena actual), `user_id`, `project_id`, `category_id`, `subcategory_id` y `q` (texto en el
título, sin distinguir mayúsculas).

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
- **Sesión propia**: se entre con contraseña o con Google, la sesión es un JWT nuestro en una cookie
  `httpOnly` (JavaScript no puede leerla).
- **Contraseñas con argon2** (`pwdlib`): lento a propósito. Si el email no existe se verifica
  contra un hash ficticio, para que la respuesta tarde lo mismo y no delate qué emails tienen cuenta.
- **Sin confirmar el email al registrarse**: al unir con Google una cuenta con contraseña se borra
  la contraseña, por si la puso otra persona que registró ese email antes.
- **Freno a la fuerza bruta en memoria** (`services/rate_limit.py`): suficiente con una instancia.
  Detrás de un proxy (Cloud Run) habrá que leer la IP real de `X-Forwarded-For`.
- **Panel /admin con SQLAdmin**: su cookie se llama `admin_session` para no pisar la `session` de
  la app, y los tests lo apuntan a la BD de pruebas con `admin_session_maker.configure(...)`.
- **El usuario se identifica por `google_sub`**, no por email: el email de una cuenta de Google puede cambiar.
- **Tokens de invitación**: aleatorios de 256 bits; en la BD solo su SHA-256. Basta SHA-256 (y no
  argon2 como con contraseñas) porque un token aleatorio tan largo no se puede adivinar por fuerza bruta.
- **Límites con `SELECT ... FOR UPDATE`**: crear espacio bloquea la fila del usuario, y aceptar un
  link bloquea la invitación. Así dos peticiones simultáneas no se saltan el límite de 5 ni `max_uses`.
- **Nada con horas se borra**: salir/expulsar rellena `memberships.removed_at`; archivar marca
  `archived`. Un espacio o proyecto sin ninguna tarea sí se borra (`DELETE`), en orden de claves
  foráneas: invitaciones y accesos, labels, proyectos, membresías y, al final, el espacio.
- **Acceso por proyecto** (`services/access.py`): `memberships.all_projects` o filas en
  `project_members`. Todas las rutas que tocan un proyecto o sus tareas usan las mismas funciones;
  un proyecto sin acceso se trata como inexistente (404 en la URL, 422 si llega en el cuerpo).
- **Nombres únicos los decide la BD**: el catálogo no comprueba con un SELECT antes de insertar
  (dos peticiones a la vez pasarían las dos); se captura el `IntegrityError` de la restricción
  única y se devuelve 409.
- **Reglas de tiempo en la BD**: `time_entries` tiene `CHECK` (fin > inicio, máx. 24 h), un índice
  único parcial (un cronómetro en marcha por persona) y una restricción de exclusión con
  `btree_gist` que impide solapes entre registros de la misma persona. La API valida antes para
  dar mensajes claros, pero la última palabra la tiene Postgres.
- **Días en hora de España**: la BD guarda UTC; los filtros `from`/`to` se interpretan como días
  de `Europe/Madrid` (`zoneinfo` + paquete `tzdata`, que Windows y las imágenes Docker no traen).
- **El panel suma en SQL**: `WHERE` dinámico con solo los filtros que llegan y `GROUP BY` por
  persona, proyecto, label y día (en hora de España con `timezone()`); Python solo da forma.
- **Cuentas eliminadas se anonimizan**, no se borran: sus horas siguen en los informes de los
  demás y una cookie antigua deja de valer (`deleted_at`).
- **Tests sobre Postgres real** (BD `clockify_test`, se crea sola): cada test corre en una
  transacción que se deshace al acabar, y el login de Google se sustituye por uno falso.
