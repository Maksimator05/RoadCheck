import logging
import tempfile
from pathlib import Path

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.lib.units import cm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore[import-untyped]

from app.db.models import Analysis

logger = logging.getLogger(__name__)

_TYPE_LABELS = {
    "pothole": "Pothole",
    "crack": "Crack",
    "patch": "Patch",
}

_SEVERITY_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}

_FONT_REGULAR_CANDIDATES = [
    "C:/Windows/Fonts/verdana.ttf",
    "/System/Library/Fonts/Supplemental/Verdana.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Verdana.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_FONT_BOLD_CANDIDATES = [
    "C:/Windows/Fonts/verdanab.ttf",
    "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Verdana_Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _find_font(candidates: list[str]) -> str | None:
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def _resolve_font_names() -> tuple[str, str]:
    regular_path = _find_font(_FONT_REGULAR_CANDIDATES)
    bold_path = _find_font(_FONT_BOLD_CANDIDATES)

    if regular_path and bold_path:
        pdfmetrics.registerFont(TTFont("AppFont", regular_path))
        pdfmetrics.registerFont(TTFont("AppFont-Bold", bold_path))
        return "AppFont", "AppFont-Bold"

    logger.warning(
        "Custom PDF fonts were not found. Falling back to built-in Helvetica fonts."
    )
    return "Helvetica", "Helvetica-Bold"


_FONT_REGULAR_NAME, _FONT_BOLD_NAME = _resolve_font_names()

_TITLE_STYLE = ParagraphStyle(
    "title", fontName=_FONT_BOLD_NAME, fontSize=16, spaceAfter=16, leading=20
)
_NORMAL_STYLE = ParagraphStyle(
    "normal", fontName=_FONT_REGULAR_NAME, fontSize=11, spaceAfter=6, leading=15
)
_TOTAL_STYLE = ParagraphStyle(
    "total", fontName=_FONT_BOLD_NAME, fontSize=11, spaceBefore=6
)


def generate_analysis_pdf(analysis: Analysis) -> str:
    path = str(Path(tempfile.gettempdir()) / f"{analysis.id}_report.pdf")

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    date_str = analysis.created_at.strftime("%d.%m.%Y %H:%M")
    defects: list[dict] = (analysis.result or {}).get("defects", [])

    table_data = [["#", "Defect type", "Severity", "Model confidence"]]
    for index, defect in enumerate(defects, 1):
        defect_type = _TYPE_LABELS.get(defect.get("type", ""), defect.get("type", "Unknown"))
        severity = _SEVERITY_LABELS.get(defect.get("severity", ""), defect.get("severity", ""))
        confidence = f"{int(defect.get('confidence', 0) * 100)}%"
        table_data.append([str(index), defect_type, severity, confidence])

    table = Table(
        table_data,
        colWidths=[1.5 * cm, 6.5 * cm, 4 * cm, 5 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD_NAME),
                ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F5F5F5")],
                ),
            ]
        )
    )

    story = [
        Paragraph("Road surface analysis report", _TITLE_STYLE),
        Paragraph(f"Date: {date_str}", _NORMAL_STYLE),
        Paragraph(f"File: {analysis.filename}", _NORMAL_STYLE),
        Spacer(1, 0.5 * cm),
        table,
        Spacer(1, 0.5 * cm),
        Paragraph(f"Detected defects: {len(defects)}", _TOTAL_STYLE),
    ]

    doc.build(story)
    return path
