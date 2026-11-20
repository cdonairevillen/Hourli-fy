"""Lector del PDF "Informe detallado" que exporta Clockify.

Es una función pura: recibe los bytes del PDF y devuelve las entradas, sin tocar la BD.

Cómo es el PDF (una entrada ocupa varias líneas):

    Fecha       Descripción                        Duración             Usuario
    30/12/2024  Añadir mapita de Granada al ...    00:30:00             José Antonio Muñoz
                escenarios                         (negro: descripción partida en dos líneas)
                                                   20:30:00 - 21:00:00  (+1 si acaba otro día)
                Scripts & scores - Guion - Acto 1  (gris: proyecto - tarea)

No se usa el texto "plano" del PDF sino la posición X de cada palabra: así se sabe a qué columna
pertenece aunque una descripción larga se parta en dos líneas. Las columnas se sacan de la
cabecera (Fecha / Descripción / Duración / Usuario). Dentro de la columna de descripción, el
color separa la descripción (negro) del proyecto y la tarea (gris).
"""

import io
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

import pdfplumber

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
CLOCK_RE = re.compile(r"^\d{1,4}:\d{2}:\d{2}$")
NEXT_DAY_RE = re.compile(r"^\+(\d)$")
# Lo que pone Clockify cuando una entrada no tiene descripción.
NO_DESCRIPTION = "(Sin Descripción)"
# Las entradas van en letra de 7 pt (y el "+1" en 6 pt). Título, cabecera y pie son más grandes.
MAX_ENTRY_FONT_SIZE = 7.5
# Dos palabras están en la misma línea si su "top" se diferencia menos que esto (en puntos).
SAME_LINE = 2.0


class ClockifyPdfError(ValueError):
    """El archivo no es un informe detallado de Clockify que sepamos leer."""


@dataclass
class ParsedEntry:
    """Una entrada del informe, tal cual viene (horas locales de España, sin zona)."""

    user_name: str
    description: str
    # Línea gris completa, p. ej. "Scripts & scores - Guion - Acto 1 principal" ("" si no hay).
    project_line: str
    start: datetime
    end: datetime
    # La duración que escribe Clockify (sirve para cuadrar con el total de la cabecera).
    duration_seconds: int


@dataclass
class ParsedReport:
    period: str
    # Total de la cabecera ("Total: 266:58:45") en segundos.
    total_seconds: int
    entries: list[ParsedEntry] = field(default_factory=list)

    @property
    def entries_seconds(self) -> int:
        return sum(entry.duration_seconds for entry in self.entries)


def clock_seconds(text: str) -> int:
    """ "266:58:45" → segundos (las horas pueden pasar de 24 en los totales)."""
    hours, minutes, seconds = (int(part) for part in text.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def parse_clock(text: str) -> time:
    hours, minutes, seconds = (int(part) for part in text.split(":"))
    return time(hours, minutes, seconds)


def is_grey(word: dict) -> bool:
    """Proyecto/tarea y horas van en gris (0.4); la descripción en negro (0)."""
    color = word.get("non_stroking_color") or (0,)
    values = color if isinstance(color, (tuple, list)) else (color,)
    return any(float(value) > 0.2 for value in values)


def group_lines(words: list[dict]) -> list[list[dict]]:
    """Agrupa palabras en líneas (por su "top") y ordena cada línea de izquierda a derecha."""
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["doctop"], w["x0"])):
        if lines and abs(lines[-1][0]["doctop"] - word["doctop"]) < SAME_LINE:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def join_words(words: list[dict]) -> str:
    return " ".join(word["text"] for word in words).strip()


@dataclass
class Columns:
    """Dónde empieza cada columna (x en puntos), leído de la cabecera."""

    description: float
    duration: float
    user: float


def find_header(page) -> tuple[Columns, float]:
    """Columnas y altura de la cabecera "Fecha Descripción Duración Usuario"."""
    words = page.extract_words()
    by_text = {word["text"]: word for word in words}
    needed = ("Fecha", "Descripción", "Duración", "Usuario")
    if not all(name in by_text for name in needed):
        raise ClockifyPdfError("No parece un informe detallado de Clockify (falta la cabecera)")
    columns = Columns(
        description=by_text["Descripción"]["x0"] - 1,
        duration=by_text["Duración"]["x0"] - 1,
        user=by_text["Usuario"]["x0"] - 1,
    )
    return columns, by_text["Fecha"]["bottom"]


