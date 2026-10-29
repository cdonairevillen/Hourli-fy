# Flujo: invitar a alguien a un espacio o a un proyecto

```mermaid
sequenceDiagram
    actor D as Dueño
    actor I as Invitado
    participant F as Front
    participant A as API
    D->>F: Espacio > Equipo > Invitaciones > alcance + "Crear link"
    F->>A: POST /workspaces/{wid}/invitations {project_id?}
    A-->>F: token (solo esta vez; en BD queda su hash)
    D-->>I: manda /invite/{token} por cualquier canal
    I->>F: abre /invite/{token}
    F->>A: GET /invitations/{token}
    A-->>F: espacio, proyecto (si lo hay), dueño y estado
    alt sin sesión
        I->>F: entrar o crear cuenta (email + contraseña, o Google)
        F->>A: POST /auth/login | /auth/register | /auth/google
        A-->>F: cookie de sesión
    end
    I->>F: "Unirme"
    F->>A: POST /invitations/{token}/accept
    A-->>F: espacio (uses + 1, salvo que el link no le dé nada nuevo)
    F->>I: link a un proyecto → /w/{wid}/p/{pid} · link al espacio → /w/{wid}
```

Alcance:

| Link | Si no eras miembro | Si ya eras miembro limitado | Si ya lo veías todo |
| --- | --- | --- | --- |
| Al espacio (`project_id` vacío) | Ves todos los proyectos, también los futuros | Pasas a verlos todos | Nada (no gasta uso) |
| A un proyecto | Entras viendo solo ese proyecto | Se te suma ese proyecto | Nada (no gasta uso) |

Reglas: el link caduca a los 10 días, el dueño puede revocarlo y fijar un máximo de usos, y
archivar el espacio o el proyecto del link lo invalida. Después, el dueño puede cambiar lo que ve
cada miembro en Equipo > Miembros > "Permisos".
