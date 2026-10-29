# Changelog — Fase 3: registro de tareas, cronómetro y hoja de horas

Fase 3 del plan ("Registro"). El changelog general está en [CHANGELOG.md](CHANGELOG.md).

> Esta fase la hice mientras estabas en una reunión, con tu permiso para no esperar a que
> aprobaras el plan. Las decisiones de diseño están explicadas abajo: si alguna no te encaja,
> la cambiamos.

## Resumen rápido

- Un espacio tiene ahora cuatro pestañas: **Proyectos** (la de entrada), **Mi hoja**, **Catálogo**
  y **Equipo**.
- **Proyectos** → cada proyecto abre **su hoja de tareas** (`/w/:wid/p/:pid`). Ahí escribes qué
  has hecho ("Animaciones de personajes Pepe y Juan"), eliges label y sublabel (opcional) y:
  - pulsas **▶ Iniciar cronómetro**, o
  - apuntas **a mano** el día y las horas, y pulsas **Añadir**.

  Todo lo que registras ahí queda ligado a ese proyecto sin elegirlo.
- Debajo, **tus tareas** de ese proyecto agrupadas por día, con el total diario. Cada una se puede
  **editar** en línea o **borrar**.
- **Cronómetro en la cabecera**: siempre visible, con el tiempo corriendo y el botón **Parar**,
  estés en la página que estés.
- **Mi hoja**: tus horas del espacio por **quincena** (A = 1–15, B = 16–fin de mes) o por
  **semana**, como una hoja de cálculo. Filas = proyecto · label, columnas = días, con totales.
- 33 tests nuevos (92 en total), todos en verde.

## Lo que tienes que saber

1. **Migración nueva** (`e442082a8fa8`): tabla `time_entries` y la extensión `btree_gist`. Ya
   está aplicada a tu Postgres local.
2. **He cambiado `DATABASE_URL` de `localhost` a `127.0.0.1`**, en tu `backend/.env`, en el
   `.env.example` y en el valor por defecto de `config.py`. Después de limitar Docker a tu equipo
   (`127.0.0.1:5432`), Windows probaba primero `localhost` por IPv6 (`::1`), y Docker Desktop
   aceptaba la conexión pero nunca la contestaba: Alembic se quedaba colgado. Con `127.0.0.1`
   conecta al instante. Es el mismo problema que ya resolvimos en el proxy de Vite.
3. **Docker**: `docker-compose.yml` publica Postgres solo en `127.0.0.1:5432`. Ya recreé el
   contenedor y tus datos siguen ahí, porque viven en el volumen.
4. **Pregunta sin responder en la spec**: al arrancar un cronómetro con otro en marcha, ¿se para
   el anterior (como Clockify) o se avisa y se bloquea? He dejado lo que proponía la spec: **se
   para solo**. El comentario sigue abierto en la spec por si prefieres lo otro.
5. **Cada persona ve solo sus tareas.** Las de todo el equipo, con totales, son el panel del
   dueño (fase 4).
6. **Reinicia la API** para que cargue las rutas nuevas, y recarga el front.

## Cambios

### infra
- `docker-compose.yml`: el puerto de Postgres solo escucha en `127.0.0.1`.
- `DATABASE_URL` con `127.0.0.1` (ver punto 2).

### backend: modelo y migración
- `app/models/time_entry.py`: `TimeEntry` (`workspace_id`, `user_id`, `project_id`,
  `category_id`, `subcategory_id` opcional, `title`, `start_at`, `end_at`, `source`
  manual/timer, `created_at`, `updated_at`). `end_at` null = cronómetro en marcha; la duración no
  se guarda.
- Reglas **en la propia BD**, para que no se las salte nadie:
  - `CHECK` fin > inicio y duración ≤ 24 h.
  - Índice único parcial `user_id WHERE end_at IS NULL`: un cronómetro en marcha por persona.
  - **Restricción de exclusión** (`btree_gist`): dos registros de la misma persona no pueden
    compartir ni un instante, **aunque sean de espacios distintos** (nadie está en dos sitios a
    la vez). El cronómetro en marcha cuenta como "hasta el infinito".
  - Índices `(workspace_id, start_at)` para el panel y `(user_id, start_at)` para la hoja.
- Dependencia `tzdata`: la base de zonas horarias que necesita `zoneinfo` en Windows y en las
  imágenes Docker ligeras.

### backend: rutas
- `GET /workspaces/{wid}/entries?from=&to=&project_id=`: mis registros. `from`/`to` son días en
  hora de España, ambos incluidos, y **un registro cuenta en el día en que empieza** (la misma
  regla que las quincenas).
- `POST /workspaces/{wid}/entries` (manual), `PATCH /entries/{id}` y `DELETE /entries/{id}`.
- `POST /workspaces/{wid}/timer/start`, `POST /timer/stop` y `GET /timer/current`.
- Lógica compartida en `app/services/entries.py`. `specs/api/openapi.yaml` regenerado.

