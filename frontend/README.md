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
│   ├── WorkspacePage.tsx   /w/:wid         pestaña Equipo: ajustes, miembros, invitaciones
│   │                       /w/:wid/catalogo  pestaña Catálogo: proyectos y labels
│   └── InvitePage.tsx      /invite/:token  ver y aceptar una invitación
├── lib/
│   ├── api.ts          apiGet/apiPost/apiPatch/apiDelete con cookies; ApiError con el detail de FastAPI
│   ├── auth.ts         useMe(): usuario de la sesión o null
│   ├── types.ts        tipos de las respuestas (espejo de backend/app/schemas.py)
│   └── utils.ts        cn() para combinar clases de Tailwind
└── components/
    ├── GoogleLoginButton.tsx  carga Google Identity Services y manda el ID token a la API
    ├── catalog/        ProjectsCard, CategoriesCard (labels + sublabels) e ItemActions (renombrar, archivar, crear)
    └── ui/             componentes de shadcn (se añaden con `npx shadcn@latest add <nombre>`)
```

## Decisiones

- **Proxy de Vite** (`vite.config.ts`): en desarrollo, `/api/*` se reenvía a `http://127.0.0.1:8000`.
  El navegador ve un único origen, así que no hace falta CORS y la cookie de login (Fase 1) funciona sin más.
- **`VITE_API_URL`**: vacío en local. En producción (Cloudflare Pages) será la URL del backend en Cloud Run.
- **`VITE_GOOGLE_CLIENT_ID`** (`frontend/.env`): el mismo Client ID que `GOOGLE_CLIENT_ID` del backend.
- **React Router** (`react-router`) para las páginas. La invitación tiene su propia página:
  si no hay sesión, el botón de Google sale ahí mismo y tras entrar sigues en la invitación.
- **Sesión en cookie `httpOnly`**: el front no guarda tokens; pregunta `/auth/me` para saber quién es.
  Al salir se vacía la caché de TanStack Query para no mostrar datos de la sesión anterior.
- **TanStack Query** gestiona las peticiones: caché, estados de carga/error y reintentos sin escribirlos a mano.
- **Alias `@/`** = `src/` (configurado en `vite.config.ts` y `tsconfig*.json`; lo exige shadcn).
- **ESLint en vez de oxlint** (el que trae la plantilla de Vite 8): oxlint usa un binario nativo que
  Smart App Control de Windows bloquea en este equipo.
- **`cn`**: shadcn instala ahora el paquete oficial `cn` (repo `shadcn-ui/cn`) en lugar de `clsx` + `tailwind-merge`.
