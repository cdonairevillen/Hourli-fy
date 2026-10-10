# Changelog — Fase 4: panel del dueño

Fase 4 del plan ("Panel"). El changelog general está en [CHANGELOG.md](CHANGELOG.md).

> Hecha mientras estabas en el trabajo, sin esperar a aprobar el plan (lo pediste así). Las
> decisiones están explicadas abajo; si alguna no encaja, se cambia.

## Resumen rápido

- Nueva pestaña **Panel** en cada espacio (`/w/:wid/panel`), **solo para el dueño**.
- **Filtros** (una sola fila arriba, afectan a todo lo de debajo):
  - **Quincena** (A = 1–15, B = 16–fin de mes, con ‹ › y "Hoy") o **rango de fechas**.
  - **Persona**, **proyecto**, **label** y **sublabel** (solo las de la label elegida).
  - **Búsqueda** en el nombre de la tarea (sin distinguir mayúsculas).
- Muestra el **total de horas** del grupo filtrado, el **reparto por persona, por proyecto y por
  label** (horas y %), y la **lista de tareas** (día, persona, tarea, proyecto · label, horas)
  paginada de 50 en 50.
- 17 tests nuevos (`tests/test_reports.py`).

## Lo que tienes que saber

1. **Solo cuentan tareas terminadas.** El cronómetro en marcha aún no tiene duración; suma
   cuando se para.
2. **Una tarea cuenta en el día de España en que empieza.** Una que empieza el 15 a las 23:30 es
   de la quincena A aunque termine el 16.
3. **Las horas de quien ya no es miembro siguen contando**, y la persona sigue apareciendo en el
   filtro de personas si tiene horas en el periodo.
4. **Sin periodo, la API usa la quincena actual.** `period` y `from`/`to` no se pueden mezclar
   (422).
5. **Windows bloquea ahora también `pytest.exe`.** Los tests se lanzan con
   `uv run python -m pytest`. Lo he cambiado en `CLAUDE.md` y en los README.

## Cambios

### backend
- `app/api/reports.py`:
  - `GET /workspaces/{wid}/reports/summary`: total, número de tareas y desglose `by_user`,
    `by_project`, `by_category` y `by_day`.
  - `GET /workspaces/{wid}/reports/entries`: tareas filtradas con el nombre de quien las hizo,
    paginadas (`limit` ≤ 200, `offset`).
- `app/services/reports.py`: resuelve `period=AAAA-MM-A|B` o `from`/`to` y construye el `WHERE`
  dinámico.
- `app/schemas.py`: `ReportSummary`, `UserTotal`, `ProjectTotal`, `CategoryTotal`, `DayTotal`,
  `ReportEntry`, `ReportEntriesPage`.
- `specs/api/openapi.yaml` regenerado.

**Decisiones que conviene entender:**
- **Postgres suma, Python solo da forma.** Cada desglose es una consulta con `GROUP BY` sobre el
  mismo `WHERE`, así que los números siempre cuadran entre sí. Traer todas las tareas a Python
  para sumarlas sería lento con meses de datos.
- **WHERE dinámico**: solo se añaden las condiciones de los filtros que llegan, y todas van con AND.
- **Búsqueda con `autoescape`**: si alguien busca "100%", el `%` se busca literalmente y no actúa
  como comodín de SQL que lo encontraría todo.
- **Los días por zona horaria se calculan en SQL** (`timezone('Europe/Madrid', start_at)`), igual
  que los filtros, para que "horas por día" y "quincena" usen la misma regla.
- **Orden estable**: con empates (dos personas con las mismas horas, dos tareas a la misma hora)
  desempata el nombre. Así la paginación nunca repite ni se salta filas.
- **Miembros 403 y ajenos 404**, igual que en el resto de rutas del dueño.

### backend: tests
- `tests/test_reports.py` (17): resumen de una quincena, quincena B de febrero, quincena actual por
  defecto, rango, parámetros incorrectos (422), filtros por persona, proyecto, label, sublabel y
  texto (incluido el `%` literal), cronómetro en marcha que no cuenta, día de España, horas de un
  expulsado, paginación con orden estable, permisos (dueño, miembro, ajeno) y que no se mezclan
  espacios.

### frontend
- `components/reports/ReportPanel.tsx`: filtros, total, tarjetas de reparto y lista con
  "Cargar más" (`useInfiniteQuery`). La búsqueda espera 400 ms sin teclear antes de pedir datos
  (*debounce*).
- `lib/reports.ts`: tipos del panel.
- `WorkspacePage` y `App.tsx`: pestaña y ruta `/w/:wid/panel` (la pestaña solo la ve el dueño).

## Commits propuestos

Ver la nota común en [CHANGELOG-fase-6.md](CHANGELOG-fase-6.md#commits-propuestos-fases-3-a-6).

## Pendiente para cerrar la fase 4

- [ ] Probar a mano el panel con dos cuentas que tengan horas: cambiar de quincena, filtrar por
      persona, por label y buscar texto.
