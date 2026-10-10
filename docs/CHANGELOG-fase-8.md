# Changelog — Fase 8: acceso por proyecto y borrar espacios/proyectos

Fase añadida a petición del autor; como la 7, **va antes del despliegue**. El changelog general
está en [CHANGELOG.md](CHANGELOG.md).

## Resumen rápido

- **Invitar a un solo proyecto.** Al crear un link (Equipo → Invitaciones) eliges el alcance:
  **"Todo el espacio"** o **"Solo el proyecto X"**. Quien entra con un link a Lorca ve el espacio,
  pero solo el proyecto Lorca: ni Cervantes ni los proyectos que se creen después.
- **La invitación al espacio sigue existiendo**, para no tener que invitar proyecto a proyecto.
- **Permisos por miembro** (Equipo → Miembros → "Permisos"): el dueño marca "Todos los proyectos"
  o elige cuáles. Debajo de cada miembro se ve qué tiene.
- **Borrar** un espacio (Equipo → Ajustes, escribiendo su nombre) o un proyecto (Catálogo →
  "Borrar"), **solo si no tienen horas registradas**. Si las tienen, se archivan, como hasta ahora.
- **Archivar un proyecto también desde su hoja** (botón "Archivar proyecto" para el dueño).
- 22 tests nuevos (167 en total), todos en verde.

## Lo que tienes que saber

1. **Los miembros que ya había no cambian**: la migración les deja "todos los proyectos".
2. **Las labels son del espacio** y las ven todos sus miembros, también los limitados a un proyecto.
3. **Un proyecto sin acceso es "invisible"**: no sale en la lista, ni en Mi hoja, ni en los
   desplegables, y la API responde como si no existiera.
4. **Si quitas el acceso a alguien, sus horas siguen contando** en tu panel, pero esa persona ya
   no puede ver ni editar esas tareas.
5. **Varios links se suman**: con un link a Lorca y otro a Cervantes, esa persona ve los dos. Un
   link al espacio le da todo. Si un link no le da nada nuevo, no gasta un uso.
6. **Quien vuelve tras salir o ser expulsado** recupera solo lo que diga el nuevo link, no los
   accesos que tenía antes.
7. **Transferir el espacio** a alguien que solo veía un proyecto le da acceso a todos (el dueño lo
   ve siempre todo).
8. **Migración nueva** (`e000194eb176`): `memberships.all_projects`, tabla `project_members` e
   `invitations.project_id`. Ya está aplicada a tu Postgres local.

## Cambios

### backend
- `models/project_member.py` (nuevo), `memberships.all_projects` e `invitations.project_id`, con
  su migración.
- `services/access.py` (nuevo): la regla de "quién ve qué proyecto" en un solo sitio
  (`accessible_project_ids`, `can_access_project`, `grant_project`, `revoke_projects`).
- `api/catalog.py`: la lista de proyectos se filtra por acceso; `DELETE .../projects/{id}`.
- `api/entries.py` y `services/entries.py`: mis tareas, registrar, editar, borrar y el cronómetro
  respetan el acceso.
- `api/workspaces.py`: miembros con su acceso; `PUT .../members/{uid}/access`; invitaciones con
  `project_id`; `DELETE /workspaces/{wid}`; al expulsar o salir se quitan también sus accesos a
  proyectos; transferir da acceso total.
- `api/invitations.py`: la vista previa dice a qué proyecto invita; aceptar aplica el alcance.
- `services/workspaces.py`: el link a un proyecto archivado pasa a "archivado".
- `services/account.py`: eliminar la cuenta quita también sus accesos a proyectos.
- `admin.py`: vista "Accesos a proyectos" y columna de proyecto en las invitaciones.

**Decisiones que conviene entender:**
- **`all_projects` en la membresía, en vez de apuntar todos los proyectos uno a uno.** Así, quien
  entra al espacio entero recibe solo con eso los proyectos que se creen después, sin tener que
  añadirle filas cada vez.
- **La regla de acceso vive en un solo servicio** (`services/access.py`) y la usan todas las
  rutas. Si cada ruta la escribiera a su manera, bastaría con olvidarla en una para filtrar
  datos de otro proyecto.
- **Sin acceso = "no existe"**: 404 en la URL, y en el cuerpo de una petición el mismo 422 que un
  proyecto inexistente. Así no se revela qué otros proyectos hay.
- **Borrar solo sin horas.** Mantiene la regla de siempre ("nada con horas se borra"): las horas
  son de las personas que las registraron, no del dueño. El borrado va en orden de claves
  foráneas (invitaciones y accesos → labels → proyectos → membresías → espacio).
- **Quitar un acceso no borra la fila** (`removed_at`), igual que con las membresías.

### backend: tests
- `tests/test_project_access.py` (22): solo ve su proyecto; no recibe los nuevos; registra en el
  suyo pero no en otro (manual, cronómetro, listado y mover una tarea); el link al espacio da
  todo; otro link suma; el link al espacio amplía; links que no dan nada no gastan uso; la lista
  de miembros muestra el acceso; cambiar permisos; quitar acceso mantiene las horas en el panel;
  permisos con proyectos ajenos, por un miembro o al dueño; quien vuelve recupera solo lo del
  link; transferir da todo; link a proyecto archivado o de otro espacio; borrar proyecto y
  espacio (vacíos, con horas, por quien no es dueño).
- Lo probé además con el **servidor real** contra la BD de pruebas: invitar a Lorca, aceptar con
  otra cuenta (solo ve Lorca), borrar el proyecto vacío y el espacio.

### frontend
- Equipo → **Invitaciones**: desplegable de alcance y el alcance de cada link en la lista.
- Equipo → **Miembros**: "Todos los proyectos" / "Solo: …" y el editor de "Permisos".
- Equipo → **Ajustes**: zona de peligro "Borrar espacio" (hay que escribir su nombre).
- Catálogo → **Proyectos**: botón "Borrar" (si tiene horas, se muestra el motivo de la API).
- **Hoja del proyecto**: "Archivar proyecto" / "Desarchivar" para el dueño.
- **Invitación**: "Te invitan al proyecto «Lorca»… Verás solo este proyecto", y al aceptar va
  directo a la hoja de ese proyecto.
- **"Salir" lleva al login.** Antes vaciaba la caché, y con eso `useMe` se quedaba mirando
  una consulta ya borrada: la pantalla no cambiaba y te quedabas dentro sin poder hacer nada.
  Ahora `goToLogin()` (`lib/auth.ts`) recarga la app en `/`, que sin sesión muestra el login, y
  la recarga borra toda la caché. "Eliminar cuenta" tenía el mismo fallo y usa la misma función.
- `lib/api.ts`: `apiPut`. `lib/types.ts`: acceso en `Member` y alcance en las invitaciones.

### docs
- `README.md` (cómo se usa, roles, reglas, modelo de datos, módulos y estado), `backend/README.md`,
  `frontend/README.md`, `specs/workflows/invitacion.md` (con la tabla de alcances), `CLAUDE.md`
  (estaba desactualizado: aún decía "no hay contraseñas") y la spec.

## Commits propuestos

Las fases 3 a 8 siguen sin commitear. La propuesta por capas de
[CHANGELOG-fase-7.md](CHANGELOG-fase-7.md#commits-propuestos) sigue valiendo: estos cambios
entran en los mismos cuatro commits (infra, backend, frontend y docs).

## Pendiente

- [ ] Probar a mano con dos cuentas: crear Lorca y Cervantes, invitar a la segunda cuenta solo a
      Lorca, comprobar que no ve Cervantes, darle Cervantes desde "Permisos", y borrar un proyecto
      vacío.
