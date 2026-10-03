# Changelog — Fase 1: login con Google y espacios

Fase 1 del plan ("Auth y espacios"). El changelog general está en [CHANGELOG.md](CHANGELOG.md).

## Resumen rápido

- Se entra **con Google**. No hay contraseñas: la primera vez que entras se crea tu usuario.
- Cada persona crea **espacios** (un estudio, un equipo) y es su **dueña**. Máximo **5 propios sin
  archivar**; en los espacios a los que te invitan no hay límite.
- El dueño invita con **links** tipo Discord: caducan a los **10 días**, se pueden **revocar** y
  admiten un **máximo de usos** opcional.
- Los miembros pueden **salir**; el dueño puede **expulsar**, **transferir** el espacio a otro
  miembro, **renombrarlo** y **archivarlo**. Nada se borra.
- **Aislamiento**: si no eres miembro de un espacio, la API responde 404 como si no existiera.
- 40 tests en pytest (login, espacios, miembros, invitaciones y aislamiento). Todos pasan.

## Lo que tienes que saber

1. **Sin un Client ID de Google no puedes entrar.** La API responde 503 en el login y el front
   muestra "Falta VITE_GOOGLE_CLIENT_ID". Pasos más abajo.
2. **La migración ya está aplicada** a tu Postgres local (`c31077379cef`, 4 tablas nuevas).
3. **Los tests usan otra BD**, `clockify_test`, que se crea sola en el mismo Postgres de Docker.
   Necesitan `docker compose up -d db` en marcha.
4. **Login real no probado de punta a punta**: falta el Client ID. Probado con el servidor real:
   `/health` 200, `/auth/me` 401, `/invitations/x` 404 y `/auth/google` 503 (sin Client ID).
   El front pasa lint y build, pero no lo he abierto en el navegador.
5. **Smart App Control bloquea también `uvicorn.exe`.** Si `fastapi dev` falla, usa
   `uv run python -m uvicorn app.main:app --reload`.
6. **Nueva dependencia del front**: `react-router`. Ejecuta `npm install` si vienes de otro equipo.

### Configurar el login con Google (una vez, ~5 min)

