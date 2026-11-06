import { useEffect, useState } from 'react'

// Modo claro u oscuro. La elección se guarda en este navegador (localStorage); si nunca se ha
// elegido, se sigue al sistema. index.html aplica la clase `dark` antes de pintar, para que no
// se vea un destello blanco al cargar; aquí solo se lee y se cambia.
export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'theme'
const systemDark = () => window.matchMedia('(prefers-color-scheme: dark)')

export function storedTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null // modo privado o almacenamiento bloqueado
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.classList.contains('dark') ? 'dark' : 'light',
  )

  // Mientras no haya elección guardada, si el sistema cambia de modo, la app también.
  useEffect(() => {
    const media = systemDark()
    const onChange = () => {
      if (storedTheme() !== null) return
      const next = media.matches ? 'dark' : 'light'
      applyTheme(next)
      setTheme(next)
    }
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    applyTheme(next)
    setTheme(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Sin almacenamiento el cambio vale hasta recargar.
    }
  }

  return { theme, toggle }
}
