# Requisitos: lo que tienes que hacer tú

Cuentas, claves y decisiones que no puedo hacer por ti. Ordenado por **cuándo** hace falta.
Marca cada casilla al terminarla.

> **Nunca pegues claves ni contraseñas en el chat.** Van directamente en `backend/.env` (o en
> los secretos de Cloud Run al desplegar). En el chat dime solo "hecho".

---

## Ya (para desarrollar en local)

### Admins de `/admin`
- [ ] Añade a `backend/.env` los emails que podrán entrar al panel de admin, separados por comas:
  ```
  ADMIN_EMAILS=["tu-email@ejemplo.com"]
  ```
  Ese usuario tiene que existir en la app (haber entrado al menos una vez). Para usar el
  formulario de login del panel necesita contraseña (si entras con Google, ponla en Mi cuenta).
  Después reinicia la API. Coste: ninguno.

### Nada más
- En local, los emails de "recuperar contraseña" **no se envían**: aparecen en la consola de la
  API, con el link incluido, para que puedas probar el flujo completo. No hace falta ninguna
  cuenta todavía.

---

## Antes de desplegar (fase 5)

> **La guía completa, paso a paso, está en [DESPLIEGUE.md](DESPLIEGUE.md).** Esta sección es
> solo el resumen de cuentas que hacen falta.

### 1. Un dominio y acceso a su DNS
Hace falta para la web (`horas.tudominio.com`) y para que los correos no lleguen a spam.
- [ ] Decide el dominio o subdominio. Si es el de la empresa, averigua **quién gestiona su DNS**
      y pídele acceso o que añada los registros que le pasemos.
- Coste: ninguno si ya existe el dominio; si no, unos 10–15 €/año.

### 2. Resend (envío de emails de recuperación)
- [ ] Crea una cuenta en <https://resend.com> (plan gratuito: 3.000 emails/mes, 100/día).
- [ ] *Domains → Add domain* con tu dominio. Resend te dará unos registros DNS (SPF y DKIM) que
      hay que añadir en el DNS del punto 1. Hasta que estén verificados, solo puede enviar a tu
      propio email (sirve para probar).
- [ ] *API Keys → Create API key* con permiso **solo de envío** (*Sending access*).
- [ ] Guárdala en `backend/.env` (y luego en Cloud Run):
  ```
  RESEND_API_KEY=re_...
  EMAIL_FROM=Hourli-fy <no-responder@tudominio.com>
  ```

### 3. Google Cloud (para la API en Cloud Run)
- [ ] En el mismo proyecto donde creaste el OAuth Client ID, activa la **facturación** con una
      tarjeta (*Facturación*). Cloud Run tiene una capa gratuita amplia y para este uso
      seguramente no cobre nada, pero exige la tarjeta.
- [ ] Recomendado: crea un **presupuesto con alerta** (p. ej. 5 €) en *Facturación → Presupuestos*,
      para que te avise si algo se dispara.

### 4. Supabase (base de datos en producción)
- [ ] Crea una cuenta en <https://supabase.com> (plan gratuito).
- [ ] El proyecto lo creamos juntos (región UE y contraseña de la base de datos generada).
- Saber: el plan gratuito **pausa el proyecto tras 7 días sin uso**. Con gente registrando horas
  no pasará, pero en vacaciones podría.

### 5. Cloudflare (web en Cloudflare Pages)
- [ ] Crea una cuenta en <https://dash.cloudflare.com> (plan gratuito).
- [ ] Ten a mano el acceso a GitHub: Cloudflare Pages se conecta al repo `Hourli-fy`.

### 6. Pantalla de consentimiento de Google
- [ ] Al desplegar, añadiremos la URL de producción a los *orígenes autorizados* del OAuth
      Client ID y **publicaremos la app** (pasar de "Prueba" a "En producción").

---

## Decisiones y textos pendientes

- [ ] **Página de privacidad** (`frontend/src/pages/PrivacyPage.tsx`): rellenar
      `[NOMBRE O RAZÓN SOCIAL DEL RESPONSABLE]`, `[EMAIL DE CONTACTO]` y `[FECHA]`. Las
      `[REGIÓN]` las completamos al desplegar. (Ya menciona contraseñas, admins y Resend.)
- [ ] **Cronómetro**: al arrancar uno con otro en marcha, ¿se para el anterior (como ahora) o se
      bloquea y avisa?
- [ ] **Contraseñas**: he dejado como norma **mínimo 8 caracteres, sin más reglas** (es lo que
      recomienda hoy el NIST: longitud sí, "mayúscula + número + símbolo" no). Dime si quieres otra.

---

## Resumen de variables nuevas en `backend/.env`

| Variable | Cuándo | Ejemplo |
| --- | --- | --- |
| `ADMIN_EMAILS` | Ya | `["tu-email@ejemplo.com"]` |
| `RESEND_API_KEY` | Al desplegar (en local no hace falta) | `re_...` |
| `EMAIL_FROM` | Al desplegar | `Hourli-fy <no-responder@tudominio.com>` |

Todas estarán también en `backend/.env.example` (sin valores reales) cuando las añada al código.
