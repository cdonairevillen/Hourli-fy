# Changelog — Fase 5 (parte de código): eliminar la cuenta y privacidad

Fase 5 del plan ("Deploy"). El changelog general está en [CHANGELOG.md](CHANGELOG.md).

> **El despliegue no está hecho**: quedamos en hacerlo juntos, paso a paso. De la fase 5 solo
> he adelantado lo que es código de la app y no toca ningún servicio externo: eliminar la cuenta
> y la página de privacidad. Ni Dockerfile, ni Cloud Run, ni Cloudflare, ni Supabase.

## Resumen rápido

- **Mi cuenta** (`/cuenta`, pulsando tu nombre en la cabecera): tus datos de Google y
  **"Eliminar mi cuenta"**.
- **Privacidad** (`/privacidad`, pública, enlazada desde el login y desde Mi cuenta): política de
  privacidad en **borrador**.
- 7 tests nuevos (`tests/test_account.py`).

## Lo que tienes que saber

1. **La página de privacidad es un borrador con huecos que tienes que rellenar tú**:
   `[NOMBRE O RAZÓN SOCIAL DEL RESPONSABLE]`, `[EMAIL DE CONTACTO]`, las `[REGIÓN]` de Supabase y
   Google Cloud (las sabremos al desplegar) y la `[FECHA]`. No me he inventado ningún dato legal.
   Antes de publicar, conviene que lo revise alguien que sepa de protección de datos.
2. **Eliminar la cuenta no borra la fila del usuario: la anonimiza**, tal como acordamos en la
   spec:
   - Hay que transferir o archivar antes los espacios propios activos (si no, 409 con sus nombres).
   - Se para su cronómetro, sale de todos sus espacios, y nombre, email y foto se sustituyen.
   - Sus horas siguen en los informes, a nombre de "Usuario eliminado".
   - Si vuelve a entrar con Google, empieza como un usuario nuevo.
3. **Migración nueva** (`32d479a0015b`): columna `users.deleted_at`. Ya está aplicada a tu
   Postgres local.
4. **La confirmación pide escribir «eliminar»**: borrar la cuenta no se puede deshacer, y un
   simple "¿Seguro?" se acepta sin leer.

## Cambios

### backend
- `app/services/account.py`: `delete_account()` con las reglas de arriba.
- `app/api/auth.py`: `DELETE /auth/me` (204 y borra la cookie).
- `app/api/deps.py`: `get_current_user` rechaza las cuentas eliminadas aunque traigan una cookie
  todavía válida (el JWT dura 30 días y no se puede "desfirmar").
- `app/models/user.py` + migración: `deleted_at`.

**Decisiones que conviene entender:**
- **Anonimizar en vez de borrar** cumple el derecho de supresión (los datos ya no identifican a
  nadie) sin dejar agujeros en los totales de los demás.
- **Email y `google_sub` pasan a valores que no son de nadie** (`eliminado-<id>@hourlify.invalid`,
  `eliminado:<id>`): son columnas únicas y obligatorias, y así la misma cuenta de Google puede
  volver a registrarse sin choques. `.invalid` es un dominio reservado que nunca existirá.
- **Los espacios archivados propios no bloquean**: ya no tienen actividad, así que quedan a
  nombre del usuario anonimizado.

### backend: tests
- `tests/test_account.py` (7): anonimiza y cierra la sesión, 409 con espacios activos, se puede con
  espacios archivados, las horas siguen en el panel como "Usuario eliminado", se para el
  cronómetro, volver con Google crea un usuario nuevo, y 401 sin sesión.

### frontend
- `pages/AccountPage.tsx`: datos de Google, aviso de los espacios que bloquean (con enlace a su
  pestaña Equipo) y la confirmación escribiendo «eliminar». Al terminar se vacía la caché y vuelve
  el login.
- `pages/PrivacyPage.tsx`: el borrador de la política (qué datos, para qué, quién los ve, dónde,
  cuánto tiempo, cómo borrarlos y derechos).
- `App.tsx`: rutas `/cuenta` (privada) y `/privacidad` (pública); tu nombre en la cabecera enlaza a
  Mi cuenta. `LoginPage`: enlace a Privacidad.

## Lo que queda de la fase 5 (en pareja)

- [ ] `Dockerfile` del backend e imagen en Artifact Registry.
- [ ] Proyecto de Supabase (región UE), `DATABASE_URL` como secreto y `alembic upgrade head` contra él.
- [ ] Servicio de Cloud Run con sus variables (`SECRET_KEY` nuevo, `GOOGLE_CLIENT_ID`,
      `CORS_ORIGINS`, `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`).
- [ ] Frontend en Cloudflare Pages (`VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID`, regla SPA para que
      `/w/...` no dé 404).
- [ ] Subdominio, orígenes autorizados en Google y publicar la pantalla de consentimiento (con la
      URL de `/privacidad` ya completada).
- [ ] Copias de seguridad (`pg_dump` periódico).

## Commits propuestos

Ver la nota común en [CHANGELOG-fase-6.md](CHANGELOG-fase-6.md#commits-propuestos-fases-3-a-6).
