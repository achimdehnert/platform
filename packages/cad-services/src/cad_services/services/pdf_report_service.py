"""PDF Report Generation Service.

Generates fire safety and escape route reports using reportlab.
"""

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


@dataclass
class ReportConfig:
    """Configuration for PDF report generation."""

    title: str = "Brandschutz-Prüfbericht"
    subtitle: str = ""
    author: str = "CAD-Hub"
    logo_path: Path | None = None
    include_toc: bool = True
    include_summary: bool = True
    page_size: tuple = A4 if REPORTLAB_AVAILABLE else (595, 842)
    margin_cm: float = 2.0


@dataclass
class FireSafetyReportData:
    """Data for fire safety report."""

    model_name: str
    project_name: str
    analysis_date: datetime = field(default_factory=datetime.now)
    building_type: str = "standard"
    has_sprinkler: bool = False
    total_elements: int = 0
    compliant_elements: int = 0
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    compartments: list[dict[str, Any]] = field(default_factory=list)
    rated_elements: list[dict[str, Any]] = field(default_factory=list)
    escape_routes: list[dict[str, Any]] = field(default_factory=list)


class PDFReportService:
    """Service for generating PDF reports."""

    def __init__(self, config: ReportConfig | None = None):
        """Initialize service.

        Args:
            config: Report configuration options
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF generation. "
                "Install with: pip install reportlab"
            )

        self.config = config or ReportConfig()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Configure custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                "Title2",
                parent=self.styles["Heading1"],
                fontSize=18,
                spaceAfter=12,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "Subtitle",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.gray,
                spaceAfter=20,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "TableHeader",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.white,
                alignment=1,  # Center
            )
        )
        self.styles.add(
            ParagraphStyle(
                "Compliant",
                parent=self.styles["Normal"],
                textColor=colors.green,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "Violation",
                parent=self.styles["Normal"],
                textColor=colors.red,
            )
        )

    def generate_fire_safety_report(
        self,
        data: FireSafetyReportData,
        output_path: Path | None = None,
    ) -> bytes | None:
        """Generate fire safety PDF report.

        Args:
            data: Report data
            output_path: Optional file path to save PDF

        Returns:
            PDF bytes if no output_path, else None
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.config.page_size,
            leftMargin=self.config.margin_cm * cm,
            rightMargin=self.config.margin_cm * cm,
            topMargin=self.config.margin_cm * cm,
            bottomMargin=self.config.margin_cm * cm,
        )

        elements = []

        # Title
        elements.append(
            Paragraph(self.config.title, self.styles["Title2"])
        )
        elements.append(
            Paragraph(
                f"Projekt: {data.project_name} | Modell: {data.model_name}",
                self.styles["Subtitle"],
            )
        )
        elements.append(Spacer(1, 10 * mm))

        # Summary section
        if self.config.include_summary:
            elements.extend(self._build_summary(data))

        # Violations section
        if data.violations:
            elements.extend(self._build_violations(data.violations))

        # Warnings section
        if data.warnings:
            elements.extend(self._build_warnings(data.warnings))

        # Fire-rated elements table
        if data.rated_elements:
            elements.extend(self._build_elements_table(data.rated_elements))

        # Escape routes table
        if data.escape_routes:
            elements.extend(self._build_routes_table(data.escape_routes))

        # Build PDF
        doc.build(elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        if output_path:
            output_path.write_bytes(pdf_bytes)
            return None

        return pdf_bytes

    def _build_summary(self, data: FireSafetyReportData) -> list:
        """Build summary section."""
        elements = []
        elements.append(Paragraph("Zusammenfassung", self.styles["Heading2"]))

        compliance_rate = (
            (data.compliant_elements / data.total_elements * 100)
            if data.total_elements > 0
            else 0
        )
        status = "KONFORM" if not data.violations else "NICHT KONFORM"
        # Status color for potential future use
        _ = colors.green if not data.violations else colors.red

        summary_data = [
            ["Eigenschaft", "Wert"],
            ["Prüfdatum", data.analysis_date.strftime("%d.%m.%Y %H:%M")],
            ["Gebäudetyp", data.building_type],
            ["Sprinkleranlage", "Ja" if data.has_sprinkler else "Nein"],
            ["Geprüfte Elemente", str(data.total_elements)],
            ["Konforme Elemente", str(data.compliant_elements)],
            ["Konformitätsrate", f"{compliance_rate:.1f}%"],
            ["Verstöße", str(len(data.violations))],
            ["Warnungen", str(len(data.warnings))],
        ]

        table = Table(summary_data, colWidths=[6 * cm, 8 * cm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ])
        )
        elements.append(table)
        elements.append(Spacer(1, 10 * mm))

        # Status badge
        status_para = Paragraph(
            f"<b>Gesamtstatus: {status}</b>",
            self.styles["Compliant"] if not data.violations else self.styles["Violation"],
        )
        elements.append(status_para)
        elements.append(Spacer(1, 10 * mm))

        return elements

    def _build_violations(self, violations: list[str]) -> list:
        """Build violations section."""
        elements = []
        elements.append(Paragraph("Verstöße", self.styles["Heading2"]))

        for i, violation in enumerate(violations, 1):
            elements.append(
                Paragraph(f"{i}. {violation}", self.styles["Violation"])
            )

        elements.append(Spacer(1, 10 * mm))
        return elements

    def _build_warnings(self, warnings: list[str]) -> list:
        """Build warnings section."""
        elements = []
        elements.append(Paragraph("Warnungen", self.styles["Heading2"]))

        for i, warning in enumerate(warnings, 1):
            elements.append(
                Paragraph(f"{i}. {warning}", self.styles["Normal"])
            )

        elements.append(Spacer(1, 10 * mm))
        return elements

    def _build_elements_table(self, rated_elements: list[dict]) -> list:
        """Build fire-rated elements table."""
        elements = []
        elements.append(
            Paragraph("Brandschutzelemente", self.styles["Heading2"])
        )

        table_data = [
            ["Typ", "Name", "Soll", "Ist", "Status"],
        ]

        for elem in rated_elements[:50]:  # Limit to 50 rows
            status = "✓" if elem.get("is_compliant") else "✗"
            table_data.append([
                elem.get("element_type", "-"),
                elem.get("name", "-")[:30],
                elem.get("required_rating", "-"),
                elem.get("actual_rating", "-"),
                status,
            ])

        table = Table(
            table_data,
            colWidths=[2.5 * cm, 6 * cm, 2 * cm, 2 * cm, 1.5 * cm],
        )
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ])
        )

        elements.append(table)
        elements.append(Spacer(1, 10 * mm))
        return elements

    def _build_routes_table(self, escape_routes: list[dict]) -> list:
        """Build escape routes table."""
        elements = []
        elements.append(Paragraph("Fluchtwege", self.styles["Heading2"]))

        table_data = [
            ["Von Raum", "Zum Ausgang", "Entfernung", "Max.", "Status"],
        ]

        for route in escape_routes[:50]:
            distance = route.get("distance_m", 0)
            max_dist = route.get("max_distance_m", 35)
            is_ok = distance <= max_dist if max_dist else True
            status = "✓" if is_ok else "✗"

            table_data.append([
                route.get("from_room_name", "-")[:25],
                route.get("to_exit_type", "-"),
                f"{distance:.1f}m",
                f"{max_dist:.1f}m",
                status,
            ])

        table = Table(
            table_data,
            colWidths=[5 * cm, 3 * cm, 2 * cm, 2 * cm, 1.5 * cm],
        )
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ])
        )

        elements.append(table)
        elements.append(Spacer(1, 10 * mm))
        return elements
