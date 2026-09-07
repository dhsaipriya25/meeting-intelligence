"""
Export service: converts meeting intelligence results into various file formats.
All public functions return bytes ready to be streamed as an HTTP response.
"""

import io
from typing import Any

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fpdf import FPDF
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Strip leading/trailing whitespace."""
    return (text or "").strip()


def _pdf_multiline(pdf: FPDF, text: str, line_height: int = 6) -> None:
    """Write multi-line text respecting newlines."""
    for line in text.split("\n"):
        pdf.multi_cell(0, line_height, line)


def _docx_bytes(doc: Document) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_bytes(pdf: FPDF) -> bytes:
    return pdf.output()


# ---------------------------------------------------------------------------
# Transcript exports
# ---------------------------------------------------------------------------

def transcript_to_txt(transcript: str) -> bytes:
    return _clean(transcript).encode("utf-8")


def transcript_to_docx(transcript: str) -> bytes:
    doc = Document()
    doc.add_heading("Meeting Transcript", level=0)
    doc.add_paragraph(_clean(transcript))
    return _docx_bytes(doc)


def transcript_to_pdf(transcript: str) -> bytes:
    """
    Note: fpdf2 built-in fonts (Helvetica) support Latin characters only.
    Hindi/Telugu characters will appear as replacement characters in the PDF.
    For full Unicode support, supply a Unicode TTF font via FPDF.add_font().
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Meeting Transcript", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)
    # Replace characters outside Latin-1 with '?' to avoid fpdf encoding errors
    safe_text = _clean(transcript).encode("latin-1", errors="replace").decode("latin-1")
    _pdf_multiline(pdf, safe_text)
    return _pdf_bytes(pdf)


# ---------------------------------------------------------------------------
# Summary exports
# ---------------------------------------------------------------------------

def summary_to_txt(summary: str) -> bytes:
    return _clean(summary).encode("utf-8")


