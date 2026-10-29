from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def setup_frontend(app: FastAPI, directory: Path) -> None:
    """Sirve la web de React (el `dist` de Vite) desde la propia API.

    En producción la web y la API van en el mismo servicio de Cloud Run: una sola URL, la cookie
    de sesión es del propio dominio y no hace falta proxy ni CORS. Se monta después de /api y
    /admin, que tienen prioridad.
    """
    root = directory.resolve()
    index = root / "index.html"
    app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        # Una ruta de la API que no existe es un 404 de la API, no la web.
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        file = (root / path).resolve()
        # Archivos de public/ (favicon…) tal cual; sin salir de la carpeta (nada de ../).
        if path and file.is_file() and file.is_relative_to(root):
            return FileResponse(file)
        # Cualquier otra ruta (/w/…, /invite/…) es de React Router: siempre index.html.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
