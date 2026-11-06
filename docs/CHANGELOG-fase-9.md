# Changelog — Fase 9: peticiones de los usuarios

Primera tanda de cambios pedidos por quienes ya usan la app desplegada (Cloud Run + Supabase). El
changelog general está en [CHANGELOG.md](CHANGELOG.md).

## Plan y decisiones del autor (2026-11-06)

| # | Paso | Decisión | Estado |
| --- | --- | --- | --- |
| 1 | Primeras copias de seguridad de la BD | Activar el workflow que ya existía y probar a restaurar | ✅ Hecho |
| 2 | Modo oscuro con interruptor | Preferencia guardada en el navegador; la primera vez sigue al sistema | ✅ Hecho (falta revisarlo a ojo) |
| 3 | Periodos de 14 días en vez de quincenas A/B | Bloques seguidos de 14 días contados desde el **sábado 7-nov-2026** | Pendiente |
| 4 | Autocompletar al escribir una tarea | Tareas del propio trabajador en ese proyecto; rellena también label y sublabel | Pendiente |
| 5 | Ventanita flotante con el cronómetro | Picture-in-Picture en Chrome/Edge, ventana emergente en el resto, y tiempo en la pestaña | Pendiente |
| 6 | Desplegar y comprobar en producción | — | Pendiente |

Otras decisiones:
- **Se trabaja en `main`** (antes `master`). `main` ya contenía todo `master` (PR #1). La base de
  datos no depende de la rama: Cloud Run despliega lo que haya en la carpeta de Cloud Shell, así
  que allí hay que tener `main` antes de desplegar.
- **Sobre el día 31**: con las quincenas actuales no se perdía (la B va del 16 al último día del
  mes), pero con bloques de 14 días seguidos la duda desaparece: ningún día queda fuera.

## Paso 1 · Primeras copias de seguridad

### Qué se hizo
- Secretos `SUPABASE_DB_URL` y `BACKUP_PASSPHRASE` creados en GitHub y primera copia lanzada a mano
  (`hourlify-2026-11-06-2057.dump.gpg`). Desde ahora se hace sola cada día a las 03:00 UTC.
- **Restauración probada** en una BD aparte del Postgres local (`restore_test`, ya borrada):
  13 usuarios, 2 espacios, 13 miembros, 2 proyectos, 14 labels, 63 sublabels, 136 tareas, última
  migración `e000194eb176`. La copia sirve.
- La copia cifrada se guardó fuera del repo (`Documentos/hourlify-copias/`); la descifrada se
  borró.

### Lo que salió en la prueba (y se ha corregido)
1. **Salto de línea en el secreto.** La primera ejecución falló con
   `invalid sslmode value: "require⏎"`: al copiar la URL de Cloud Shell se coló un salto de línea.
   Se corrigió el secreto y, además, el workflow ahora quita espacios y saltos al principio y al
   final de los dos secretos.
2. **Restaurar en una BD vacía no crea la restricción anti-solapes.** Supabase guarda la extensión
   `btree_gist` en el esquema `extensions`, que la copia no incluye (solo `public`). Sobre la
   propia Supabase no pasa nada (la extensión ya está), pero en un proyecto nuevo sí. La guía
   ahora dice que se cree antes de restaurar.
3. **Las copias no estaban en `.gitignore`**: un `git add .` las habría subido.

### Cambios
- `.github/workflows/backup-db.yml`: recorta los secretos antes de usarlos.
- `.gitignore`: ignora `*.dump` y `*.dump.gpg`.
- `docs/DESPLIEGUE.md`:
  - 8.1: la rama por defecto es `main`; aviso del salto de línea al pegar secretos.
  - 8.2: crear `btree_gist` antes de restaurar en una BD vacía; no dejar la copia descifrada en
    el repo.
  - "Cómo actualizar": `git checkout main` antes de `git pull` en Cloud Shell.
  - Se recupera la plantilla `https://hourlify-api-NÚMERO.europe-west1.run.app` donde había quedado
    `[vieja url expuesta]` (la plantilla no revela la URL real) y el nombre real de la migración
    (`e000194eb176`) en la comprobación del paso 3.5.

### Commit propuesto
```
copias: primera copia probada, secretos recortados y guía de restauración

- backup-db.yml quita espacios/saltos de los secretos
- .gitignore ignora *.dump y *.dump.gpg
- DESPLIEGUE.md: rama main, btree_gist al restaurar en BD vacía, plantilla de URL
- CHANGELOG-fase-9.md con el plan de la fase y el paso 1
```
Archivos: `.github/workflows/backup-db.yml`, `.gitignore`, `docs/DESPLIEGUE.md`,
`docs/CHANGELOG-fase-9.md`, `docs/CHANGELOG.md`.

## Paso 2 · Modo oscuro

### Cómo funciona
- **Botón luna/sol** en la cabecera, junto a "Salir". Cambia al momento y se recuerda en ese
  navegador (`localStorage`, clave `theme`). Cada dispositivo tiene su propia elección.
- **Si nunca se ha pulsado, sigue al sistema** (Windows/macOS/móvil en oscuro → app en oscuro), y si
  el sistema cambia con la app abierta, la app también.
- **Sin destello blanco al cargar**: un script pequeño en `index.html` pone la clase `dark` antes de
  que React pinte nada.
- Las pantallas sin cabecera (login, invitación, privacidad) no tienen botón, pero respetan la
  elección guardada o el modo del sistema.

### Por qué así
- shadcn/ui ya traía todos los colores del modo oscuro (`.dark` en `index.css`) y la gráfica del
  panel ya tenía su azul para fondo oscuro: solo faltaba poner y quitar la clase `dark`.
- `color-scheme: dark` hace que el calendario, el reloj y los desplegables nativos del navegador
  (los `<input type="date">`, `type="time"` y `<select>`) también salgan oscuros; sin eso se verían
  blancos en medio de la página.
- Guardarlo en el navegador evita migración, ruta y test en el backend (decisión del autor).

### Cambios (solo frontend)
- `src/lib/theme.ts` (nuevo): leer, aplicar y cambiar el modo (`useTheme`).
- `src/components/ThemeToggle.tsx` (nuevo): el botón.
- `src/App.tsx`: el botón en la cabecera.
- `index.html`: script que aplica el modo antes de pintar.
- `src/index.css`: `color-scheme: dark` en `.dark`.
- `npm run lint` y `npm run build` en verde. **Pendiente**: revisarlo a ojo en todas las pantallas.

### Commit propuesto
```
front: modo oscuro con interruptor en la cabecera

- useTheme guarda la elección en el navegador; sin elección sigue al sistema
- index.html aplica el modo antes de pintar (sin destello)
- color-scheme: dark para los controles nativos
```
Archivos: `frontend/src/lib/theme.ts`, `frontend/src/components/ThemeToggle.tsx`,
`frontend/src/App.tsx`, `frontend/index.html`, `frontend/src/index.css`,
`docs/CHANGELOG-fase-9.md`, `docs/CHANGELOG.md`.
