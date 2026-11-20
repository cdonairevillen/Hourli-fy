"""Importar horas de un PDF de Clockify (solo el dueño). Ver services/clockify_import.py.

El PDF viaja como archivo (multipart) en los dos pasos: vista previa y confirmar. Las opciones de
la importación van en el campo `options` como JSON.

Las rutas son `def` normales (no `async`): leer el PDF y escribir en la BD bloquea, y FastAPI
ejecuta las `def` en otro hilo para no parar al resto de peticiones mientras tanto.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.api.deps import OwnerAccess, SessionDep
from app.schemas import ImportOptions, ImportPreview, ImportResult
from app.services.clockify_import import MAX_PDF_BYTES, build_preview, read_report, run_import

router = APIRouter(prefix="/workspaces/{wid}/imports", tags=["imports"])

PdfFile = Annotated[UploadFile, File(description="PDF «Informe detallado» de Clockify")]


def read_upload(file: UploadFile) -> bytes:
    # Se lee como mucho un byte más que el límite: basta para saber si se pasa.
    return file.file.read(MAX_PDF_BYTES + 1)


@router.post("/preview")
def preview_import(file: PdfFile, session: SessionDep, access: OwnerAccess) -> ImportPreview:
    """Lee el PDF y enseña qué se importaría (personas, labels, duplicados). No guarda nada."""
    report = read_report(read_upload(file))
    return build_preview(session, access.workspace, report)


@router.post("", status_code=status.HTTP_201_CREATED)
def import_pdf(
    file: PdfFile,
    session: SessionDep,
    access: OwnerAccess,
    options: Annotated[str, Form()] = "{}",
) -> ImportResult:
    """Importa el PDF con las opciones elegidas (lo que no venga, como en la vista previa)."""
    try:
        parsed = ImportOptions.model_validate_json(options)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Opciones de importación no válidas"
        ) from error
    report = read_report(read_upload(file))
    return run_import(session, access.workspace, report, parsed)
