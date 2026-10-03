# Flujo: invitar a alguien a un espacio

```mermaid
sequenceDiagram
    actor D as Dueño
    actor I as Invitado
    participant F as Front
    participant A as API
    D->>F: Espacio > Invitaciones > "Crear link"
    F->>A: POST /workspaces/{wid}/invitations
    A-->>F: token (solo esta vez; en BD queda su hash)
    D-->>I: manda /invite/{token} por cualquier canal
    I->>F: abre /invite/{token}
    F->>A: GET /invitations/{token}
    A-->>F: espacio, dueño y estado (active / expired / revoked / exhausted / archived)
    alt sin sesión
        I->>F: "Iniciar sesión con Google"
        F->>A: POST /auth/google (ID token)
        A-->>F: cookie de sesión
    end
    I->>F: "Unirme"
    F->>A: POST /invitations/{token}/accept
    A-->>F: espacio (uses + 1, salvo que ya fuera miembro)
    F->>I: redirige a /w/{wid}
```

Reglas: el link caduca a los 10 días, el dueño puede revocarlo y fijar un máximo de usos, y
archivar el espacio invalida todos sus links. Si ya eres miembro, aceptar no gasta un uso.
