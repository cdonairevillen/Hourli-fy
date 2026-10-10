# Despliegue paso a paso

Guía para publicar Hourli-fy **desde cero y solo con el navegador**: todo se hace en las webs de
Supabase, Google Cloud (con **Cloud Shell**, una terminal en el navegador que ya trae `gcloud`,
`git` y `python3`) y Cloudflare. No hace falta instalar nada en el ordenador del clúster.

Tiempo estimado: 1–1,5 h la primera vez (pasos 1–6 y 8; el 7 es opcional). Coste: 0 € con los planes gratuitos (Google pide una
tarjeta para Cloud Run, pero con este uso no debería cobrar nada).

> **Nunca subas claves al repo ni las pegues en un chat.** Van en las variables de Cloud Run y de
> Cloudflare, y en el archivo `~/hourlify-env.yaml` de tu Cloud Shell (fuera del repo).

---

## Cómo queda montado

```
Navegador ──► https://hourli-fy.pages.dev          (Cloudflare Pages: la web de React)
                 │
                 └─ /api/*  ──► Pages Function ──► https://hourlify-api-….run.app   (Cloud Run: FastAPI)
                                                          │
                                                          └──► Supabase (PostgreSQL)

Admin: https://hourlify-api-….run.app/admin/   (directo a Cloud Run)
```

- **La web y la API comparten dominio.** La Pages Function (`frontend/functions/api/[[path]].js`)
  reenvía `/api/*` a Cloud Run, igual que el proxy de Vite en local. Así la cookie de sesión es
  del propio dominio de la web: si la API estuviera en otro dominio, Safari y los bloqueadores la
  tratarían como cookie de terceros y no se podría iniciar sesión.
- **La base de datos se crea sola.** Cada vez que arranca, la API ejecuta `alembic upgrade head`
  (`backend/Dockerfile`). La primera vez crea todas las tablas en una base de datos vacía; las
  siguientes no hace nada salvo que haya migraciones nuevas. **No se migra nada de la BD local**:
  producción empieza limpia.

### Valores que irás apuntando

Ten un bloc de notas a mano (o mejor, un gestor de contraseñas). Los irás rellenando:

| Nombre | De dónde sale | Ejemplo |
| --- | --- | --- |
| `DB_PASSWORD` | Paso 1 (Supabase) | `k3J9xQ2mP7…` (solo letras y números) |
| `DATABASE_URL` | Paso 1 (Supabase) | `postgresql+psycopg://postgres.abcd…:…@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require` |
| `WEB_URL` | Paso 2 (Cloudflare) | `https://hourli-fy.pages.dev` |
| `GOOGLE_CLIENT_ID` | Ya lo tienes (`backend/.env`) | `1234-abc.apps.googleusercontent.com` |
| `PROJECT_ID` | Paso 3 (Google Cloud) | `hourli-fy-123456` |
| `SECRET_KEY` | Paso 3 (Cloud Shell) | `Zb8…` (43 caracteres) |
| `API_URL` | Paso 3 (Cloud Run) | `https://hourlify-api-abc123-ew.a.run.app` |
| `BACKUP_PASSPHRASE` | Paso 8 (la inventas tú) | cuatro o cinco palabras al azar |

---

## Paso 1 · Supabase (base de datos)

1. Entra en <https://supabase.com> → **Start your project** y regístrate (con GitHub es lo más
   rápido).
2. **New project**:
   - *Organization*: la que te crea por defecto (plan **Free**).
   - *Project name*: `hourlify`.
   - *Database password*: pulsa **Generate a password**. Si la contraseña generada tiene símbolos
     (`@`, `/`, `#`, `?`, `%`…), **escribe tú una solo con letras y números** de 24 o más
     caracteres: los símbolos rompen la URL de conexión. Apúntala como `DB_PASSWORD`.
   - *Region*: **West EU (Ireland)** o **Central EU (Frankfurt)** (cerca de Cloud Run en Bélgica).
   - Si aparece una sección **Security / Data API**, **desmarca "Enable Data API"** (ver punto 4).
   - **Create new project** y espera 1–2 minutos.
