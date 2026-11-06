# Changelog — Fase 9: peticiones de los usuarios

Primera tanda de cambios pedidos por quienes ya usan la app desplegada (Cloud Run + Supabase). El
changelog general está en [CHANGELOG.md](CHANGELOG.md).

## Plan y decisiones del autor (2026-11-06)

| # | Paso | Decisión | Estado |
| --- | --- | --- | --- |
| 1 | Primeras copias de seguridad de la BD | Activar el workflow que ya existía y probar a restaurar | ✅ Hecho |
| 2 | Modo oscuro con interruptor | Preferencia guardada en el navegador; la primera vez sigue al sistema | ✅ Hecho |
| 3 | Periodos de 14 días en vez de quincenas A/B | Bloques seguidos de 14 días contados desde el **sábado 7-nov-2026** | ✅ Hecho |
| 4 | Autocompletar al escribir una tarea | Tareas del propio trabajador en ese proyecto; rellena también label y sublabel | ✅ Hecho |
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

## Paso 3 · Periodos de 14 días

### La regla que cambia
- **Antes**: quincenas pegadas al mes. A = días 1–15, B = del 16 al último día.
- **Ahora**: bloques de **14 días seguidos** contados desde el **sábado 7-nov-2026**, hacia
  delante y hacia atrás: 7–20 nov, 21 nov–4 dic, 5–18 dic… y antes, 24 oct–6 nov, 10–23 oct…
  Cada bloque va de sábado a viernes. No dependen del mes, así que cruzan meses y años
  (19 dic 2026 – 1 ene 2027) y ningún día queda fuera.
- **No cambia**: una tarea cuenta en el día (de España) en que empieza. Los datos guardados no se
  tocan: solo cambia cómo se agrupan al verlos.

### Lo que hay que saber
1. **La API cambia**: `period=2026-10-A` ya no vale (da 422). Ahora `period=AAAA-MM-DD` es
   **cualquier día** del periodo y devuelve el bloque que lo contiene (`period=2026-11-12` →
   7–20 nov). Sin `period` ni `from`/`to`, el periodo actual. Web y API se despliegan juntas, así
   que no hay clientes con el formato viejo.
2. **Los periodos antiguos ya no coinciden con el mes.** Para ver "octubre entero" o una quincena
   antigua, usa *Rango de fechas* en el panel.
3. **Mi hoja también** usa los mismos periodos (antes, quincenas), para que coincida con el panel.
   El botón se llama ahora **"2 semanas"** en los dos sitios, y la etiqueta muestra las fechas
   (*7 nov – 20 nov 2026*).
4. **La fecha de inicio está en dos sitios**, que deben coincidir: `PERIOD_START` en
   `backend/app/services/reports.py` y en `frontend/src/lib/time.ts`. Cambiarla mueve todos los
   periodos, también los pasados.
5. **Sobre el día 31**: con las quincenas no se perdía (la B llegaba al último día del mes). Con
   los bloques seguidos la duda desaparece del todo.

### Por qué así
- La cuenta se hace con días enteros (`(día − inicio) // 14`, redondeando hacia abajo también con
  negativos). Así no hay que guardar nada en la BD ni crear periodos a mano, y los anteriores al
  7-nov salen solos.
- `period` acepta cualquier día del bloque, y no solo el primero, para que pedir "el periodo de hoy"
  sea simplemente `period=<hoy>`.

### Cambios
- **backend**:
  - `services/reports.py`: `PERIOD_START`, `period_containing()` y `current_period()` sustituyen
    a `fortnight_range()` y `current_fortnight()`; `resolve_period` acepta una fecha.
  - `api/reports.py`: nueva descripción de `period`.
  - Comentarios en `api/entries.py` y `services/entries.py`.
- **tests**:
  - `test_reports.py`: los tests de quincenas pasan a periodos.
  - Test nuevo `test_periodos_de_14_dias_seguidos`: inicio, días anteriores, cruce de mes y año.
  - El formato viejo da 422.
  - El caso del límite pasa a 9/10-oct.
  - `test_account.py` y `test_project_access.py` usan el nuevo formato.
  - **171 tests en verde.**
- **frontend**:
  - `lib/time.ts`: `fortnightOf()` calcula el bloque de 14 días (*fortnight* = 14 noches, así
    que el nombre sigue siendo correcto).
  - `ReportPanel.tsx` envía `period=<inicio>`.
  - Botón "2 semanas" en el panel y en Mi hoja.
  - Comprobado: lint y build en verde; la función da los mismos bloques que el backend
    (7-nov, 6-nov, 31-dic, cambios de hora).
- **docs**:
  - `CLAUDE.md`: regla de los periodos.
  - `README.md`, `backend/README.md` y `frontend/README.md`.
  - `specs/api/openapi.yaml` regenerado.
  - Pendiente: la especificación (Claude Doc) sigue hablando de quincenas.

