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
├── main.tsx            monta la app dentro de QueryClientProvider
├── App.tsx             pantalla inicial (estado de la API)
├── index.css           Tailwind + tema de shadcn (variables CSS)
├── lib/
│   ├── api.ts          apiGet(): fetch a /api con cookies
│   └── utils.ts        cn() para combinar clases de Tailwind
└── components/ui/      componentes de shadcn (se añaden con `npx shadcn@latest add <nombre>`)
```

## Decisiones

- **Proxy de Vite** (`vite.config.ts`): en desarrollo, `/api/*` se reenvía a `http://127.0.0.1:8000`.
  El navegador ve un único origen, así que no hace falta CORS y la cookie de login (Fase 1) funciona sin más.
- **`VITE_API_URL`**: vacío en local. En producción (Cloudflare Pages) será la URL del backend en Cloud Run.
- **TanStack Query** gestiona las peticiones: caché, estados de carga/error y reintentos sin escribirlos a mano.
- **Alias `@/`** = `src/` (configurado en `vite.config.ts` y `tsconfig*.json`; lo exige shadcn).
- **ESLint en vez de oxlint** (el que trae la plantilla de Vite 8): oxlint usa un binario nativo que
  Smart App Control de Windows bloquea en este equipo.
- **`cn`**: shadcn instala ahora el paquete oficial `cn` (repo `shadcn-ui/cn`) en lugar de `clsx` + `tailwind-merge`.
