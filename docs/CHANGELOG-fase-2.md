# Changelog — Fase 2: catálogo (proyectos, labels y sublabels)

Fase 2 del plan ("Catálogos"). El changelog general está en [CHANGELOG.md](CHANGELOG.md).

## Resumen rápido

- Cada espacio tiene ahora una pestaña **Catálogo** (`/w/:wid/catalogo`) junto a **Equipo**.
- **Proyectos**: nombre y color. Cada uno será la puerta a su hoja de tareas en la fase 3. Al
  entrar en un proyecto, lo que se registre queda ligado a él sin elegirlo.
- **Labels** con **sublabels** (p. ej. "Acto 1" › "Entornos 3D", "Personajes", "Arte 2D"; o
  "Gestión" sin sublabels). Son del espacio y se usan en todos sus proyectos.
- Solo el **dueño** crea, renombra y archiva. Los **miembros** lo ven en solo lectura.
- Nada se borra: se archiva y se puede desarchivar ("Ver archivados").
- 19 tests nuevos (59 en total), todos en verde.

## Lo que tienes que saber

1. **Migración nueva** (`2c80dffbd7ee`, 3 tablas). Ya está aplicada a tu Postgres local. En otro
   equipo: `uv run python -m alembic upgrade head`.
2. **Vocabulario**: en pantalla se llaman "labels" y "sublabels"; en el código, la BD y la API,
   `categories` y `subcategories` (tipologías y subtipologías en la spec). Es lo mismo.
3. **Una tarea (fase 3)** = nombre libre ("Animaciones de personajes Pepe y Juan") + label de un
   desplegable + sublabel opcional (solo las de esa label). Anotado en la spec.
4. **Nombres únicos**: no puede haber dos proyectos ni dos labels con el mismo nombre en un
   espacio, ni dos sublabels iguales dentro de una label, **contando los archivados**. Si
   intentas crear uno que ya existe archivado, la app te pide que lo desarchives. Es intencionado:
   así no hay dos "Acto 1" que en los informes parecerían el mismo.
5. **Smart App Control a veces bloquea la DLL de psycopg** (el driver de Postgres):
   `ImportError: no pq wrapper available ... Una directiva de Control de aplicaciones bloqueó este
   archivo`. Me pasó una vez y al reintentar funcionó (Windows consulta la reputación del fichero
   en la nube y a veces falla). Si se repite a menudo, lo resolvemos para siempre ejecutando el
   backend dentro de Docker, que necesitaremos igualmente para Cloud Run.
6. **Tu `SECRET_KEY` sigue siendo el de ejemplo** y PyJWT avisa de que es corto (25 bytes, mínimo
   recomendado 32). En local da igual; genera uno con
   `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"` cuando quieras.
   Los tests ya usan una clave propia y no dependen de tu `.env`.

## Cambios

### backend: modelos y migración del catálogo
- `app/models/catalog.py`: `Project` (`name`, `color`, `archived`), `Category` y `Subcategory`
  (`name`, `archived`). Todas con `created_at` para ordenar de forma estable (la spec no lo
  ponía en las dos últimas; actualizada).
- Restricciones únicas `(workspace_id, name)` y `(category_id, name)`.
- Migración `2c80dffbd7ee`; `alembic check` confirma que coincide con los modelos.

**Decisión**: sin índice aparte en `workspace_id` / `category_id`. El índice que crea la
restricción única `(workspace_id, name)` empieza por `workspace_id`, y Postgres lo usa también
para "todos los proyectos de este espacio". Un segundo índice solo gastaría espacio y haría más
lentas las escrituras.

### backend: rutas del catálogo
- `app/api/catalog.py`, con las rutas bajo `/workspaces/{wid}`:
  `GET/POST /projects`, `PATCH /projects/{id}`, `GET/POST /categories`,
  `PATCH /categories/{id}`, `POST /categories/{cid}/subcategories` y
  `PATCH /categories/{cid}/subcategories/{sid}`.
