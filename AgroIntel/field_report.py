"""Build downloadable field reports as portable PDF documents."""

from __future__ import annotations

from io import BytesIO
import unicodedata
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


GREEN = colors.HexColor("#1b5e20")
PALE_GREEN = colors.HexColor("#eaf5e8")
MUTED = colors.HexColor("#607064")


def _display(value: object) -> str:
    if value is None or value == "":
        return "Not provided"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return normalized.replace("_", " ")


def _table(rows: list[list[object]], widths: list[float] | None = None) -> Table:
    if widths is None and rows:
        widths = [176 * mm / len(rows[0])] * len(rows[0])
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREEN]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d8e4d8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def build_field_report_pdf(report: dict) -> bytes:
    """Render the recommendation, soil lab categories, and analysis as a PDF."""
    output = BytesIO()
    is_soil_only = not report.get("field") and not report.get("crop_recommendation")
    title = "AgroIntel Soil Analysis Report" if is_soil_only else "AgroIntel Field Report"
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"{title} - {report.get('field', {}).get('name', 'Field')}",
        author="AgroIntel",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AgroTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=25, textColor=GREEN, alignment=TA_CENTER, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="AgroSection", parent=styles["Heading2"], fontSize=12,
        leading=15, textColor=GREEN, spaceBefore=14, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="AgroBody", parent=styles["BodyText"], fontSize=8.5,
        leading=12, textColor=MUTED,
    ))
    story = [
        Paragraph(title, styles["AgroTitle"]),
        Paragraph(
            "Soil measurements and lab rating summary" if is_soil_only
            else "Crop recommendation and soil report summary",
            styles["AgroBody"],
        ),
        Spacer(1, 10),
    ]

    field = report.get("field", {})
    if field:
        story.extend([
            Paragraph("Field details", styles["AgroSection"]),
            _table([
                ["Field", "District", "Season", "Report date (UTC)"],
                [_display(field.get("name")), _display(field.get("district_or_location")),
                 _display(report.get("season")), _display(field.get("created_at"))],
            ]),
        ])

    crop = report.get("crop_recommendation")
    if crop or report.get("selected_model"):
        story.extend([
            Paragraph("Crop recommendation", styles["AgroSection"]),
            _table([
                ["Recommended crop", "Model top crop", "District context", "Season"],
                [_display(crop), _display(report.get("unadjusted_model_crop")),
                 _display(report.get("district_region_context")), _display(report.get("season"))],
            ]),
            _table([
                ["Selected model", "Adjusted rank score", "District prior", "Dataset rows / classes"],
                [_display(report.get("selected_model")), _display(report.get("district_adjusted_rank_score")),
                 _display(f"Applied · {report.get('district_context_influence', 0)}%" if report.get("district_context_applied") else "Not applied"),
                 f"{_display(report.get('dataset', {}).get('rows'))} / "
                 f"{_display(report.get('dataset', {}).get('crop_classes'))}"],
            ]),
            Paragraph(
                "This crop is listed in the region's ICAR Kharif advisory coverage."
                if report.get("district_crop_in_advisory")
                else "This crop is not listed in the region's ICAR Kharif advisory coverage; local suitability is unverified.",
                styles["AgroBody"],
            ),
            Paragraph("The Kharif district context is a bounded regional crop-advisory prior, not measured district crop prevalence. It is not applied for unsupported seasons. The model was not trained with district data; rank scores are not probabilities of harvest success.", styles["AgroBody"]),
        ])
    local_stats = report.get("local_crop_statistics")
    local_check = report.get("local_crop_comparison") or {}
    if local_stats:
        story.extend([
            Paragraph("District crop records", styles["AgroSection"]),
            Paragraph(
                f"Observed area records for {escape(_display(field.get('district_or_location')))}, "
                f"{escape(_display(report.get('season')))}, {escape(_display(local_stats.get('year')))}. "
                "These are historical reported crop areas, not suitability estimates.",
                styles["AgroBody"],
            ),
            _table([["Reported crop", "Area (ha)", "Share of reported area", "Rank"]] + [
                [_display(row.get("crop")), _display(row.get("area_ha")),
                 f"{float(row.get('share', 0)):.1%}", _display(row.get("rank"))]
                for row in local_stats.get("rows", [])[:5]
            ]),
            Spacer(1, 5),
        ])
        if report.get("local_crop_statistics_is_demo"):
            story.append(Paragraph(
                "SYNTHETIC DEMO DATA — invented values for software verification only; not official district statistics and not for farming decisions.",
                styles["AgroBody"],
            ))
        match = local_check.get("record") or {}
        story.append(Paragraph(
            f"Suggested-crop record status: {escape(_display(local_check.get('status')))}. "
            f"{escape(_display(local_check.get('reason')))}"
            + (f" Reported area: {float(match['area_ha']):,.1f} ha (rank {int(match['rank'])})." if match else ""),
            styles["AgroBody"],
        ))
        story.append(Paragraph(
            "Missing crop rows mean no matching record in this dataset and year; they are not interpreted as zero area. "
            "Historical area patterns do not establish whether a crop can grow on this specific field.",
            styles["AgroBody"],
        ))
        if report.get("local_crop_statistics_source"):
            story.append(Paragraph(
                f"Statistics file: {escape(_display(report.get('local_crop_statistics_source')))}",
                styles["AgroBody"],
            ))
    elif local_check:
        story.extend([
            Paragraph("District crop records", styles["AgroSection"]),
            Paragraph(
                "Local record comparison unavailable: " + escape(_display(local_check.get("reason"))),
                styles["AgroBody"],
            ),
        ])
    alternatives = report.get("model_ranked_alternatives") or []
    if alternatives:
        story.extend([
            Spacer(1, 6),
            _table([["Other crop options", "District adjusted rank score", "Original model score"]] + [
                [_display(item.get("Crop option")), _display(item.get("District-adjusted rank score")),
                 _display(item.get("Original model score"))]
                for item in alternatives
            ]),
        ])

    inputs = report.get("model_input_values") or {}
    if inputs:
        story.extend([
            Paragraph("Crop model input values", styles["AgroSection"]),
            _table([["Input", "Entered value"]] + [[key, _display(value)] for key, value in inputs.items()]),
        ])

    soil_analysis = report.get("soil_health_analysis") or {}
    soil_values = soil_analysis.get("values") or {}
    guidance_ratings = (report.get("soil_lab_analysis") or {}).get("ratings") or {}
    lab_ratings = {**guidance_ratings, **(soil_values.get("lab_ratings") or {})}
    story.append(Paragraph("Soil lab ratings", styles["AgroSection"]))
    if lab_ratings:
        story.append(_table([
            ["Nutrient", "Rating as reported by the lab"],
            ["Nitrogen (N)", _display(lab_ratings.get("N"))],
            ["Phosphorus (P)", _display(lab_ratings.get("P"))],
            ["Potassium (K)", _display(lab_ratings.get("K"))],
        ]))
        story.append(Spacer(1, 5))
        story.append(Paragraph(
            "These categories are entered from the soil laboratory report; raw NPK values are not converted into rating categories.",
            styles["AgroBody"],
        ))
    else:
        story.append(Paragraph(
            "No N/P/K category ratings were entered from a lab report.", styles["AgroBody"]
        ))
    if soil_values:
        numeric_values = {key: value for key, value in soil_values.items() if key != "lab_ratings"}
        if numeric_values:
            story.extend([
                Paragraph("Additional soil measurements", styles["AgroSection"]),
                _table([["Measurement", "Entered value"]] + [
                    [key.replace("_", " ").title(), _display(value)]
                    for key, value in numeric_values.items()
                ]),
            ])
    if soil_analysis:
        story.extend([
            Paragraph("Reference rule screening", styles["AgroSection"]),
            _table([
                ["Numeric checks outside reference bands"],
                [f"{soil_analysis.get('flag_count', 'Not available')} / {soil_analysis.get('check_count', 9)}"],
            ]),
        ])
        flagged_measurements = soil_analysis.get("flagged_measurements") or []
        if flagged_measurements:
            story.append(Paragraph(
                "Flagged numeric checks: " + escape(_display(", ".join(flagged_measurements))),
                styles["AgroBody"],
            ))
        for title, key in (("Findings", "findings"), ("Nutrient and amendment notes", "fertilizer_notes"),
                           ("Water and soil notes", None)):
            notes = soil_analysis.get(key, []) if key else (
                soil_analysis.get("irrigation_notes", []) + soil_analysis.get("soil_notes", [])
            )
            if notes:
                story.append(Paragraph(title, styles["AgroSection"]))
                story.append(Paragraph("<br/>".join(f"- {escape(_display(note))}" for note in notes), styles["AgroBody"]))
        if soil_analysis.get("summary"):
            story.append(Paragraph(escape(_display(soil_analysis["summary"])), styles["AgroBody"]))
        if soil_analysis.get("limitations"):
            story.append(Spacer(1, 4))
            story.append(Paragraph(escape(_display(soil_analysis["limitations"])), styles["AgroBody"]))

    guidance = report.get("soil_lab_analysis")
    if guidance and guidance.get("guidance"):
        story.extend([
            Paragraph("Crop-specific soil lab guidance", styles["AgroSection"]),
            Paragraph(
                f"Crop: {escape(_display(guidance.get('crop', '')))} | Context: {escape(_display(guidance.get('region', '')))}",
                styles["AgroBody"],
            ),
            Spacer(1, 5),
        ])
        rating_key = {"N": "N", "P₂O₅": "P", "K₂O": "K"}
        rates = guidance.get("guidance", {}).get("rates", {})
        base = guidance.get("base_rates", {})
        story.append(_table([["Nutrient", "Lab rating", "Published baseline reference kg/ha"]] + [
            [_display(nutrient), _display(guidance.get("ratings", {}).get(rating_key.get(nutrient))),
             _display(base.get(nutrient, rates.get(nutrient)))]
            for nutrient in rates
        ]))
        story.append(Spacer(1, 5))
        story.append(Paragraph(
            "Published baseline reference only. It is not adjusted by lab ratings. Follow the current Soil Health Card or confirm with the local KVK.",
            styles["AgroBody"],
        ))

    metrics = report.get("selected_model_metrics") or {}
    if metrics:
        story.extend([
            Paragraph("Selected model evaluation", styles["AgroSection"]),
            _table([["Metric", "Value"]] + [[key, _display(value)] for key, value in metrics.items()]),
        ])
    source = report.get("dataset", {}).get("source")
    if source:
        story.extend([Spacer(1, 8), Paragraph(f"Dataset source: {escape(_display(source))}", styles["AgroBody"])])
        digest = report.get("dataset", {}).get("sha256")
        if digest:
            story.append(Paragraph(f"Dataset SHA-256: {escape(_display(digest))}", styles["AgroBody"]))

    def page_footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(17 * mm, 10 * mm, "AgroIntel · Decision support; confirm recommendations with local soil guidance")
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return output.getvalue()