1. En [Google Cloud Console](https://console.cloud.google.com/), crea o elige un proyecto. Puede
   ser el mismo que usaremos para Cloud Run.
2. **APIs y servicios → Pantalla de consentimiento de OAuth**: tipo **Externo**, nombre de la app,
   tu email. Ámbitos: solo `email` y `profile`, así que no hace falta verificar la app. Mientras esté
   en modo "Prueba", añade como usuarios de prueba los Gmail que vayan a entrar.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**:
   tipo **Aplicación web**. En *Orígenes de JavaScript autorizados* pon `http://localhost:5173`
   y `http://localhost`. No hace falta ninguna URI de redirección.
4. Copia el Client ID (`xxxx.apps.googleusercontent.com`) en dos sitios:
   - `backend/.env` → `GOOGLE_CLIENT_ID=...`
   - `frontend/.env` → `VITE_GOOGLE_CLIENT_ID=...` (copia `frontend/.env.example`)
5. Reinicia la API y `npm run dev`. Abre `http://localhost:5173`; tiene que ser `localhost`, no
   `127.0.0.1`, porque Google solo acepta los orígenes que autorizaste.

El Client ID no es secreto (va en el JavaScript del navegador), pero sigue el criterio del
proyecto: solo en `.env`.

### Cómo probar las invitaciones tú solo

Abre una ventana normal con tu cuenta y otra **de incógnito** con otro Gmail, que tiene que estar
en la lista de usuarios de prueba. Crea un espacio, genera un link, ábrelo en la de incógnito y
acepta.

## Cambios

### backend: modelos y migración de usuarios, espacios, miembros e invitaciones
- `app/models/`: `User` (identificado por `google_sub`), `Workspace` (`owner_id`, `archived`),
  `Membership` (clave `(workspace_id, user_id)`; `removed_at` en vez de borrar) e `Invitation`
  (solo `token_hash`, `expires_at`, `max_uses`, `uses`, `revoked_at`).
- `models/common.py`: `utc_now()` y `TZDateTime` (`timestamptz`: fechas siempre en UTC).
- Migración `c31077379cef`. `alembic check` confirma que coincide con los modelos.
- Dependencias: `google-auth[requests]` (verificar el ID token) y `pyjwt` (cookie de sesión).
- `core/config.py`: `GOOGLE_CLIENT_ID`, `SESSION_DAYS`, `COOKIE_SECURE`, `COOKIE_SAMESITE`.

### backend: login con Google, espacios e invitaciones
- `POST /auth/google`, `POST /auth/logout`, `GET /auth/me`.
- `GET/POST /workspaces`, `PATCH /workspaces/{wid}`, `GET /workspaces/{wid}/members`,
  `DELETE /workspaces/{wid}/members/{uid}`.
- `GET/POST /workspaces/{wid}/invitations`, `DELETE /workspaces/{wid}/invitations/{id}`,
  `GET /invitations/{token}` (pública) y `POST /invitations/{token}/accept`.
- `api/deps.py`: `CurrentUser`, `MemberAccess` (miembro activo o 404) y `OwnerAccess` (además dueño o 403).
- `services/workspaces.py`: límite de 5 espacios y estado de un link (`active`, `expired`, `revoked`, `exhausted`, `archived`).
- `specs/api/openapi.yaml` regenerado.

**Decisiones que conviene entender:**
- **404 y no 403 en espacios ajenos**: un 403 confirmaría que el espacio existe. Dentro de tu
  espacio, en cambio, sí se responde 403 ("solo el dueño puede…"), porque ahí ya no se revela nada.
- **Sesión propia en vez de usar el token de Google**: el ID token de Google caduca en 1 hora.
  Lo verificamos una vez y a partir de ahí manda nuestro JWT (30 días) en una cookie `httpOnly`.
- **Hash de los tokens de invitación**: si alguien leyera la BD, no podría usar los links.
- **`SELECT ... FOR UPDATE`**: sin él, dos peticiones simultáneas podrían crear el 6.º espacio
  o pasarse de `max_uses`. Bloquear la fila obliga a la segunda petición a esperar a la primera.
- **Transferir o desarchivar también respeta el límite de 5**, para que no se pueda esquivar.
- **Si ya eres miembro, aceptar un link no gasta un uso.** Un expulsado puede volver con un link
  nuevo: el dueño decide a quién se lo manda, y puede revocarlo.
- **Arreglo en `deps.py`**: el parámetro de la cookie se llamaba `token` y chocaba con
  `/invitations/{token}` (FastAPI empareja por nombre). Ahora se llama `session_token`.

### backend: tests
- `tests/conftest.py`: BD `clockify_test` creada desde los modelos. Cada test va dentro de una
  transacción que se deshace al acabar (`join_transaction_mode="create_savepoint"`), así que los
  `commit()` de las rutas no dejan nada guardado.
- El verificador de Google se sustituye por uno falso (`"sub|email|nombre"`) con
  `app.dependency_overrides`; por eso la verificación se inyecta como dependencia.
- `make_client("ana")` da un cliente con la sesión de Ana iniciada. Con varios clientes se
  simulan varias personas.
- `test_auth.py` (8 tests), `test_workspaces.py` (17 tests, entre ellos los de aislamiento) y
  `test_invitations.py` (14 tests).

### frontend: login, espacios e invitaciones
- `react-router` y los componentes shadcn `input` y `badge`.
- `GoogleLoginButton`: carga Google Identity Services, recibe el ID token y lo manda a la API.
- Páginas: login, `/` (mis espacios + crear), `/w/:wid` (ajustes, miembros, invitaciones) e
  `/invite/:token` (pública; si no hay sesión, el botón de Google sale ahí mismo).
- `lib/api.ts`: `apiPost`, `apiPatch`, `apiDelete` y `ApiError`, que muestra el mensaje de FastAPI.
- `lib/auth.ts` (`useMe`) y `lib/types.ts`. Nuevo `frontend/.env.example`.
- El link de invitación se muestra **una sola vez**, al crearlo, porque la BD solo guarda su hash.

### docs
- `CLAUDE.md` y `README.md`: descripción y modelo de datos multi-espacio.
- `backend/README.md`: estructura, tabla de endpoints y decisiones.
- `frontend/README.md`: estructura y decisiones.
- `backend/.env.example` con las variables nuevas.
- `specs/workflows/invitacion.md`: diagrama del flujo de invitación.

## Commits propuestos

Todo está en el árbol de trabajo, sin commitear. Propuesta, en este orden:

1. `backend: modelos y migración de usuarios, espacios, miembros e invitaciones`
   `backend/app/models/`, `backend/alembic/versions/c31077379cef_*.py`, `backend/pyproject.toml`,
   `backend/uv.lock`, `backend/app/core/config.py`
2. `backend: login con Google, espacios, miembros e invitaciones con sus tests`
   `backend/app/core/security.py`, `backend/app/core/google.py`, `backend/app/api/`,
   `backend/app/schemas.py`, `backend/app/services/`, `backend/app/main.py`, `backend/tests/`,
   `specs/api/openapi.yaml`
3. `frontend: login con Google, mis espacios, gestión del espacio e invitaciones`
   `frontend/src/`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/.env.example`
4. `docs: fase 1 en changelog, READMEs, CLAUDE.md y flujo de invitación`
   `docs/`, `README.md`, `CLAUDE.md`, `backend/README.md`, `backend/.env.example`,
   `frontend/README.md`, `specs/workflows/invitacion.md`

## Pendiente para cerrar la fase 1

- [x] Crear el Client ID de Google y probar el login de verdad en el navegador.
- [ ] Probar a mano una invitación con dos cuentas.

Anotado para más adelante (fase 5, en la spec): opción de **eliminar la cuenta**. Se anonimizan
los datos personales y las horas se conservan sin nombre.