### Commit propuesto
```
periodos: bloques de 14 días seguidos desde el 7-nov-2026 en vez de quincenas A/B

- backend: period=AAAA-MM-DD (periodo que contiene ese día), tests adaptados y nuevos
- front: panel y Mi hoja con periodos de 14 días ("2 semanas")
- CLAUDE.md, README y openapi con la nueva regla
```
Archivos:
- backend: `backend/app/services/reports.py`, `backend/app/api/reports.py`,
  `backend/app/api/entries.py`, `backend/app/services/entries.py`
- tests: `backend/tests/test_reports.py`, `backend/tests/test_account.py`,
  `backend/tests/test_project_access.py`
- frontend: `frontend/src/lib/time.ts`, `frontend/src/components/reports/ReportPanel.tsx`,
  `frontend/src/components/entries/TimesheetCard.tsx`, `frontend/src/pages/WorkspacePage.tsx`
- docs: `CLAUDE.md`, `README.md`, `backend/README.md`, `frontend/README.md`,
  `specs/api/openapi.yaml`, `docs/CHANGELOG-fase-9.md`, `docs/CHANGELOG.md`

## Paso 4 · Autocompletar al escribir una tarea

### Cómo funciona
- **Mientras escribes el nombre de una tarea** en la hoja de un proyecto, aparece una lista con las
  tareas que **tú** ya has hecho en **ese proyecto**. Al lado de cada una se ve su label
  ("Acto 1 › Personajes").
- **Al elegir una se rellenan también su label y su sublabel**, las de la última vez que la usaste.
  Si esa label o sublabel se ha archivado, solo se aprovecha el nombre (o se queda sin sublabel).
- **Los títulos no se repiten** aunque cambien las mayúsculas ("Reunión" y "reunión" salen una
  vez, con la forma más reciente). Salen primero los más recientes, hasta 50.
- **Lo que escriben los demás no se ve** (decisión del autor): las sugerencias son solo tuyas.
- **Tras guardar una tarea, la lista se actualiza sola.**

### Por qué así
- **Una ruta nueva y no la lista de registros que ya había**: esa lista trae todos los registros
  con fechas; para sugerir solo hacen falta los títulos distintos. Postgres los saca de una vez con
  `DISTINCT ON (lower(title))`, quedándose con la fila más reciente de cada título.
- **`<datalist>` del navegador** en vez de un desplegable hecho a mano: el navegador ya filtra
  mientras se escribe, se maneja con el teclado, funciona en el móvil y sigue el modo oscuro. Se
  pide la lista una vez por proyecto, no en cada tecla. El precio es que el aspecto de la lista lo
  decide cada navegador. Si un día se quiere otro diseño, la ruta ya admite `q` para filtrar en el
  servidor.
- `autoComplete="off"` quita el autocompletado propio del navegador, que se mezclaría con este.

### Cambios
- **backend**:
  - `GET /api/workspaces/{wid}/entries/suggestions?project_id=&q=&limit=` en `api/entries.py`.
    `project_id` es obligatorio; un proyecto sin acceso o un espacio ajeno da 404.
  - Esquema `TaskSuggestion` en `schemas.py`.
- **tests**: `tests/test_suggestions.py` (4 tests nuevos):
  - sin repetir, con mayúsculas distintas y la label del último uso;
  - solo las mías y solo de ese proyecto;
  - filtro `q` (el `%` se busca literal) y `limit`;
  - 404 sin acceso o desde fuera, y 422 sin `project_id`.
  - **175 tests en verde.** `ruff check` y `ruff format` limpios: la línea larga de `api/reports.py`
    del paso 3 ya está corregida.
- **frontend**:
  - `components/entries/TaskForm.tsx`: el `datalist` y el relleno de label/sublabel.
  - `lib/types.ts`: tipo `TaskSuggestion`.
  - Lint y build en verde.
- **docs**: `backend/README.md` (tabla de rutas), `README.md` y `specs/api/openapi.yaml`
  regenerado.

### Commit propuesto
```
tareas: autocompletar el nombre con mis tareas anteriores del proyecto

- GET /workspaces/{wid}/entries/suggestions (DISTINCT ON por título, label del último uso)
- TaskForm: datalist y relleno de label/sublabel al elegir
- 4 tests nuevos; ruff format de api/reports.py
```
Archivos:
- backend: `backend/app/api/entries.py`, `backend/app/api/reports.py`, `backend/app/schemas.py`
- tests: `backend/tests/test_suggestions.py`
- frontend: `frontend/src/components/entries/TaskForm.tsx`, `frontend/src/lib/types.ts`
- docs: `backend/README.md`, `README.md`, `specs/api/openapi.yaml`, `docs/CHANGELOG-fase-9.md`,
  `docs/CHANGELOG.md`
