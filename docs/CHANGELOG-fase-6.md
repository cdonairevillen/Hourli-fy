# Changelog — Fase 6 (parte): gráficas del panel

Fase 6 del plan ("Extra"). El changelog general está en [CHANGELOG.md](CHANGELOG.md).

> La fase 6 tenía dos partes: **gráficas** (hecha) y **actividad en vivo con Supabase Realtime**
> (pendiente). Realtime necesita el proyecto de Supabase, que crearemos al desplegar, así que se
> queda para después de la fase 5.

## Resumen rápido

- **Horas por día** en el panel: una gráfica de columnas con un día por columna en el periodo
  filtrado. Al pasar el ratón (o el foco del teclado) por un día se ven sus horas, y el botón
  **"Ver como tabla"** muestra los mismos valores sin depender del ratón.
- **Barras de reparto** en las tarjetas *Por persona*, *Por proyecto* y *Por label*: una barra
  fina proporcional bajo cada fila, junto al número y el %.
- **Nueva paleta de colores para proyectos**, validada para daltonismo.

## Lo que tienes que saber

1. **La paleta de proyectos de la fase 2 no pasaba el validador de daltonismo**: el turquesa y el
   rosa se confundían con deuteranopía (diferencia 3,7, cuando el mínimo es 8) y el gris casi no
   tenía color. La he sustituido por la paleta de referencia, que pasa todas las comprobaciones.
   **Los proyectos ya creados conservan su color**; solo cambian las opciones al crear o editar, y
   el color por defecto (`#2a78d6`).
2. **La he mirado dibujada**: la monté en una página de prueba fuera del repo (en mi carpeta
   temporal) y le hice una captura con Edge, en modo claro y oscuro. No queda nada de esa prueba
   en el proyecto.
3. **Para rangos de más de 62 días** no se dibuja la gráfica por días (las columnas serían
   demasiado finas); se muestra un aviso y el resto del panel funciona igual.

## Cambios

### frontend
- `components/reports/DailyHoursChart.tsx`: gráfica SVG hecha a mano, sin librerías.
  - Una sola serie y un solo color (`--series-1`), sin leyenda (el título dice qué es).
  - Columnas de 24 px de ancho como máximo, esquinas de arriba redondeadas y base recta sobre el eje.
  - Cuadrícula de líneas finas y continuas, y eje Y en horas redondas (0, 4, 8, 12…).
  - Las etiquetas del eje X se espacian solas si hay muchos días.
  - La zona de hover es la columna entera del día, no solo la barra; con teclado (Tab) funciona igual.
  - Mientras se recargan datos, la gráfica anterior se queda atenuada en vez de parpadear.
- `ReportPanel`: la gráfica bajo el total, y las barras de reparto en `TotalsCard`.
- `index.css`: token `--series-1` (azul `#2a78d6` en claro, `#3987e5` en oscuro).
- `components/catalog/ProjectsCard.tsx`: paleta validada (azul, naranja, aqua, amarillo, magenta,
  verde, violeta, rojo, en ese orden).

### backend
- `app/schemas.py`: el color por defecto de un proyecto pasa a `#2a78d6` (el primero de la paleta).

**Decisiones que conviene entender:**
- **Sin librería de gráficas**: para unas columnas y unas barras, un SVG de ~150 líneas pesa menos
  que cualquier librería y se controla todo (accesibilidad, colores, modo oscuro).
- **Un solo color en "horas por día"**: es una sola magnitud. Colorear cada columna distinta
  haría pensar que significan cosas diferentes.
- **El color de cada proyecto es su identidad**: en "Por proyecto" la barra usa el color del
  proyecto, el mismo de su punto en el resto de la app.
- **El texto nunca va en el color de la serie**: los nombres y valores van en los colores de texto
  normales; el color lo lleva la barra.
- **Ningún valor depende solo del tooltip**: "Ver como tabla" y las tarjetas de reparto los dan
  siempre a la vista.

## Pendiente de la fase 6

- [ ] **Actividad en vivo** (Supabase Realtime sobre `time_entries`): que el dueño vea quién tiene
      el cronómetro en marcha sin recargar. Tras el despliegue, con Supabase ya creado.

## Commits propuestos (fases 3 a 6)

Nada de esto está commiteado. La **fase 3 tampoco**: sigue sin commitear desde el día 5.

Algunos ficheros se tocaron en varias fases (`backend/app/schemas.py`, `backend/app/main.py`,
`frontend/src/App.tsx`, `frontend/src/pages/WorkspacePage.tsx`, los README…), así que no se pueden
separar por fase solo eligiendo ficheros. Dos opciones:

- **Un commit por fase** con `git add -p` (eliges los trozos de cada fichero). Es lo más limpio,
  pero lleva un rato.
- **Por capas**, que es lo que te propongo:
  1. `infra: Postgres solo en 127.0.0.1 y DATABASE_URL sin localhost`
     `docker-compose.yml`, `backend/.env.example`, `backend/app/core/config.py`
  2. `backend: tareas, cronómetro, panel del dueño y eliminar cuenta (fases 3-5), con migraciones y tests`
     `backend/` (menos lo del commit 1), `specs/api/openapi.yaml`
  3. `frontend: hoja de proyecto, cronómetro, mi hoja, panel con gráficas, mi cuenta y privacidad (fases 3-6)`
     `frontend/src/`
  4. `docs: changelogs de las fases 3 a 6, README detallado y comandos con python -m`
     `docs/`, `README.md`, `backend/README.md`, `frontend/README.md`, `CLAUDE.md`
