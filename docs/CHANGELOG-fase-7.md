# Changelog — Fase 7: cuentas con email y contraseña, y panel de admin

Fase añadida a petición del autor. Se numera 7 para no renumerar las demás, pero **va antes del
despliegue** (fase 5), porque cambia el login. El changelog general está en [CHANGELOG.md](CHANGELOG.md).

## Resumen rápido

- **Cuentas con cualquier email** (Gmail, Hotmail, Outlook…) **y contraseña**. La pantalla de
  entrada tiene "Entrar" / "Crear cuenta" y, debajo, el botón de Google como opción extra.
- **Sin confirmación al registrarse**, como acordamos.
- **"¿Olvidaste tu contraseña?"**: manda un link por email que caduca en 1 hora y sirve una sola
  vez. En local el email no se envía: sale en la consola de la API con el link.
- **Mi cuenta → Contraseña**: cambiarla, o ponerse una si entras con Google.
- **Panel de admin en `/admin`** (SQLAdmin) para los emails de `ADMIN_EMAILS`: ver, buscar y
  editar cualquier tabla. Enlace "Admin" en la cabecera si lo eres.
- 29 tests nuevos (145 en total), todos en verde.

## Lo que tienes que saber

1. **Para entrar al admin**: pon tu email en `backend/.env` → `ADMIN_EMAILS=["tu@email.com"]` y
   reinicia la API. Con la sesión de la app abierta, entras directamente en
   `http://localhost:5173/admin/`. Su formulario de login propio (en *Username* va el email) pide
   contraseña: si entras con Google, ponte una en Mi cuenta.
2. **El admin edita la base de datos directamente.** Se salta las reglas de la API (límite de 5
   espacios, permisos…), aunque las restricciones de la BD siguen (sin solapes, máx. 24 h, nombres
   únicos). Para no romper nada, desde el admin **no se pueden borrar** usuarios, espacios,
   proyectos ni labels (se archivan editando); sí tareas, invitaciones y links de recuperación.
   Cada cambio queda en el log de la API con quién lo hizo.
3. **La interfaz de SQLAdmin está en inglés**: no trae traducción al español.
4. **El botón de Google ahora es opcional**: si `frontend/.env` no tiene `VITE_GOOGLE_CLIENT_ID`,
   no aparece (antes mostraba un error) y se entra con email y contraseña.
5. **Emails en minúsculas**: `Ana@Hotmail.com` y `ana@hotmail.com` son la misma cuenta. La
   migración pasó a minúsculas los emails que ya había.
6. **Migración nueva** (`84efe5a21d70`): `users.password_hash`, `users.google_sub` pasa a opcional
   y la tabla `password_reset_tokens`. Ya está aplicada a tu Postgres local.
7. **En la consola de Windows la "ñ" del asunto se ve rota** ("contrase�a"). Es cómo muestra el
   texto la consola; un email real por Resend va en UTF-8 y se ve bien.
8. La **página de privacidad** ya menciona las contraseñas (cifradas), a los administradores y a
   Resend.

## Cambios

### backend
- `core/passwords.py`: hash y verificación con **argon2** (`pwdlib`, lo que recomienda hoy la doc
  de FastAPI).
- `services/passwords.py`: registro, login, links de recuperación y cambio de contraseña.
- `services/email.py`: backend `console` (local) o `resend` (producción, con `httpx`).
- `services/rate_limit.py`: 10 intentos de login cada 15 min por IP + email; 3 emails de
  recuperación por hora y email → 429.
- `api/auth.py`: rutas `register`, `login`, `password/forgot`, `password/reset` y `password`
  (cambiar o poner). `UserRead` añade `has_password` e `is_admin`. Google ahora también **une** la
  cuenta si ya existía con contraseña.
- `admin.py`: panel SQLAdmin con una vista por tabla y acceso solo para `ADMIN_EMAILS`.
- `models/password_reset.py` + migración; `models/user.py` con `password_hash` y `google_sub`
  opcional.
- `services/account.py`: eliminar la cuenta también borra la contraseña y gasta sus links; el
  `google_sub` pasa a `null`.
- `core/config.py` y `.env.example`: `ADMIN_EMAILS`, `FRONTEND_URL`, `EMAIL_BACKEND`,
  `RESEND_API_KEY` y `EMAIL_FROM`.
- Dependencias: `pwdlib[argon2]`, `sqladmin` e `itsdangerous`.

**Decisiones que conviene entender:**
- **Login con mensaje genérico y tiempo igual.** "Email o contraseña incorrectos" en los dos casos,
  y si el email no existe se verifica igualmente contra un hash ficticio. Si no, por el mensaje o
  por lo que tarda la respuesta se podría averiguar qué emails tienen cuenta.
- **"Recuperar" responde siempre igual** (202), exista o no la cuenta, por la misma razón.
- **Sin confirmar el email, pero a salvo.** El riesgo es que alguien registre *tu* email antes que
  tú. Lo cubren dos cosas: recuperar la contraseña sí exige el email, y si entras con Google y ya
  había una cuenta con contraseña con tu email, se unen **borrando esa contraseña**. Así quien la
  puso pierde el acceso.