def summary_to_pdf(summary: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Meeting Summary", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    safe_text = _clean(summary).encode("latin-1", errors="replace").decode("latin-1")
    _pdf_multiline(pdf, safe_text)
    return _pdf_bytes(pdf)


# ---------------------------------------------------------------------------
# Action items exports
# ---------------------------------------------------------------------------

def actions_to_excel(action_items: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Action Items"

    headers = ["Task", "Assignee", "Due Date", "Priority", "Status", "Context"]
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    priority_colors = {
        "High": "FF0000",
        "Medium": "FFA500",
        "Low": "00AA00",
    }

    for row_idx, item in enumerate(action_items or [], start=2):
        values = [
            item.get("task", ""),
            item.get("assignee", "TBD"),
            item.get("due_date") or "",
            item.get("priority", "Medium"),
            item.get("status", "Open"),
            item.get("context", ""),
        ]
        priority = item.get("priority", "Medium")
        color = priority_colors.get(priority, "000000")

        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border
            if col_idx == 4:  # Priority column
                cell.font = Font(color=color, bold=True)

    # Auto-width columns
    col_widths = [40, 20, 15, 12, 12, 50]
    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def actions_to_pdf(action_items: list) -> bytes:
    pdf = FPDF(orientation="L")  # Landscape for table width
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Action Items", ln=True, align="C")
    pdf.ln(4)

    headers = ["Task", "Assignee", "Due Date", "Priority", "Context"]
    col_widths = [80, 35, 30, 22, 100]

    # Header row
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(31, 78, 121)
    pdf.set_text_color(255, 255, 255)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 8, header, border=1, fill=True, align="C")
    pdf.ln()

    # Data rows
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(0, 0, 0)
    priority_colors = {
        "High": (220, 50, 50),
        "Medium": (200, 100, 0),
        "Low": (0, 150, 0),
    }

    for item in action_items or []:
        row = [
            item.get("task", ""),
            item.get("assignee", "TBD"),
            str(item.get("due_date") or ""),
            item.get("priority", "Medium"),
            item.get("context", ""),
        ]
        priority = item.get("priority", "Medium")
        p_color = priority_colors.get(priority, (0, 0, 0))

        # Calculate row height based on longest cell
        row_height = 6
        for text, width in zip(row, col_widths):
            safe = str(text).encode("latin-1", errors="replace").decode("latin-1")
            num_lines = max(1, len(safe) // max(1, width // 2))
            row_height = max(row_height, num_lines * 5)

        for col_idx, (text, width) in enumerate(zip(row, col_widths)):
            safe = str(text).encode("latin-1", errors="replace").decode("latin-1")
            if col_idx == 3:  # Priority
                r, g, b = p_color
                pdf.set_text_color(r, g, b)
                pdf.cell(width, row_height, safe, border=1, align="C")
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(width, row_height, safe[:60], border=1)
        pdf.ln()

    return _pdf_bytes(pdf)


# ---------------------------------------------------------------------------
# Risks exports
# ---------------------------------------------------------------------------

def risks_to_excel(risks: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Risks & Dependencies"

    headers = ["Description", "Category", "Severity", "Mitigation"]
    header_fill = PatternFill("solid", fgColor="7B2C2C")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    severity_colors = {
        "High": "FF0000",
        "Medium": "FFA500",
        "Low": "00AA00",
    }

    for row_idx, item in enumerate(risks or [], start=2):
        values = [
            item.get("description", ""),
            item.get("category", "risk"),
            item.get("severity", "Medium"),
            item.get("mitigation", ""),
        ]
        severity = item.get("severity", "Medium")
        color = severity_colors.get(severity, "000000")

        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border
            if col_idx == 3:  # Severity column
                cell.font = Font(color=color, bold=True)

    col_widths = [60, 18, 14, 60]
    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def risks_to_pdf(risks: list) -> bytes:
    pdf = FPDF(orientation="L")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Risks & Dependencies", ln=True, align="C")
    pdf.ln(4)

    headers = ["Description", "Category", "Severity", "Mitigation"]
    col_widths = [100, 30, 25, 112]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(123, 44, 44)
    pdf.set_text_color(255, 255, 255)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 8, header, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(0, 0, 0)
    severity_colors = {
        "High": (220, 50, 50),
        "Medium": (200, 100, 0),
        "Low": (0, 150, 0),
    }

    for item in risks or []:
        row = [
            item.get("description", ""),
            item.get("category", "risk"),
            item.get("severity", "Medium"),
            item.get("mitigation", ""),
        ]
        severity = item.get("severity", "Medium")
        s_color = severity_colors.get(severity, (0, 0, 0))

        row_height = 6
        for i, (text, width) in enumerate(zip(row, col_widths)):
            safe = str(text).encode("latin-1", errors="replace").decode("latin-1")
            lines = max(1, len(safe) // max(1, width // 2))
            row_height = max(row_height, lines * 5)

        for col_idx, (text, width) in enumerate(zip(row, col_widths)):
            safe = str(text).encode("latin-1", errors="replace").decode("latin-1")
            if col_idx == 2:  # Severity
                r, g, b = s_color
                pdf.set_text_color(r, g, b)
                pdf.cell(width, row_height, safe, border=1, align="C")
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(width, row_height, safe[:80], border=1)
        pdf.ln()

    return _pdf_bytes(pdf)


# ---------------------------------------------------------------------------
# MOM exports
# ---------------------------------------------------------------------------

def mom_to_docx(mom_document: str) -> bytes:
    doc = Document()

    lines = _clean(mom_document).split("\n")
    first_line = True
    for line in lines:
        line = line.rstrip()
        if not line:
            doc.add_paragraph("")
            continue

        if first_line and line:
            # First non-empty line is the main title
            heading = doc.add_heading(line, level=0)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            first_line = False
        elif line.endswith("===") or line.startswith("==="):
            # Section underline — skip rendering the === line
            continue
        elif len(line) > 0 and line == line.upper() and len(line.split()) <= 8:
            # All-caps short lines are section headers
            doc.add_heading(line, level=2)
        else:
            doc.add_paragraph(line)

    return _docx_bytes(doc)


def mom_to_pdf(mom_document: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    lines = _clean(mom_document).split("\n")
    first_line = True

    for line in lines:
        line = line.rstrip()
        safe = line.encode("latin-1", errors="replace").decode("latin-1")

        if not safe:
            pdf.ln(3)
            continue

        if first_line and safe:
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, safe, ln=True, align="C")
            first_line = False
        elif "===" in safe:
            continue  # Skip separator lines
        elif len(safe) > 0 and safe == safe.upper() and len(safe.split()) <= 8:
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(4)
            pdf.cell(0, 8, safe, ln=True)
            pdf.set_font("Helvetica", size=10)
        else:
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 6, safe)

    return _pdf_bytes(pdf)


# ---------------------------------------------------------------------------
# Email draft export
# ---------------------------------------------------------------------------

def email_to_txt(email_draft: str) -> bytes:
    return _clean(email_draft).encode("utf-8")


# ---------------------------------------------------------------------------
# Generic text-to-PDF export
# ---------------------------------------------------------------------------

def text_to_pdf(title: str, content: str) -> bytes:
    """Generic text-to-PDF for explanation and steps."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _clean(title), ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)
    _pdf_multiline(pdf, _clean(content))
    return _pdf_bytes(pdf)
