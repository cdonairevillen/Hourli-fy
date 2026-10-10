// Cloudflare Pages Function: reenvía /api/* a la API en Cloud Run (variable API_ORIGIN).
// Así el navegador solo habla con el dominio de la web, igual que con el proxy de Vite en local:
// la cookie de sesión es del propio dominio (Safari y los bloqueadores no la tiran) y no hay CORS.
export async function onRequest({ request, env }) {
  const url = new URL(request.url)
  const target = new URL(url.pathname + url.search, env.API_ORIGIN)
  // redirect: 'manual' para que una redirección de la API llegue tal cual al navegador.
  return fetch(new Request(target, request), { redirect: 'manual' })
}