- **Los links de recuperación siguen el patrón de las invitaciones**: token aleatorio largo, en
  la BD solo su hash, caducidad (1 h) y un solo uso. Usar uno gasta los demás pendientes.
- **Contraseñas: mínimo 8 caracteres y sin más reglas** (lo que recomienda el NIST). Las reglas
  tipo "mayúscula + número + símbolo" llevan a contraseñas peores y más fáciles de olvidar.
- **El freno a la fuerza bruta vive en memoria**: basta con un servidor. En Cloud Run, con varias
  instancias, cada una llevaría su cuenta, y la IP real llega en `X-Forwarded-For`. Lo revisamos
  al desplegar.
- **La cookie del admin se llama `admin_session`**: SQLAdmin usa por defecto `session`, que es la
  de la app, y la pisaría.
- **Un fallo al enviar el email no rompe la petición**: se registra en el log. Si no, "recuperar"
  respondería distinto cuando la cuenta existe.

### backend: tests
- `tests/test_password_auth.py` (21): registro con cualquier dominio, hash en la BD, email
  repetido o en mayúsculas, email de una cuenta de Google, validaciones, login correcto e
  incorrecto con el mismo mensaje, cuenta de Google sin contraseña, 429, cuenta eliminada,
  recuperar con el link del email, email sin cuenta, link de un solo uso, caducado, usar uno gasta
  los demás, link inventado, límite de 3 emails, cambiar y poner contraseña, y unir con Google
  borrando la contraseña.
- `tests/test_admin.py` (8): sin sesión o sin ser admin redirige al login del panel; el admin entra
  con su sesión de la app; ve la lista de todas las tablas; no se muestran hashes; login del panel
  con email y contraseña (y rechazo de quien no es admin); `is_admin` en `/auth/me`.
- `tests/conftest.py`: captura los emails en `outbox`, apunta el admin a la BD de pruebas y vacía
  los contadores de intentos en cada test.
- Además lo probé con el **servidor real** contra la BD de pruebas: registro → login fallido →
  email en consola → reset → login con la contraseña nueva, y el panel entrando como admin.

### frontend
- `components/auth/AuthPanel.tsx`: "Entrar" / "Crear cuenta", "¿Olvidaste tu contraseña?" y el
  botón de Google si está configurado. Lo usan `LoginPage` e `InvitePage`, así que quien abre una
  invitación puede crearse la cuenta ahí mismo.
- `pages/PasswordRecoveryPages.tsx`: `/recuperar` y `/recuperar/:token` (al guardar, ya entras).
- `pages/AccountPage.tsx`: tarjeta "Contraseña".
- `App.tsx`: rutas nuevas y enlace "Admin" en la cabecera.
- `vite.config.ts`: proxy de `/admin` con `changeOrigin: false`. Con la forma corta, Vite cambia
  la cabecera `Host` a `127.0.0.1:8000`; SQLAdmin construye sus links con ella y mandaba al
  navegador fuera de `localhost:5173`, donde ya no viaja la cookie. Lo detecté probándolo.
- `lib/auth.ts`: `GOOGLE_ENABLED`. `lib/types.ts`: `has_password` e `is_admin`.
- `pages/PrivacyPage.tsx`: contraseñas, administradores y Resend.
- Revisé con capturas el login, `/recuperar` y el login del panel de admin.

### docs
- `README.md` (cómo se usa, panel de admin, módulos, modelo de datos, reglas y estado),
  `backend/README.md`, `frontend/README.md`, `docs/REQUISITOS.md` y la spec.

## Commits propuestos

Las fases 3 a 7 siguen sin commitear. Propuesta por capas (amplía la de
[CHANGELOG-fase-6.md](CHANGELOG-fase-6.md#commits-propuestos-fases-3-a-6)):

1. `infra: Postgres solo en 127.0.0.1 y DATABASE_URL sin localhost`
   `docker-compose.yml`, `backend/.env.example`, `backend/app/core/config.py`
2. `backend: tareas, cronómetro, panel, eliminar cuenta, contraseñas y /admin (fases 3-7)`
   `backend/` (menos lo del commit 1), `specs/api/openapi.yaml`
3. `frontend: hoja de proyecto, cronómetro, panel con gráficas, cuentas con contraseña (fases 3-7)`
   `frontend/`
4. `docs: changelogs de las fases 3 a 7, README detallado y requisitos`
   `docs/`, `README.md`, `backend/README.md`, `frontend/README.md`, `CLAUDE.md`

## Pendiente

- [ ] Probar a mano: crear una cuenta con un Hotmail, salir, "¿Olvidaste tu contraseña?" con el
      link de la consola, y entrar a `/admin` con tu email en `ADMIN_EMAILS`.
- [ ] Al desplegar: Resend con dominio verificado (`EMAIL_BACKEND=resend`), `FRONTEND_URL` de
      producción e IP real detrás del proxy para el freno de intentos. Ver [REQUISITOS.md](REQUISITOS.md).
