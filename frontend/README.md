# Frontend — Registro de horas

React 19 + TypeScript + Vite 8, Tailwind CSS v4, shadcn/ui y TanStack Query.

```bash
npm install
npm run dev      # http://localhost:5173 (necesita la API en :8000)
npm run lint     # ESLint
npm run build    # comprobación de tipos + build de producción en dist/
```

## Estructura

```
src/
├── main.tsx            monta la app dentro de QueryClientProvider y BrowserRouter
├── App.tsx             rutas; sin sesión muestra el login (salvo /invite/:token, que es pública)
├── index.css           Tailwind + tema de shadcn (variables CSS)
├── pages/
│   ├── LoginPage.tsx       botón de Google
│   ├── WorkspacesPage.tsx  /               mis espacios + crear uno
│   ├── WorkspacePage.tsx   pestañas del espacio: /w/:wid (Proyectos), /hoja (Mi hoja), /panel (dueño),
│   │                       /catalogo (proyectos y labels), /equipo (ajustes y borrar espacio,
│   │                       miembros y permisos por proyecto, invitaciones al espacio o a un proyecto)
│   ├── ProjectSheetPage.tsx  /w/:wid/p/:pid  hoja de un proyecto: nueva tarea y mis tareas por día
│   ├── AccountPage.tsx     /cuenta         mis datos, contraseña y eliminar la cuenta
│   ├── PasswordRecoveryPages.tsx  /recuperar y /recuperar/:token (públicas)
│   ├── PrivacyPage.tsx     /privacidad     política de privacidad (pública; borrador)
│   └── InvitePage.tsx      /invite/:token  ver y aceptar una invitación
├── lib/
│   ├── api.ts          apiGet/apiPost/apiPatch/apiDelete con cookies; ApiError con el detail de FastAPI
│   ├── auth.ts         useMe(): usuario de la sesión o null
│   ├── types.ts        tipos de las respuestas (espejo de backend/app/schemas.py)
│   ├── time.ts         fechas en hora de España (dayKey 'AAAA-MM-DD', semanas, quincenas, local → UTC)
│   ├── catalog.ts      useCatalog(): proyectos y labels con búsqueda por id
│   ├── entries.ts      useCurrentTimer(), useNow() y refresco tras cambios
│   ├── reports.ts      tipos del panel
│   └── utils.ts        cn() para combinar clases de Tailwind
└── components/
    ├── auth/AuthPanel.tsx  entrar / crear cuenta con email y contraseña (+ Google si está configurado)
    ├── GoogleLoginButton.tsx  carga Google Identity Services y manda el ID token a la API
    ├── catalog/        ProjectsCard, CategoriesCard (labels + sublabels) e ItemActions (renombrar, archivar, crear)
    ├── entries/        TimerBar (cabecera), TaskForm, EntryRow, LabelPicker, ProjectLinks, TimesheetCard
    ├── reports/        ReportPanel (filtros, totales, lista) y DailyHoursChart (gráfica SVG por día)
    ├── NativeSelect.tsx  <select> nativo con el estilo de <Input>
    └── ui/             componentes de shadcn (se añaden con `npx shadcn@latest add <nombre>`)
```

## Decisiones

- **Proxy de Vite** (`vite.config.ts`): en desarrollo, `/api/*` se reenvía a `http://127.0.0.1:8000`.
  El navegador ve un único origen, así que no hace falta CORS y la cookie de login (Fase 1) funciona sin más.
- **`VITE_API_URL`**: vacío en local y en producción. En producción la web y la API van en el
  mismo servicio de Cloud Run (la API sirve el `dist`), así que `/api` es del mismo origen.
- **`VITE_ADMIN_URL`**: vacío normalmente (`/admin/` del mismo dominio).
- **`VITE_GOOGLE_CLIENT_ID`** (`frontend/.env`, opcional): el mismo Client ID que `GOOGLE_CLIENT_ID`
  del backend. Si falta, el botón de Google no aparece y se entra con email y contraseña.
- **Proxy de `/admin`** con `changeOrigin: false`: SQLAdmin construye sus links con la cabecera
  `Host`; si el proxy la cambiara a `127.0.0.1:8000`, el navegador saldría del origen del front
  y perdería la cookie de sesión.
- **React Router** (`react-router`) para las páginas. La invitación tiene su propia página:
  si no hay sesión, el botón de Google sale ahí mismo y tras entrar sigues en la invitación.
- **Horas siempre en España**: la API habla en UTC y `lib/time.ts` convierte con `Intl` y la zona
  `Europe/Madrid`, así que todo funciona igual aunque el navegador esté en otra zona horaria.
- **El cronómetro lo lleva el servidor**: el front solo pinta `ahora - inicio` cada segundo, así
  que sobrevive a recargar la página o a cambiar de equipo.
- **Gráficas sin librería**: `DailyHoursChart` es SVG a mano (una serie, un color `--series-1`,
  barras finas, tooltip también con teclado y botón "Ver como tabla"). La paleta de colores de
  proyectos es la de referencia de dataviz, validada para daltonismo.
- **Sesión en cookie `httpOnly`**: el front no guarda tokens; pregunta `/auth/me` para saber quién es.
  Al salir se vacía la caché de TanStack Query para no mostrar datos de la sesión anterior.
- **TanStack Query** gestiona las peticiones: caché, estados de carga/error y reintentos sin escribirlos a mano.
- **Alias `@/`** = `src/` (configurado en `vite.config.ts` y `tsconfig*.json`; lo exige shadcn).
- **ESLint en vez de oxlint** (el que trae la plantilla de Vite 8): oxlint usa un binario nativo que
  Smart App Control de Windows bloquea en este equipo.
- **`cn`**: shadcn instala ahora el paquete oficial `cn` (repo `shadcn-ui/cn`) en lugar de `clsx` + `tailwind-merge`.
