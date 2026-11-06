// Ventanita aparte para el cronómetro.
// - Chrome y Edge: Document Picture-in-Picture, una ventana que queda SIEMPRE encima de las demás
//   aplicaciones (Excel, Blender…), como el vídeo flotante de YouTube.
// - Resto (Firefox, Safari): una ventana emergente pequeña normal; se queda detrás si se hace clic
//   en otra aplicación.
// En los dos casos es una ventana vacía del mismo origen: React pinta dentro con createPortal,
// así que comparte datos (TanStack Query) y lógica con la pestaña principal.

type DocumentPictureInPicture = {
  requestWindow(options: { width: number; height: number }): Promise<Window>
}

const WIDTH = 340
const HEIGHT = 150

function pictureInPicture(): DocumentPictureInPicture | undefined {
  return (window as unknown as { documentPictureInPicture?: DocumentPictureInPicture })
    .documentPictureInPicture
}

export function supportsAlwaysOnTop(): boolean {
  return pictureInPicture() !== undefined
}

// La ventana nueva nace sin estilos: se le copian los de la página (Tailwind) y el modo oscuro.
function copyStyles(target: Window) {
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      const style = target.document.createElement('style')
      style.textContent = Array.from(sheet.cssRules)
        .map((rule) => rule.cssText)
        .join('\n')
      target.document.head.appendChild(style)
    } catch {
      // Hoja de otro origen (no se pueden leer sus reglas): se enlaza tal cual.
      if (sheet.href) {
        const link = target.document.createElement('link')
        link.rel = 'stylesheet'
        link.href = sheet.href
        target.document.head.appendChild(link)
      }
    }
  }
  target.document.title = 'Cronómetro · Hourli-fy'
  target.document.body.className = 'bg-background text-foreground'
}

// El modo claro/oscuro sigue al de la pestaña principal mientras la ventanita esté abierta.
function syncTheme(target: Window): () => void {
  const apply = () => {
    target.document.documentElement.className = document.documentElement.className
  }
  apply()
  const observer = new MutationObserver(apply)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  return () => observer.disconnect()
}

// Abre la ventanita (tiene que llamarse desde un clic: los navegadores lo exigen).
// Devuelve null si el navegador la bloquea. `onClose` se llama cuando el usuario la cierra.
export async function openFloatingWindow(onClose: () => void): Promise<Window | null> {
  const pip = pictureInPicture()
  let target: Window | null
  if (pip) {
    target = await pip.requestWindow({ width: WIDTH, height: HEIGHT })
  } else {
    target = window.open('', 'hourlify-cronometro', `popup,width=${WIDTH},height=${HEIGHT}`)
    // Si ya estaba abierta de antes, se vacía para no pintar dos veces.
    if (target) target.document.body.replaceChildren()
  }
  if (!target) return null
  copyStyles(target)
  const stopSync = syncTheme(target)
  const opened = target
  let closed = false
  const handleClose = () => {
    if (closed) return
    closed = true
    clearInterval(watcher)
    stopSync()
    onClose()
  }
  // Al cerrar una ventana emergente no siempre llega 'pagehide': se comprueba también cada segundo.
  const watcher = setInterval(() => {
    if (opened.closed) handleClose()
  }, 1000)
  opened.addEventListener('pagehide', handleClose)
  return opened
}