**Decisiones que conviene entender:**
- **Validar dos veces a propósito**: la API comprueba fin > inicio y ≤ 24 h para dar un mensaje
  claro; la BD lo vuelve a comprobar por si acaso. Los **solapes** solo los decide la BD (con dos
  peticiones a la vez, un `SELECT` previo dejaría pasar las dos), y la API traduce su error a
  "Se solapa con otro registro tuyo".
- **Cronómetro olvidado**: si alguien lo deja encendido más de 24 h, al pararlo se corta en 24 h
  (un registro no puede durar más) y la persona lo corrige a mano.
- **"No archivado" solo para lo que se elige ahora**: si la label de una tarea antigua se archivó
  después, puedes corregir sus horas sin tener que cambiarle la label.
- **Cambiar la label quita la sublabel**, salvo que mandes una nueva: la anterior era de otra label.
- **Al cronómetro en marcha no se le pone fin editando**: se para con "Parar". Así no hay dos
  formas de hacer lo mismo.
- **Borrar sí borra**: un registro es un dato tuyo, nada depende de él. "Nada se borra, se
  archiva" sigue valiendo para proyectos y labels, de los que dependen los registros.
- **Registros ajenos → 404**, también para el dueño del espacio: nadie edita las horas de otro.
  Si te expulsan de un espacio, dejas de poder tocar tus registros de ahí, pero siguen contando.
- **Fechas siempre con zona horaria** (`AwareDatetime`): una hora "a secas" sería ambigua.

### backend: tests
- `tests/test_entries.py` (33 tests): manual, sublabel opcional, fechas sin zona, fin antes del
  inicio, más de 24 h, solapes (también entre espacios y contra el cronómetro), registros
  seguidos que no chocan, catálogo archivado o ajeno, días de España en el filtro, solo lo mío,
  editar, cambiar label, borrar, permisos, expulsados, espacio archivado, y el cronómetro
  (arrancar, parar, arrancar otro, olvidado más de 24 h, borrar el que está en marcha).
- `tests/conftest.py` activa `btree_gist` en la BD de pruebas.

### frontend
- `lib/time.ts`: todo en hora de España **aunque el navegador esté en otra zona**: días
  `AAAA-MM-DD`, semanas de lunes a domingo, quincenas A/B, y conversión de "día + hora" a UTC
  teniendo en cuenta el cambio de hora. Lo he probado con el reloj del sistema en Nueva York y
  Tokio.
- `components/entries/`:
  - `TimerBar`: el cronómetro de la cabecera. El servidor manda: el front solo pinta
    `ahora - inicio` cada segundo, así que sobrevive a recargas y a cambiar de equipo.
  - `TaskForm`: nueva tarea, con cronómetro o a mano. Si el fin es anterior al inicio
    (22:00 → 01:00), el fin cuenta como del día siguiente.
  - `EntryRow`: la fila de cada tarea, con edición en línea que **solo manda lo que cambias**
    (si no, los segundos se perderían al mostrar HH:MM).
  - `LabelPicker`: desplegables de label y sublabel, con solo las sublabels de la label elegida.
  - `ProjectLinks` y `TimesheetCard`.
- `pages/ProjectSheetPage.tsx`: la hoja del proyecto, con los últimos 30 días y "Ver 30 días más".
- Pestañas del espacio como rutas: `/w/:wid` (Proyectos), `/hoja`, `/catalogo` y `/equipo`.

### docs
- `backend/README.md` y `frontend/README.md`: rutas, estructura y decisiones.
- Spec: parámetro `project_id` del listado y regla del cronómetro de más de 24 h.

## Commits propuestos

> Desactualizado: la fase 3 no se llegó a commitear antes de las fases 4 a 6, que tocan algunos
> de los mismos ficheros. La propuesta vigente está en
> [CHANGELOG-fase-6.md](CHANGELOG-fase-6.md#commits-propuestos-fases-3-a-6).

1. `infra: Postgres solo en 127.0.0.1 y DATABASE_URL sin localhost`
   `docker-compose.yml`, `backend/.env.example`, `backend/app/core/config.py`
2. `backend: registros de tiempo y cronómetro con su migración y tests`
   `backend/app/`, `backend/alembic/versions/e442082a8fa8_*.py`, `backend/tests/`,
   `backend/pyproject.toml`, `backend/uv.lock`, `specs/api/openapi.yaml`
3. `frontend: hoja de cada proyecto, cronómetro en cabecera y mi hoja quincenal`
   `frontend/src/`
4. `docs: fase 3 en changelog y READMEs`
   `docs/`, `backend/README.md`, `frontend/README.md`

## Pendiente para cerrar la fase 3

- [ ] Probar a mano: arrancar y parar el cronómetro, añadir una tarea a mano, editar y borrar,
      y ver "Mi hoja" en semana y quincena.
- [ ] Decidir si al arrancar un cronómetro con otro en marcha se para el anterior (lo actual) o
      se bloquea.