- Los `GET` devuelven solo lo activo; `?include_archived=true` lo incluye todo (pantalla del dueño).
- `GET /categories` devuelve cada label con sus sublabels anidadas. Son dos consultas que se
  agrupan en Python, en vez de una consulta por label (el clásico problema "N+1").
- Schemas en `app/schemas.py`: el nombre se recorta y debe tener entre 1 y 80 caracteres; el
  color tiene que ser `#RRGGBB`.
- `specs/api/openapi.yaml` regenerado.

**Decisiones que conviene entender:**
- **Reutiliza `MemberAccess` / `OwnerAccess`** de la fase 1: si no eres miembro, 404; si eres
  miembro pero no dueño, 403 al escribir.
- **Un id de otro espacio da 404** aunque seas dueño de los dos espacios. Cada ruta comprueba
  que el proyecto o la label pertenecen al `{wid}` de la URL, y que la sublabel pertenece a su label.
- **Duplicados → 409 a partir del error de la BD**: no se hace un `SELECT` previo. Dos peticiones
  simultáneas pasarían las dos esa comprobación; la restricción única de la BD no se la salta nadie.
- **Archivar una label no toca sus sublabels**: al no salir la label en los desplegables, sus
  sublabels tampoco. Si la desarchivas, vuelven tal como estaban.
- **Espacio archivado**: el catálogo se puede consultar, pero no modificar (409).

### backend: tests
- `tests/test_catalog.py` (19 tests): crear, listar, editar y archivar los tres; color y nombre
  inválidos (422); duplicados (409), incluso contra uno archivado; mismo nombre permitido en otro
  espacio u otra label; miembro lee pero no escribe (403); ajeno 404 en todo; ids de otro
  espacio 404; espacio archivado 409.
- `tests/conftest.py`: los tests usan un `SECRET_KEY` propio de 32+ bytes.

### frontend: pestaña Catálogo
- `WorkspacePage` con dos pestañas, que son rutas: **Equipo** (`/w/:wid`) y **Catálogo**
  (`/w/:wid/catalogo`). Al ser rutas, cada pestaña tiene su propio link y funciona con atrás/adelante.
- `components/catalog/ProjectsCard.tsx`: lista con punto de color, crear con paleta de 8 colores,
  renombrar, cambiar color, archivar/desarchivar y "Ver archivados".
- `components/catalog/CategoriesCard.tsx`: cada label con sus sublabels debajo; crear, renombrar
  y archivar ambas.
- `components/catalog/ItemActions.tsx`: piezas comunes (renombrar en línea, archivar, crear por
  nombre, "Ver archivados"). Si crear falla (p. ej. nombre repetido), no se borra lo escrito.
- `lib/types.ts`: `Project`, `Category`, `Subcategory`.

### docs
- `backend/README.md`: endpoints del catálogo y decisión de los nombres únicos.
- `frontend/README.md`: nueva estructura.
- Spec: rutas de sublabels, `created_at`, vocabulario label/sublabel y cómo será la hoja del proyecto.

## Commits propuestos

Todo está en el árbol de trabajo, sin commitear. Propuesta, en este orden:

1. `backend: catálogo de proyectos, labels y sublabels con su migración y tests`
   `backend/app/models/`, `backend/alembic/versions/2c80dffbd7ee_*.py`, `backend/app/api/catalog.py`,
   `backend/app/schemas.py`, `backend/app/main.py`, `backend/tests/`, `specs/api/openapi.yaml`
2. `frontend: pestaña Catálogo con proyectos, labels y sublabels`
   `frontend/src/`
3. `docs: fase 2 en changelog y READMEs`
   `docs/`, `backend/README.md`, `frontend/README.md`

## Pendiente para cerrar la fase 2

- [ ] Probar a mano: como dueño, crear 2 proyectos y "Acto 1" con 2 sublabels, archivar y
      desarchivar uno; como miembro (incógnito), ver el catálogo en solo lectura.
- [ ] De paso, la invitación con dos cuentas que quedó pendiente en la fase 1.
