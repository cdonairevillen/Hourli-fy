import { Link } from 'react-router'

// Política de privacidad (pública: Google la pide para la pantalla de consentimiento).
// BORRADOR: los [CORCHETES] hay que rellenarlos y conviene que lo revise alguien con
// conocimientos legales antes de publicar la app.
export function PrivacyPage() {
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6 text-sm leading-relaxed">
      <Link to="/" className="text-muted-foreground hover:underline">
        ← Hourli-fy
      </Link>
      <h1 className="text-2xl font-semibold">Privacidad</h1>
      <p className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3">
        Borrador pendiente de revisión: los datos entre corchetes están por completar.
      </p>

      <h2 className="text-lg font-semibold">Quién es el responsable</h2>
      <p>
        [NOMBRE O RAZÓN SOCIAL DEL RESPONSABLE], contacto: [EMAIL DE CONTACTO]. Escríbenos para
        cualquier duda o para ejercer tus derechos.
      </p>

      <h2 className="text-lg font-semibold">Qué datos guardamos</h2>
      <ul className="list-disc pl-5">
        <li>De tu cuenta: nombre y email.</li>
        <li>
          Si usas contraseña, la guardamos cifrada con un algoritmo de un solo sentido (argon2):
          nadie, ni nosotros, puede leerla.
        </li>
        <li>
          Si entras con Google: además, tu foto de perfil y un identificador de tu cuenta de
          Google. Nunca recibimos tu contraseña de Google.
        </li>
        <li>
          Lo que registras en la app: los espacios en los que participas y las tareas con su nombre,
          label, proyecto y horas de inicio y fin.
        </li>
        <li>Una cookie de sesión para que no tengas que entrar cada vez. No usamos cookies de publicidad ni de análisis.</li>
      </ul>

      <h2 className="text-lg font-semibold">Para qué</h2>
      <p>
        Solo para que funcione el registro de horas: identificarte, guardar tus tareas y mostrar
        al dueño de cada espacio las horas registradas en él. No vendemos ni cedemos tus datos.
      </p>

      <h2 className="text-lg font-semibold">Quién los ve</h2>
      <p>
        Tus tareas las ves tú y el dueño de cada espacio (en su panel). Los demás miembros ven tu
        nombre y tu email en la lista de miembros del espacio, pero no tus horas.
      </p>
      <p>
        Los administradores del servicio pueden acceder a todos los datos, solo para resolver
        incidencias y dar soporte.
      </p>

      <h2 className="text-lg font-semibold">Dónde se guardan</h2>
      <p>
        En una base de datos de Supabase ([REGIÓN]) y en servidores de Google Cloud ([REGIÓN]).
        Los emails de recuperación de contraseña se envían con Resend. Los tres actúan como
        encargados del tratamiento.
      </p>

      <h2 className="text-lg font-semibold">Cuánto tiempo y cómo borrarlos</h2>
      <p>
        Mientras tengas la cuenta. Puedes eliminarla tú mismo en{' '}
        <Link to="/cuenta" className="underline">
          Mi cuenta
        </Link>
        : se borran tu nombre, email y foto, y tus horas quedan en los informes de cada espacio a
        nombre de «Usuario eliminado», sin forma de relacionarlas contigo.
      </p>

      <h2 className="text-lg font-semibold">Tus derechos</h2>
      <p>
        Puedes pedir acceso, rectificación, supresión, oposición, limitación y portabilidad de tus
        datos escribiendo a [EMAIL DE CONTACTO], y reclamar ante la Agencia Española de Protección
        de Datos (aepd.es).
      </p>
      <p className="text-muted-foreground">Última actualización: [FECHA].</p>
    </main>
  )
}