def find_total(page) -> tuple[str, int]:
    """Periodo ("01/01/2024 - 31/12/2024") y total ("Total: 266:58:45") de la primera página."""
    words = page.extract_words()
    period = ""
    for line in group_lines(words):
        texts = [word["text"] for word in line]
        if len(texts) == 3 and DATE_RE.match(texts[0]) and DATE_RE.match(texts[2]):
            period = " ".join(texts)
    # Si el número va pegado a "Total:", pdfplumber lo lee como una sola palabra.
    for word in words:
        glued = word["text"].removeprefix("Total:")
        if glued != word["text"] and CLOCK_RE.match(glued):
            return period, clock_seconds(glued)
    # Si no, va en letra más grande que "Total:" y su "top" no coincide del todo: basta con que
    # esté a su derecha y a la misma altura (que se crucen verticalmente).
    label = next((word for word in words if word["text"] == "Total:"), None)
    clocks = [
        word
        for word in words
        if label is not None
        and CLOCK_RE.match(word["text"])
        and word["x0"] > label["x0"]
        and word["top"] < label["bottom"]
        and word["bottom"] > label["top"]
    ]
    if not clocks:
        raise ClockifyPdfError("No se encuentra el total de la cabecera (Total: HH:MM:SS)")
    return period, clock_seconds(min(clocks, key=lambda word: word["x0"])["text"])


def build_entry(words: list[dict], columns: Columns) -> ParsedEntry:
    """Convierte las palabras de una entrada (desde su fecha hasta la siguiente) en un registro."""
    day_word = min(words, key=lambda w: (w["doctop"], w["x0"]))
    day = datetime.strptime(day_word["text"], "%d/%m/%Y").date()

    text_words = [w for w in words if columns.description <= w["x0"] < columns.duration]
    time_words = [w for w in words if columns.duration <= w["x0"] < columns.user]
    user_words = [w for w in words if w["x0"] >= columns.user]

    description_lines, project_lines = [], []
    for line in group_lines(text_words):
        (project_lines if is_grey(line[0]) else description_lines).append(join_words(line))
    description = " ".join(description_lines)
    if description == NO_DESCRIPTION:
        description = ""

    clocks = [w["text"] for w in sorted(time_words, key=lambda w: (w["doctop"], w["x0"]))]
    next_days = [int(NEXT_DAY_RE.match(text)[1]) for text in clocks if NEXT_DAY_RE.match(text)]
    clocks = [text for text in clocks if CLOCK_RE.match(text)]
    if len(clocks) != 3:
        raise ClockifyPdfError(f"Entrada del {day_word['text']} sin duración o sin horas")
    duration, start_text, end_text = clocks
    start = datetime.combine(day, parse_clock(start_text))
    end = datetime.combine(day + timedelta(days=sum(next_days)), parse_clock(end_text))

    user_name = " ".join(join_words(line) for line in group_lines(user_words))
    if not user_name:
        raise ClockifyPdfError(f"Entrada del {day_word['text']} sin usuario")
    return ParsedEntry(
        user_name=user_name,
        description=description,
        project_line=" ".join(project_lines),
        start=start,
        end=end,
        duration_seconds=clock_seconds(duration),
    )


def parse_clockify_pdf(data: bytes) -> ParsedReport:
    """Lee el PDF entero. Las entradas pueden cruzar de página: se tratan como un solo flujo."""
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as error:  # pdfplumber lanza varios tipos según cómo esté roto el archivo
        raise ClockifyPdfError("El archivo no es un PDF válido") from error
    with pdf:
        if not pdf.pages:
            raise ClockifyPdfError("El PDF está vacío")
        columns, header_bottom = find_header(pdf.pages[0])
        period, total = find_total(pdf.pages[0])

        words: list[dict] = []
        for page in pdf.pages:
            for word in page.extract_words(extra_attrs=["size", "non_stroking_color"]):
                is_entry_text = word["size"] < MAX_ENTRY_FONT_SIZE
                below_header = page.page_number > 1 or word["top"] > header_bottom
                if is_entry_text and below_header:
                    words.append(word)

    # Cada fecha en la columna "Fecha" abre una entrada nueva.
    entries_words: list[list[dict]] = []
    for line in group_lines(words):
        first = line[0]
        if first["x0"] < columns.description and DATE_RE.match(first["text"]):
            entries_words.append([])
        if not entries_words:
            raise ClockifyPdfError("Hay texto antes de la primera entrada")
        entries_words[-1].extend(line)

    report = ParsedReport(period=period, total_seconds=total)
    report.entries = [build_entry(entry_words, columns) for entry_words in entries_words]
    return report


def split_project_line(line: str) -> list[str]:
    """ "Scripts & scores - Guion - Acto 1" → ["Scripts & scores", "Guion", "Acto 1"]."""
    return [part.strip() for part in line.split(" - ") if part.strip()] if line else []
