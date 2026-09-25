"""Shared look for the two PDFs (evaluation report, agent note).

Font: Source Sans 3 (OFL), embedded from report/fonts/. If the files are
missing the styles fall back to Helvetica so the builders still run.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

FONTS = Path(__file__).resolve().parent / "fonts"

# ---------------------------------------------------------------- fonts

def _register() -> tuple[str, str, str, str]:
    files = {
        "SourceSans": "SourceSans3-Regular.ttf",
        "SourceSans-It": "SourceSans3-It.ttf",
        "SourceSans-Semi": "SourceSans3-Semibold.ttf",
        "SourceSans-SemiIt": "SourceSans3-SemiboldIt.ttf",
        "SourceSans-Bold": "SourceSans3-Bold.ttf",
    }
    if not all((FONTS / f).exists() for f in files.values()):
        return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"
    for name, f in files.items():
        pdfmetrics.registerFont(TTFont(name, str(FONTS / f)))
    # <b> maps to semibold: bold Source Sans is too heavy at text sizes
    pdfmetrics.registerFontFamily("SourceSans", normal="SourceSans", bold="SourceSans-Semi",
                                  italic="SourceSans-It", boldItalic="SourceSans-SemiIt")
    return "SourceSans", "SourceSans-Semi", "SourceSans-It", "SourceSans-SemiIt"


REGULAR, BOLD, ITALIC, BOLD_ITALIC = _register()

# ---------------------------------------------------------------- palette

INK = colors.HexColor("#17212B")        # headings
TEXT = colors.HexColor("#2B3640")       # body
MUTED = colors.HexColor("#66737F")      # captions, footer
ACCENT = colors.HexColor("#1D5C8B")     # clinical blue
ACCENT_SOFT = colors.HexColor("#E6EEF5")
RULE = colors.HexColor("#D3DCE4")
BAND = colors.HexColor("#F4F7FA")
ZEBRA = colors.HexColor("#FAFBFC")
WHITE = colors.white

# ---------------------------------------------------------------- page

MARGIN = 19 * mm
PAGE_W = A4[0]
CONTENT_W = PAGE_W - 2 * MARGIN
CONTENT_W_MM = CONTENT_W / mm

# ---------------------------------------------------------------- styles

def _ps(name: str, **kw) -> ParagraphStyle:
    base = dict(fontName=REGULAR, fontSize=9.8, leading=13.4, textColor=TEXT, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)


S = {
    "title": _ps("title", fontName=BOLD, fontSize=21, leading=25, textColor=INK, spaceAfter=3),
    "subtitle": _ps("subtitle", fontSize=9.4, leading=12.5, textColor=MUTED, spaceAfter=0),
    "h1": _ps("h1", fontName=BOLD, fontSize=13.6, leading=17, textColor=INK, spaceBefore=13, spaceAfter=2, keepWithNext=1),
    "h2": _ps("h2", fontName=BOLD, fontSize=10.6, leading=13.5, textColor=ACCENT, spaceBefore=9, spaceAfter=3, keepWithNext=1),
    # for a heading before a long table or paragraph that may split across pages
    "h2free": _ps("h2free", fontName=BOLD, fontSize=10.6, leading=13.5, textColor=ACCENT, spaceBefore=9, spaceAfter=3),
    "body": _ps("body", spaceAfter=5),
    "small": _ps("small", fontSize=8.6, leading=11.4, textColor=MUTED, spaceAfter=4),
    "cell": _ps("cell", fontSize=8.9, leading=11.4),
    "cellhead": _ps("cellhead", fontName=BOLD, fontSize=8.2, leading=10.5, textColor=ACCENT),
    "cellgroup": _ps("cellgroup", fontName=BOLD, fontSize=8.9, leading=11.4, textColor=INK),
    "bullet": _ps("bullet", leftIndent=11, bulletIndent=1, spaceAfter=3, bulletColor=ACCENT, bulletFontName=BOLD),
    "numbered": _ps("numbered", leftIndent=13, bulletIndent=0, spaceAfter=3.5, bulletColor=ACCENT, bulletFontName=BOLD),
    "box": _ps("box", fontSize=9.8, leading=13.8),
}


# ---------------------------------------------------------------- flowables

def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def title_block(title: str, subtitle: str) -> list:
    rule = HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceBefore=6, spaceAfter=10)
    return [p(title, "title"), p(subtitle, "subtitle"), rule]


def h1(text: str) -> list:
    """Section heading with a hairline beneath; both stick to what follows."""
    rule = HRFlowable(width="100%", thickness=0.6, color=RULE, spaceBefore=0, spaceAfter=5)
    rule.keepWithNext = 1
    return [p(text, "h1"), rule]


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(item, S["bullet"], bulletText="•") for item in items]


def numbered(items: list[str]) -> list[Paragraph]:
    return [Paragraph(item, S["numbered"], bulletText=f"{n}.") for n, item in enumerate(items, 1)]


def table(header: list[str] | None, rows: list[list[str]], widths: list[float],
          group_rows: list[int] | None = None, total_row: bool = False) -> Table:
    """Rows are strings (inline markup allowed). Widths in mm. `group_rows` are
    row indexes (counting the header) spanning the full width as sub-headings;
    `total_row` gives the last row a top rule and band."""
    body = [[Paragraph(c, S["cellgroup"] if group_rows and i + (1 if header else 0) in group_rows else S["cell"]) for c in row]
            for i, row in enumerate(rows)]
    data = ([[Paragraph(h, S["cellhead"]) for h in header]] if header else []) + body
    scale = CONTENT_W_MM / sum(widths)  # every table spans the text width
    t = Table(data, colWidths=[w * scale * mm for w in widths], repeatRows=1 if header else 0)
    first_body = 1 if header else 0
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LINEBELOW", (0, first_body), (-1, -1), 0.4, RULE),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT_SOFT),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
            ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ]
    for i in group_rows or []:
        style += [("SPAN", (0, i), (-1, i)), ("BACKGROUND", (0, i), (-1, i), BAND),
                  ("TOPPADDING", (0, i), (-1, i), 4.5), ("BOTTOMPADDING", (0, i), (-1, i), 3)]
    if total_row:
        style += [("LINEABOVE", (0, -1), (-1, -1), 0.8, ACCENT), ("BACKGROUND", (0, -1), (-1, -1), BAND)]
    t.setStyle(TableStyle(style))
    return t


def callout(lines: list[str]) -> Table:
    """Summary box: accent bar on the left, soft band behind the text."""
    bar_w = 2.2 * mm
    t = Table([[Paragraph("", S["box"]), Paragraph(l, S["box"])] for l in lines], colWidths=[bar_w, CONTENT_W - bar_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), ACCENT),
        ("BACKGROUND", (1, 0), (1, -1), BAND),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (1, 0), (1, -1), 9), ("RIGHTPADDING", (1, 0), (1, -1), 9),
        ("TOPPADDING", (1, 0), (1, 0), 7), ("BOTTOMPADDING", (1, -1), (1, -1), 7),
        ("TOPPADDING", (1, 1), (1, -1), 2), ("BOTTOMPADDING", (1, 0), (1, -2), 2),
        ("LEFTPADDING", (0, 0), (0, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 0),
    ]))
    return t


# ---------------------------------------------------------------- document

def make_doc(out: Path, title: str, footer_label: str) -> SimpleDocTemplate:
    def footer(canvas, doc) -> None:
        canvas.saveState()
        y = 11 * mm
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, y + 4.5 * mm, PAGE_W - MARGIN, y + 4.5 * mm)
        canvas.setFont(REGULAR, 7.6)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, y, footer_label)
        canvas.drawRightString(PAGE_W - MARGIN, y, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=16 * mm, bottomMargin=20 * mm,
                            title=title, author="Cartesia FDE take-home")
    doc.build_kwargs = dict(onFirstPage=footer, onLaterPages=footer)  # type: ignore[attr-defined]
    return doc


def build_doc(doc: SimpleDocTemplate, story: list) -> None:
    doc.build(story, **doc.build_kwargs)  # type: ignore[attr-defined]


__all__ = [
    "S", "p", "title_block", "h1", "bullets", "numbered", "table", "callout", "make_doc", "build_doc",
    "Spacer", "KeepTogether", "INK", "TEXT", "MUTED", "ACCENT", "ACCENT_SOFT", "RULE", "BAND", "REGULAR", "BOLD",
    "CONTENT_W", "CONTENT_W_MM", "mm",
]