3. **Cadena de conexión**: botón **Connect** (arriba) → pestaña *Connection String* → elige
   **Session pooler** (no "Direct connection": Cloud Run no tiene IPv6 y la directa sí lo exige;
   tampoco "Transaction pooler", que no es compatible con psycopg). Verás algo así:
   ```
   postgresql://postgres.abcdefghijkl:[YOUR-PASSWORD]@aws-0-eu-west-1.pooler.supabase.com:5432/postgres
   ```
   Conviértela en tu `DATABASE_URL` con **tres cambios**:
   - `postgresql://` → `postgresql+psycopg://`
   - `[YOUR-PASSWORD]` → tu `DB_PASSWORD` (sin corchetes)
   - añade al final `?sslmode=require`

   Resultado:
   ```
   postgresql+psycopg://postgres.abcdefghijkl:TU_PASSWORD@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```
4. **Desactiva la Data API** (importante para la seguridad). Supabase publica por defecto cada
   tabla de la base de datos en una API REST pública protegida solo por RLS, y nosotros no usamos
   RLS: toda la seguridad está en FastAPI. Si la dejas activa, cualquiera con la clave pública del
   proyecto podría leer las tablas.
   - **Project Settings → Data API** (o **Integrations → Data API**, según la versión del panel) →
     desactiva **Enable Data API** → **Save**.
   - Si no la encuentras, alternativa: en *Exposed schemas* quita `public` y guarda.
5. No crees tablas a mano: las crea la API en el paso 3.

> **Saber**: el plan gratuito **pausa el proyecto tras 7 días sin uso**. Se reactiva desde el
> panel de Supabase (*Restore project*). Con gente registrando horas no ocurrirá.

---

## Paso 2 · Cloudflare Pages (la web)

La web se publica primero (aún sin API) para saber su URL, que la API necesita en el paso 3.

