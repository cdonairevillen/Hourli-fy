"""Lector del PDF de Clockify (services/clockify_pdf.py).

Los PDFs reales tienen nombres y horas de personas, así que no se guardan en el repo: los tests
fabrican uno con la misma maqueta (mismas columnas, tamaños de letra y colores) con
`build_clockify_pdf`.
"""

from dataclasses import dataclass, field
from datetime import datetime

import pytest
from fastapi import HTTPException

from app.services.clockify_import import read_report
from app.services.clockify_pdf import ClockifyPdfError, parse_clockify_pdf

PAGE_HEIGHT = 842
BLACK, GREY = "0 g", "0.4 g"


@dataclass
class FakeEntry:
    """Una entrada del informe tal como la pinta Clockify."""

    day: str
    user: str
    start: str
    end: str
    duration: str
    description: list[str] = field(default_factory=lambda: ["Tarea"])
    project: list[str] = field(default_factory=lambda: ["Reuniones"])
    # Días después del inicio en que acaba (Clockify pinta "+1" junto a la hora de fin).
    plus_days: int = 0
    # Fuerza un salto de página justo después de la primera línea de la entrada.
    break_after_first_line: bool = False


def pdf_text(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"({escaped})"


def build_clockify_pdf(
    entries: list[FakeEntry], total: str, period: str = "01/01/2024 - 31/12/2024"
) -> bytes:
    """PDF mínimo con la maqueta del "Informe detallado" de Clockify (Helvetica, WinAnsi)."""
    pages: list[list[str]] = [[]]

    def put(top: float, x: float, text: str, size: float = 7, color: str = BLACK) -> None:
        y = PAGE_HEIGHT - top - size
        pages[-1].append(f"BT /F1 {size} Tf {color} {x} {y} Td {pdf_text(text)} Tj ET")

    put(49, 36, "Informe detallado", 18)
    put(76, 36, period, 10)
    put(100, 36, "Total:", 10)
    put(99, 64, total, 12)
    for x, title in ((38, "Fecha"), (103, "Descripción"), (300, "Duración"), (430, "Usuario")):
        put(156, x, title, 8)

    top = 183
    for entry in entries:
        if top > 760:
            pages.append([])
            top = 47
        put(top, 38, entry.day)
        put(top, 103, entry.description[0])
        put(top, 300, entry.duration)
        put(top, 430, entry.user)
        if entry.break_after_first_line:
            pages.append([])
            top = 33
        for line in entry.description[1:]:
            top += 7
            put(top, 103, line)
        top += 14 if len(entry.description) == 1 else 7
        if entry.plus_days:
            put(top - 5, 360, f"+{entry.plus_days}", 6, GREY)
        put(top, 300, f"{entry.start} - {entry.end}", color=GREY)
        if len(entry.description) > 1:
            top += 7
        for index, line in enumerate(entry.project):
            put(top + 7 * index, 103, line, color=GREY)
        top += 7 * (len(entry.project) - 1) + 27

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "",  # /Pages: se rellena al final, cuando se conocen las páginas
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    page_ids = []
    for number, commands in enumerate(pages, start=1):
        footer_text = pdf_text(f"Estudio - Creado con Clockify {number}")
        footer = f"BT /F1 8 Tf {BLACK} 308 34 Td {footer_text} Tj ET"
        stream = "\n".join([*commands, footer]).encode("cp1252")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode('cp1252')}\nendstream")
        content_id = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(len(objects))
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("cp1252")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    trailer = f"<< /Size {len(objects) + 1} /Root 1 0 R >>"
    out += f"trailer\n{trailer}\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def simple_entry(**changes) -> FakeEntry:
    values = dict(
        day="30/12/2024",
        user="José Antonio Muñoz García",
        start="20:30:00",
        end="21:00:00",
        duration="00:30:00",
        description=["Añadir mapita de Granada"],
        project=["Scripts & scores - Guion - Acto 1 principal"],
    )
    return FakeEntry(**(values | changes))


def test_lee_una_entrada_con_sus_columnas():
    pdf = build_clockify_pdf([simple_entry()], total="0:30:00")

    report = parse_clockify_pdf(pdf)

    assert report.period == "01/01/2024 - 31/12/2024"
    assert report.total_seconds == 1800
    [entry] = report.entries
    assert entry.user_name == "José Antonio Muñoz García"
    assert entry.description == "Añadir mapita de Granada"
    assert entry.project_line == "Scripts & scores - Guion - Acto 1 principal"
    assert entry.start == datetime(2024, 12, 30, 20, 30)
    assert entry.end == datetime(2024, 12, 30, 21, 0)
    assert entry.duration_seconds == 1800


def test_descripcion_y_proyecto_partidos_en_varias_lineas():
    entry = simple_entry(
        description=["Añadir mapita de Granada al documento espacios y", "escenarios"],
        project=[
            "Scripts & scores - Banda sonora - 5. Réquiem por un",
            "maestro (Acto 1 escena 3)",
        ],
    )

    [parsed] = parse_clockify_pdf(build_clockify_pdf([entry], total="0:30:00")).entries

    assert parsed.description == "Añadir mapita de Granada al documento espacios y escenarios"
    assert parsed.project_line == (
        "Scripts & scores - Banda sonora - 5. Réquiem por un maestro (Acto 1 escena 3)"
    )


def test_mas_uno_acaba_al_dia_siguiente_y_sin_descripcion_queda_vacia():
    entry = simple_entry(
        start="23:00:00",
        end="02:00:00",
        duration="03:00:00",
        plus_days=1,
        description=["(Sin Descripción)"],
        project=["Reuniones"],
    )

    [parsed] = parse_clockify_pdf(build_clockify_pdf([entry], total="3:00:00")).entries

    assert parsed.end == datetime(2024, 12, 31, 2, 0)
    assert parsed.description == ""
    assert parsed.project_line == "Reuniones"


def test_entradas_que_cruzan_de_pagina_y_muchas_paginas():
    entries = [simple_entry(day=f"{day:02d}/12/2024") for day in range(1, 29)]
    entries[3].break_after_first_line = True
    pdf = build_clockify_pdf(entries, total="14:00:00")

    report = parse_clockify_pdf(pdf)

    assert len(report.entries) == 28
    assert report.entries_seconds == report.total_seconds
    assert report.entries[3].project_line == "Scripts & scores - Guion - Acto 1 principal"
    assert report.entries[3].start == datetime(2024, 12, 4, 20, 30)


def test_no_es_un_pdf():
    with pytest.raises(ClockifyPdfError):
        parse_clockify_pdf(b"hola, no soy un PDF")


def test_pdf_sin_la_cabecera_de_clockify():
    pdf = build_clockify_pdf([], total="0:00:00").replace(b"(Usuario)", b"(Persona)")

    with pytest.raises(ClockifyPdfError, match="cabecera"):
        parse_clockify_pdf(pdf)


def test_si_no_cuadra_con_el_total_no_se_importa():
    pdf = build_clockify_pdf([simple_entry()], total="1:00:00")

    with pytest.raises(HTTPException) as error:
        read_report(pdf)

    assert error.value.status_code == 422
    assert "no se importa nada" in error.value.detail