1. Entra en <https://dash.cloudflare.com> y regístrate (plan **Free**).
2. Menú izquierdo **Compute (Workers) → Workers & Pages** → **Create application**. Cloudflare
   ofrece por defecto un *Worker*: busca la pestaña o el enlace **Pages** ("Looking to deploy
   Pages? Get started") → **Import an existing Git repository**.
3. **Connect GitHub** → autoriza la app de Cloudflare → en *Repository access* elige *Only select
   repositories* → **Hourli-fy** → *Install & Authorize*. Selecciona el repo → **Begin setup**.
4. Configuración:

   | Campo | Valor |
   | --- | --- |
   | Project name | `hourli-fy` (define la URL: `hourli-fy.pages.dev`) |
   | Production branch | `master` |
   | Framework preset | `None` |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Root directory (advanced) | `frontend` |

   En **Environment variables (advanced)** añade:

   | Variable | Valor |
   | --- | --- |
   | `NODE_VERSION` | `22` |
   | `VITE_GOOGLE_CLIENT_ID` | tu `GOOGLE_CLIENT_ID` |

5. **Save and Deploy**. Tarda 1–2 minutos. Al terminar verás la URL (`https://hourli-fy.pages.dev`,
   o con un sufijo si el nombre ya estaba cogido). Apúntala como `WEB_URL`, **sin barra final**.
6. Si abres la web ahora verás el login, pero dará error al entrar: aún no hay API. Es normal.

---

## Paso 3 · Google Cloud Run (la API)

Usa el **mismo proyecto de Google Cloud** donde creaste el Client ID de OAuth.

### 3.1 Facturación y presupuesto
1. <https://console.cloud.google.com> → arriba, selector de proyectos → elige el tuyo. Apunta su
   **ID** (no el nombre) como `PROJECT_ID`.
2. **☰ → Facturación** → *Vincular una cuenta de facturación* → crea una con tu tarjeta.
3. Recomendado: **Facturación → Presupuestos y alertas → Crear presupuesto** → importe `5 €` →
   alertas al 50 %, 90 % y 100 %. Te avisa por email si algo se dispara.

### 3.2 Abrir Cloud Shell y preparar
1. Botón **>_** (*Activar Cloud Shell*) arriba a la derecha. Se abre una terminal abajo.
2. Selecciona el proyecto y activa los servicios (tarda ~1 min):
   ```bash
   gcloud config set project PROJECT_ID
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```
3. **Clonar el repo**. Es privado, así que necesitas un token de GitHub:
   - En GitHub: **Settings → Developer settings → Personal access tokens → Fine-grained tokens →
     Generate new token**. *Repository access*: *Only select repositories* → `Hourli-fy`.
     *Permissions → Repository permissions → Contents*: **Read-only**. Caducidad: 30 días.
     Copia el token (`github_pat_…`).
   - En Cloud Shell:
     ```bash
     git clone https://github.com/cdonairevillen/Hourli-fy.git
     ```
     Usuario: `cdonairevillen`. Contraseña: **pega el token** (no se ve al escribir).
4. Genera la clave de las sesiones y apúntala como `SECRET_KEY`:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

### 3.3 Variables de la API
Crea el archivo de variables **fuera del repo** (en tu carpeta personal de Cloud Shell):
```bash
nano ~/hourlify-env.yaml
```
Pega esto sustituyendo los valores (las comillas son necesarias; las simples `'…'` de las listas
también):
```yaml
DATABASE_URL: "postgresql+psycopg://postgres.abcdefghijkl:TU_PASSWORD@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
SECRET_KEY: "TU_SECRET_KEY"
GOOGLE_CLIENT_ID: "TU_GOOGLE_CLIENT_ID"
CORS_ORIGINS: '["https://hourli-fy.pages.dev"]'
FRONTEND_URL: "https://hourli-fy.pages.dev"
COOKIE_SECURE: "true"
COOKIE_SAMESITE: "lax"
ADMIN_EMAILS: '["tu-email@ejemplo.com"]'
EMAIL_BACKEND: "console"
```
Guarda con `Ctrl+O`, `Enter`, y sal con `Ctrl+X`.

- `CORS_ORIGINS` y `FRONTEND_URL` = tu `WEB_URL` (sin barra final).
- `COOKIE_SAMESITE` es `lax` (no `none`) porque la web y la API comparten dominio gracias a la
  Pages Function.
- `EMAIL_BACKEND: "console"`: los emails de "recuperar contraseña" se escriben en los logs de
  Cloud Run en vez de enviarse. Para enviarlos de verdad, ver el paso 7 (opcional).
- Este archivo se queda en Cloud Shell (que conserva tu carpeta personal). Guarda también una copia
  en tu gestor de contraseñas: Google borra la carpeta de Cloud Shell tras 120 días sin usarla.

### 3.4 Desplegar
```bash
cd ~/Hourli-fy
gcloud run deploy hourlify-api \
  --source backend \
  --region europe-west1 \
  --allow-unauthenticated \
  --env-vars-file ~/hourlify-env.yaml \
  --memory 512Mi \
  --max-instances 2
```
- Si pregunta *"Deploying from source requires an Artifact Registry Docker repository… create?"*
  → `Y`.
- Tarda 3–5 minutos: Cloud Build construye la imagen con `backend/Dockerfile` y la publica.
- Al terminar muestra `Service URL: https://hourlify-api-….run.app`. Apúntala como `API_URL`.
- `--max-instances 2` limita el coste si algo se dispara. `--allow-unauthenticated` es necesario:
  la API es pública (la protege el login de la propia app).

### 3.5 Comprobar
```bash
curl https://hourlify-api-….run.app/api/health
```
Debe responder `{"status":"ok"}`. Para ver que se crearon las tablas:
```bash
gcloud run services logs read hourlify-api --region europe-west1 --limit 50
```
Deben aparecer las líneas `Running upgrade … -> e000194eb176, acceso por proyecto`. En Supabase,
**Table Editor** mostrará las tablas (`users`, `workspaces`, …).

---

## Paso 4 · Conectar la web con la API

1. Cloudflare → **Workers & Pages** → `hourli-fy` → **Settings → Variables and Secrets** →
   **Add** (entorno **Production**):

   | Variable | Valor | Para qué |
   | --- | --- | --- |
   | `API_ORIGIN` | tu `API_URL` (sin barra final) | La usa la Pages Function para reenviar `/api` |
   | `VITE_ADMIN_URL` | `API_URL` + `/admin/` | El enlace "Admin" de la cabecera |

   Comprueba que siguen `NODE_VERSION` y `VITE_GOOGLE_CLIENT_ID`. **Save**.
2. Las variables solo se aplican en un despliegue nuevo: **Deployments** → en el último, menú
   **⋯ → Retry deployment**. Espera a que termine.

---

## Paso 5 · Google: login y pantalla de consentimiento

1. <https://console.cloud.google.com> → **APIs y servicios → Credenciales** → tu *ID de cliente
   de OAuth 2.0* (tipo Aplicación web).
2. En **Orígenes de JavaScript autorizados** → *Añadir URI* → tu `WEB_URL`
   (`https://hourli-fy.pages.dev`, sin barra final). Deja también `http://localhost:5173` para
   seguir desarrollando. **No** hacen falta *URIs de redireccionamiento*. **Guardar**. Puede
   tardar unos minutos en aplicarse.
3. **Antes de publicar la app**, rellena los `[PLACEHOLDERS]` de la página de privacidad
   (`frontend/src/pages/PrivacyPage.tsx`: responsable, email de contacto, fecha y región:
   *Supabase UE (Irlanda/Fráncfort), Google Cloud europe-west1 (Bélgica), Cloudflare*). Haz
   commit y push: Cloudflare redespliega sola la web.
4. **APIs y servicios → Pantalla de consentimiento de OAuth** (o *Google Auth Platform*):
   - **Branding**: *Página principal de la aplicación* = `WEB_URL`; *Política de privacidad* =
     `WEB_URL/privacidad`; *Dominios autorizados*: `pages.dev`. Guardar.
   - **Audience / Público**: *Estado de publicación* → **Publicar aplicación** → Confirmar. Sin
     esto, solo pueden entrar con Google los "usuarios de prueba" que añadiste.
   - Al pedir solo email y perfil, Google no exige verificación: queda "En producción" al momento.

---

## Paso 6 · Probar en producción

Abre `WEB_URL` en una ventana normal (no la de desarrollo):

- [ ] **Registro** con email y contraseña → entras a "Espacios".
- [ ] **Salir** → vuelves al login. **Entrar** de nuevo con la misma cuenta.
- [ ] **Entrar con Google** (otra cuenta o la misma; si el email coincide, se unen).
- [ ] Crear un espacio, un proyecto, una label, y registrar una tarea manual y una con cronómetro.
- [ ] Invitar a otra cuenta (otro navegador o ventana privada) **solo a un proyecto** y comprobar
      que no ve los demás.
- [ ] Panel del dueño: totales de la quincena y gráfica.
- [ ] **Admin**: tu cuenta tiene que estar en `ADMIN_EMAILS` y **tener contraseña** (si entras con
      Google, ponla en *Mi cuenta*). Enlace **Admin** de la cabecera → login del panel.
- [ ] **Recuperar contraseña** (con `EMAIL_BACKEND: "console"`): pídelo desde el login y busca el
      link en los logs:
      ```bash
      gcloud run services logs read hourlify-api --region europe-west1 --limit 30
      ```
- [ ] Con el móvil (otra red): la web carga y se puede entrar.

Si todo va, ya está desplegado. Falta solo activar las copias de seguridad (paso 8): **no lo
saltes**.

---

## Paso 7 (opcional) · Dominio propio y emails de verdad

Hace falta un **dominio** (unos 10–15 €/año, o el de la empresa si te dan acceso a su DNS).

### 7.1 Dominio para la web
1. Cloudflare → `hourli-fy` → **Custom domains → Set up a custom domain** → `horas.tudominio.com`.
   Sigue las instrucciones (si el DNS está en Cloudflare es automático; si no, te da un registro
   `CNAME` que añadir en el DNS del dominio).
2. Con el nuevo dominio cambia **en todos estos sitios** `WEB_URL` por `https://horas.tudominio.com`:
   - `~/hourlify-env.yaml` (`CORS_ORIGINS` y `FRONTEND_URL`) y aplica (ver 7.3).
   - Google → Orígenes de JavaScript autorizados (añádelo) y Branding (página principal,
     privacidad y dominio autorizado).

### 7.2 Resend (emails de recuperación)
1. <https://resend.com> → regístrate (gratis: 3.000 emails/mes, 100/día).
2. **Domains → Add domain** → `tudominio.com` → región `eu-west-1`. Añade los registros DNS que te
   da (SPF/DKIM, tipo `TXT` y `MX`) en el DNS del dominio → **Verify**. Puede tardar de minutos a
   horas.
3. **API Keys → Create API key** → permiso **Sending access** → copia `re_…`.
4. Añade a `~/hourlify-env.yaml` (cambiando `EMAIL_BACKEND`):
   ```yaml
   EMAIL_BACKEND: "resend"
   RESEND_API_KEY: "re_..."
   EMAIL_FROM: "Hourli-fy <no-responder@tudominio.com>"
   ```

### 7.3 Aplicar cambios de variables en la API
Sin reconstruir la imagen:
```bash
gcloud run services update hourlify-api --region europe-west1 --env-vars-file ~/hourlify-env.yaml
```
(`--env-vars-file` reemplaza **todas** las variables por las del archivo: mantenlo completo.)

---

## Paso 8 · Copias de seguridad diarias

El plan gratuito de Supabase **no da copias descargables**. Por eso el repo trae un workflow de
GitHub Actions (`.github/workflows/backup-db.yml`) que **cada día a las 03:00 UTC** hace un
`pg_dump` de la base de datos, lo **cifra** y lo guarda **30 días** como artefacto del workflow.
Gratis: dura menos de 1 minuto al día (el plan gratuito de GitHub da 2.000 minutos al mes) y cada
copia ocupa poco.

### 8.1 Activarlo (una vez)
1. Prepara la URL de conexión **para pg_dump**: es tu `DATABASE_URL` **sin** `+psycopg`:
   ```
   postgresql://postgres.abcdefghijkl:TU_PASSWORD@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```
2. Inventa una **frase de cifrado** larga (por ejemplo cuatro o cinco palabras al azar) y
   **guárdala en tu gestor de contraseñas**. Sin ella las copias no se pueden abrir: ni GitHub ni
   yo podemos recuperarla.
3. GitHub → repo `Hourli-fy` → **Settings → Secrets and variables → Actions → New repository
   secret**, dos veces:

   | Name | Secret |
   | --- | --- |
   | `SUPABASE_DB_URL` | la URL del punto 1 |
   | `BACKUP_PASSPHRASE` | la frase del punto 2 |

4. Pruébalo ya, sin esperar a la noche: pestaña **Actions** → *Copia de seguridad de la BD* →
   **Run workflow** → *Run workflow*. En 1 minuto debe salir en verde ✅, y dentro del run, abajo,
   en **Artifacts**, un archivo `hourlify-AAAA-MM-DD-HHMM.dump.gpg`.
5. Si sale en rojo, abre el run y mira el error: casi siempre es la URL (contraseña, `+psycopg`
   que sobra o falta `?sslmode=require`).

GitHub te avisa por email si una ejecución programada falla. Si el repo pasa **60 días sin
commits**, GitHub puede desactivar los workflows programados: lo verás en la pestaña *Actions* y
se reactivan con un botón.

### 8.2 Restaurar una copia
Solo si se pierden datos. Se hace desde Cloud Shell (tiene `gpg` y Docker):

1. GitHub → **Actions** → elige el run de la fecha que quieres → **Artifacts** → descarga el
   `.zip`.
2. Cloud Shell → menú **⋮ → Subir** → sube el `.zip`. Después:
   ```bash
   unzip hourlify-*.dump.gpg.zip
   gpg -d -o copia.dump hourlify-*.dump.gpg     # pide la frase de cifrado
   ```
3. Restaura sobre la base de datos de Supabase. Esto **reemplaza** las tablas por las de la copia:
   lo registrado después de la copia se pierde.
   ```bash
   docker run --rm -i postgres:18 pg_restore --clean --if-exists --no-owner --no-privileges \
     -d "postgresql://postgres.abcdefghijkl:TU_PASSWORD@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require" \
     < copia.dump
   ```
   Al final dirá `errors ignored on restore: 2` o `3` (no puede borrar ni crear el esquema
   `public`, que ya existe, y quizá un `transaction_timeout`). **Es normal**: los datos se
   restauran igual. Lo probé así en local.
4. Comprueba en Supabase → **Table Editor** que están los datos, y entra en la web.
5. Borra los archivos de Cloud Shell: `rm copia.dump hourlify-*`.

> **Para más tranquilidad**: Supabase **Pro** (unos 25 $/mes) añade copias diarias automáticas
> que se restauran con un clic. Con el plan gratuito, esta copia de GitHub es la red de seguridad.

---

## Después: cómo actualizar

- **Web**: cada `git push` a `master` redespliega sola en Cloudflare (1–2 min). Puedes verlo en
  *Deployments*.
- **API**: en Cloud Shell:
  ```bash
  cd ~/Hourli-fy && git pull
  gcloud run deploy hourlify-api --source backend --region europe-west1 \
    --allow-unauthenticated --env-vars-file ~/hourlify-env.yaml --memory 512Mi --max-instances 2
  ```
  Si hay migraciones nuevas, se aplican solas al arrancar. Si el token de GitHub caducó,
  `git pull` lo pedirá otra vez: genera uno nuevo como en el paso 3.2.
- **Primero la API, luego la web** si un cambio toca a las dos (la web nueva puede usar rutas que
  la API vieja no tiene).

---

## Si algo falla

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `gcloud run deploy` falla en Cloud Build | Facturación sin vincular o APIs sin activar | Paso 3.1 y `gcloud services enable …` del 3.2 |
| `/api/health` responde 503 o la API no arranca | La BD no conecta | Logs (`gcloud run services logs read …`). Revisa `DATABASE_URL`: *Session pooler*, `postgresql+psycopg://`, contraseña sin símbolos, `?sslmode=require` |
| Logs: `password authentication failed` | Contraseña mal | Supabase → **Project Settings → Database → Reset database password** (solo letras y números), actualiza el yaml y 7.3 |
| Logs: `Network is unreachable` / IPv6 | Usaste la conexión directa | Cambia a la URL del **Session pooler** |
| La web dice "No se puede contactar con la API" | `API_ORIGIN` mal o sin redesplegar la web | Paso 4 (sin barra final) y *Retry deployment* |
| Login con email OK pero al recargar vuelves al login | Cookie no guardada | `COOKIE_SECURE: "true"` y `COOKIE_SAMESITE: "lax"`; entra siempre por `WEB_URL`, no por la URL de Cloud Run |
| Botón de Google: "origin is not allowed" / error 400 | Falta el origen en Google | Paso 5.2 (exacto, `https://`, sin barra). Espera 5 min |
| Google: "Acceso bloqueado: app en pruebas" | App sin publicar | Paso 5.4 |
| La API devuelve 503 en `/api/auth/google` | Falta `GOOGLE_CLIENT_ID` en la API | Añádelo al yaml y 7.3 |
| Admin: "acceso denegado" | Email no está en `ADMIN_EMAILS` o la cuenta no tiene contraseña | Revisa el yaml (lista JSON con comillas simples fuera) y pon contraseña en *Mi cuenta* |
| Cloudflare: el build falla con un error de Node | Versión de Node | `NODE_VERSION` = `22` en las variables |
| Supabase: el proyecto está en pausa | 7 días sin uso | Panel de Supabase → *Restore project* |

---

## Saber

- **Coste y límites gratuitos**: Supabase Free (500 MB de BD), Cloud Run (2 millones de
  peticiones/mes gratis), Cloudflare Pages (despliegues ilimitados; las Functions, 100.000
  peticiones/día). De sobra para un equipo.
- **Arranque en frío**: con `min-instances` a 0 (por defecto), la primera petición tras un rato sin
  uso tarda 3–5 s. Es gratis así; si molesta, `--min-instances 1` lo evita, pero cuesta unos
  euros al mes.
- **Freno de intentos de login**: se guarda en memoria de cada instancia, así que se reinicia
  cuando Cloud Run para o crea instancias. Para este uso basta.
- **Supabase Realtime** (fase 6, pendiente) se hará después del despliegue. Entonces habrá que
  revisar qué expone Supabase (RLS en `time_entries`) antes de activarlo.
