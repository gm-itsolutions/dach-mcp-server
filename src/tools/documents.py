"""
Dokumenten-Tools
=================
Erstellt Gefährdungsbeurteilungen als PDF nach BG BAU Muster.
"""

import json
import base64
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
    KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", "/app/templates"))

# ──────────────────────────────────────────────────
# Farb-Palette
# ──────────────────────────────────────────────────
COLOR_PRIMARY = colors.HexColor("#1B2A4A")      # Dunkelblau – Header
COLOR_SECONDARY = colors.HexColor("#2C5F8A")    # Mittelblau – Akzente
COLOR_HEADER_TEXT = colors.white
COLOR_RISK_HIGH = colors.HexColor("#F8D7DA")     # Rot – hohes Risiko
COLOR_RISK_MEDIUM = colors.HexColor("#FFF3CD")   # Gelb – mittleres Risiko
COLOR_RISK_LOW = colors.HexColor("#D4EDDA")      # Grün – niedriges Risiko
COLOR_ROW_ALT = colors.HexColor("#F8F9FA")       # Hellgrau – Zebra-Streifen
COLOR_BORDER = colors.HexColor("#DEE2E6")        # Rahmenfarbe


def _get_risk_color(risiko: str) -> colors.Color:
    """Gibt die Hintergrundfarbe für eine Risikostufe zurück."""
    r = risiko.lower().strip()
    if r == "hoch":
        return COLOR_RISK_HIGH
    elif r == "mittel":
        return COLOR_RISK_MEDIUM
    return COLOR_RISK_LOW


def _get_risk_label(risiko: str) -> str:
    """Normalisiert die Risiko-Bezeichnung."""
    r = risiko.lower().strip()
    if r == "hoch":
        return "⚠ HOCH"
    elif r == "mittel":
        return "⚡ MITTEL"
    return "✓ NIEDRIG"


def _build_styles() -> dict:
    """Erstellt die PDF-Styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=COLOR_PRIMARY,
        spaceAfter=4 * mm,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontSize=10,
        fontName="Helvetica",
        textColor=COLOR_SECONDARY,
        spaceAfter=6 * mm,
    ))
    styles.add(ParagraphStyle(
        name="SectionHead",
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=COLOR_PRIMARY,
        spaceBefore=8 * mm,
        spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name="CellText",
        fontSize=7.5,
        fontName="Helvetica",
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="CellBold",
        fontSize=7.5,
        fontName="Helvetica-Bold",
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="FooterText",
        fontSize=7,
        fontName="Helvetica",
        textColor=colors.HexColor("#6C757D"),
        alignment=TA_CENTER,
    ))

    return styles


def register_document_tools(mcp):
    """Registriert alle Dokumenten-Tools beim MCP Server."""

    @mcp.tool()
    def create_gefaehrdungsbeurteilung(
        projekt_name: str,
        baustelle_adresse: str,
        ersteller: str,
        gefaehrdungen: str,
        datum: str = "",
        auftraggeber: str = "",
        bauvorhaben_art: str = "",
        fotos_base64: str = "[]",
    ) -> str:
        """Erstellt eine Gefährdungsbeurteilung als PDF-Dokument.

        Generiert ein professionelles PDF nach dem Muster der BG BAU
        Gefährdungsbeurteilung mit farbcodierter Risikobewertung,
        Maßnahmen und optionaler Fotodokumentation.

        Args:
            projekt_name: Name des Bauprojekts / Bauvorhabens
            baustelle_adresse: Vollständige Adresse der Baustelle
            ersteller: Name des Erstellers der Gefährdungsbeurteilung
            gefaehrdungen: JSON-String mit Array von Gefährdungsobjekten.
                Jedes Objekt enthält:
                {
                    "nr": 1,
                    "bereich": "z.B. Dacharbeiten, Gerüstbau, Transport",
                    "gefaehrdung": "Beschreibung der konkreten Gefährdung",
                    "risiko": "hoch" | "mittel" | "niedrig",
                    "massnahmen": "Beschreibung der Schutzmaßnahmen",
                    "verantwortlich": "Name oder Rolle des Verantwortlichen",
                    "frist": "Umsetzungsfrist z.B. 'sofort' oder '15.03.2026'",
                    "erledigt": false
                }
            datum: Datum der Beurteilung im Format YYYY-MM-DD (Standard: heute)
            auftraggeber: Name des Auftraggebers (optional)
            bauvorhaben_art: Art des Bauvorhabens z.B. "Dachsanierung" (optional)
            fotos_base64: JSON-Array mit Foto-Objekten für Fotodokumentation (optional).
                Jedes Objekt: {"image_base64": "...", "beschreibung": "Beschreibungstext"}

        Returns:
            JSON-String mit:
            - success: true/false
            - pdf_base64: Das PDF als Base64-kodierter String (zum Download)
            - filename: Vorgeschlagener Dateiname
            - gefaehrdungen_count: Anzahl der Gefährdungen
            - risiko_zusammenfassung: Aufschlüsselung nach Risikostufe
        """
        try:
            # Parameter verarbeiten
            gefaehrdungen_list = json.loads(gefaehrdungen)
            fotos_list = json.loads(fotos_base64) if fotos_base64 != "[]" else []

            if not datum:
                datum = datetime.now().strftime("%Y-%m-%d")

            datum_display = datetime.strptime(datum, "%Y-%m-%d").strftime("%d.%m.%Y")
            erstellt_am = datetime.now().strftime("%d.%m.%Y %H:%M")

            styles = _build_styles()

            # ── PDF erstellen ──
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=1.5 * cm,
                rightMargin=1.5 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
                title=f"Gefährdungsbeurteilung – {projekt_name}",
                author=ersteller,
            )

            story = []

            # ── 1. Kopfbereich ──
            story.append(Paragraph("GEFÄHRDUNGSBEURTEILUNG", styles["DocTitle"]))
            story.append(Paragraph(
                "nach §§ 5, 6 Arbeitsschutzgesetz (ArbSchG) · DGUV Vorschrift 1",
                styles["DocSubtitle"],
            ))

            # Trennlinie
            line_table = Table(
                [[""]],
                colWidths=[doc.width],
                rowHeights=[1],
            )
            line_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_SECONDARY),
            ]))
            story.append(line_table)
            story.append(Spacer(1, 4 * mm))

            # ── 2. Projektdaten ──
            story.append(Paragraph("Projektdaten", styles["SectionHead"]))

            projekt_rows = [
                ["Projekt / Bauvorhaben:", projekt_name],
                ["Baustelle:", baustelle_adresse],
            ]
            if bauvorhaben_art:
                projekt_rows.append(["Art des Bauvorhabens:", bauvorhaben_art])
            if auftraggeber:
                projekt_rows.append(["Auftraggeber:", auftraggeber])
            projekt_rows.extend([
                ["Datum der Beurteilung:", datum_display],
                ["Erstellt von:", ersteller],
                ["Erstellt am:", erstellt_am],
            ])

            # Projektdaten in Paragraph-Objekte umwandeln für Textumbruch
            projekt_cells = []
            for label, value in projekt_rows:
                projekt_cells.append([
                    Paragraph(label, styles["CellBold"]),
                    Paragraph(str(value), styles["CellText"]),
                ])

            t = Table(projekt_cells, colWidths=[4.5 * cm, doc.width - 4.5 * cm])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
            ]))
            story.append(t)

            # ── 3. Gefährdungstabelle ──
            story.append(Paragraph(
                "Ermittelte Gefährdungen und Schutzmaßnahmen",
                styles["SectionHead"],
            ))

            # Risiko-Zusammenfassung
            risk_counts = {"hoch": 0, "mittel": 0, "niedrig": 0}
            for g in gefaehrdungen_list:
                r = g.get("risiko", "mittel").lower().strip()
                if r in risk_counts:
                    risk_counts[r] += 1

            summary_text = (
                f'<font color="#DC3545"><b>⚠ Hoch: {risk_counts["hoch"]}</b></font>'
                f'&nbsp;&nbsp;|&nbsp;&nbsp;'
                f'<font color="#FFC107"><b>⚡ Mittel: {risk_counts["mittel"]}</b></font>'
                f'&nbsp;&nbsp;|&nbsp;&nbsp;'
                f'<font color="#28A745"><b>✓ Niedrig: {risk_counts["niedrig"]}</b></font>'
            )
            story.append(Paragraph(summary_text, styles["Normal"]))
            story.append(Spacer(1, 3 * mm))

            # Tabellen-Header
            col_widths = [
                0.8 * cm,   # Nr.
                2.2 * cm,   # Bereich
                3.8 * cm,   # Gefährdung
                1.4 * cm,   # Risiko
                4.2 * cm,   # Maßnahmen
                2.0 * cm,   # Verantw.
                1.6 * cm,   # Frist
                0.9 * cm,   # ✓
            ]

            header_row = [
                Paragraph("<b>Nr.</b>", styles["CellBold"]),
                Paragraph("<b>Bereich</b>", styles["CellBold"]),
                Paragraph("<b>Gefährdung</b>", styles["CellBold"]),
                Paragraph("<b>Risiko</b>", styles["CellBold"]),
                Paragraph("<b>Schutzmaßnahmen</b>", styles["CellBold"]),
                Paragraph("<b>Verantw.</b>", styles["CellBold"]),
                Paragraph("<b>Frist</b>", styles["CellBold"]),
                Paragraph("<b>✓</b>", styles["CellBold"]),
            ]

            rows = [header_row]

            for i, g in enumerate(gefaehrdungen_list):
                nr = g.get("nr", i + 1)
                erledigt_symbol = "☑" if g.get("erledigt", False) else "☐"

                row = [
                    Paragraph(str(nr), styles["CellText"]),
                    Paragraph(g.get("bereich", ""), styles["CellText"]),
                    Paragraph(g.get("gefaehrdung", ""), styles["CellText"]),
                    Paragraph(
                        _get_risk_label(g.get("risiko", "mittel")),
                        styles["CellBold"],
                    ),
                    Paragraph(g.get("massnahmen", ""), styles["CellText"]),
                    Paragraph(g.get("verantwortlich", ""), styles["CellText"]),
                    Paragraph(g.get("frist", ""), styles["CellText"]),
                    Paragraph(erledigt_symbol, styles["CellText"]),
                ]
                rows.append(row)

            t = Table(rows, colWidths=col_widths, repeatRows=1)

            # Basis-Style
            table_style_cmds = [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_HEADER_TEXT),
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]

            # Risiko-Farben und Zebra-Streifen
            for i, g in enumerate(gefaehrdungen_list):
                row_idx = i + 1  # +1 wegen Header

                # Risiko-Spalte einfärben
                risk_color = _get_risk_color(g.get("risiko", "mittel"))
                table_style_cmds.append(
                    ("BACKGROUND", (3, row_idx), (3, row_idx), risk_color)
                )

                # Zebra-Streifen (jede zweite Zeile leicht grau)
                if i % 2 == 1:
                    table_style_cmds.append(
                        ("BACKGROUND", (0, row_idx), (2, row_idx), COLOR_ROW_ALT)
                    )
                    table_style_cmds.append(
                        ("BACKGROUND", (4, row_idx), (-1, row_idx), COLOR_ROW_ALT)
                    )

            t.setStyle(TableStyle(table_style_cmds))
            story.append(t)

            # ── 4. Fotodokumentation (optional) ──
            if fotos_list:
                story.append(PageBreak())
                story.append(Paragraph("Fotodokumentation", styles["SectionHead"]))

                for foto_idx, foto in enumerate(fotos_list, 1):
                    try:
                        img_data = base64.b64decode(foto["image_base64"])
                        img_buffer = BytesIO(img_data)

                        # Bildgröße ermitteln und proportional skalieren
                        pil_img = Image.open(BytesIO(img_data))
                        img_w, img_h = pil_img.size
                        max_w = 14 * cm
                        max_h = 9 * cm
                        ratio = min(max_w / img_w, max_h / img_h)
                        display_w = img_w * ratio
                        display_h = img_h * ratio

                        img = RLImage(img_buffer, width=display_w, height=display_h)
                        img.hAlign = "CENTER"

                        beschreibung = foto.get("beschreibung", f"Foto {foto_idx}")

                        # Foto + Beschreibung zusammenhalten
                        foto_block = KeepTogether([
                            Paragraph(
                                f"<b>Foto {foto_idx}:</b> {beschreibung}",
                                styles["Normal"],
                            ),
                            Spacer(1, 2 * mm),
                            img,
                            Spacer(1, 5 * mm),
                        ])
                        story.append(foto_block)

                    except Exception as e:
                        story.append(Paragraph(
                            f"[Foto {foto_idx} konnte nicht eingebettet werden: {str(e)}]",
                            styles["Normal"],
                        ))

            # ── 5. Unterschriften ──
            story.append(Spacer(1, 15 * mm))
            story.append(Paragraph("Unterschriften", styles["SectionHead"]))

            sig_col_w = (doc.width - 2 * cm) / 2
            sig_data = [
                [
                    "_" * 40,
                    "",
                    "_" * 40,
                ],
                [
                    Paragraph("Ersteller / Fachkraft für Arbeitssicherheit", styles["CellText"]),
                    "",
                    Paragraph("Bauleiter / Aufsichtführender", styles["CellText"]),
                ],
                [
                    Paragraph(f"Datum: {datum_display}", styles["CellText"]),
                    "",
                    Paragraph("Datum: _______________", styles["CellText"]),
                ],
            ]
            sig_table = Table(sig_data, colWidths=[sig_col_w, 2 * cm, sig_col_w])
            sig_table.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
            ]))
            story.append(sig_table)

            # ── 6. Footer-Hinweis ──
            story.append(Spacer(1, 10 * mm))
            story.append(Paragraph(
                "Diese Gefährdungsbeurteilung wurde KI-gestützt erstellt und muss "
                "von einer fachkundigen Person geprüft und freigegeben werden. "
                "Rechtsgrundlage: §§ 5, 6 ArbSchG · DGUV Vorschrift 1 · "
                "ArbStättV · BetrSichV · TRBS 2121",
                styles["FooterText"],
            ))

            # ── PDF generieren ──
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            pdf_b64 = base64.b64encode(pdf_bytes).decode()

            # Dateiname
            safe_name = projekt_name.replace(" ", "_").replace("/", "-")[:50]
            filename = f"Gefaehrdungsbeurteilung_{safe_name}_{datum}.pdf"

            return json.dumps({
                "success": True,
                "pdf_base64": pdf_b64,
                "filename": filename,
                "size_kb": round(len(pdf_bytes) / 1024, 1),
                "gefaehrdungen_count": len(gefaehrdungen_list),
                "risiko_zusammenfassung": risk_counts,
                "fotos_count": len(fotos_list),
            })

        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"JSON-Parsing-Fehler bei den Gefährdungen: {str(e)}",
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Fehler bei PDF-Erstellung: {str(e)}",
            })

    @mcp.tool()
    def get_standard_gefaehrdungen() -> str:
        """Gibt branchenübliche Standard-Gefährdungen für Dachdecker- und Gerüstbauarbeiten zurück.

        Diese vorgefertigten Gefährdungen basieren auf DGUV Vorschrift 38,
        TRBS 2121 und BG BAU Handlungshilfen. Sie können als Ausgangsbasis
        für eine projektspezifische Gefährdungsbeurteilung verwendet werden.

        Returns:
            JSON-String mit Array von Standard-Gefährdungen, jeweils mit
            bereich, gefaehrdung, risiko, massnahmen und rechtsgrundlage.
        """
        standards = [
            {
                "nr": 1,
                "bereich": "Dacharbeiten",
                "gefaehrdung": "Absturz von der Dachfläche/Dachkante",
                "risiko": "hoch",
                "massnahmen": "Seitenschutz an Dachkanten, Fangnetze, PSAgA mit Auffanggurt und Sicherungsseil. Prüfung der Anschlagpunkte vor Arbeitsbeginn.",
                "rechtsgrundlage": "TRBS 2121, DGUV Vorschrift 38, ArbStättV §3a",
            },
            {
                "nr": 2,
                "bereich": "Dacharbeiten",
                "gefaehrdung": "Durchsturz durch nicht tragfähige Bauteile (Lichtplatten, Faserzementplatten, morsche Dachlatten)",
                "risiko": "hoch",
                "massnahmen": "Durchsturzsicherung durch Schutznetze oder begehbare Abdeckungen. Kennzeichnung nicht tragfähiger Flächen. Laufstege bei Arbeiten auf Dächern mit nicht durchtrittsicherer Eindeckung.",
                "rechtsgrundlage": "TRBS 2121 Teil 1, DGUV Information 201-023",
            },
            {
                "nr": 3,
                "bereich": "Gerüstbau",
                "gefaehrdung": "Absturz während Auf-, Um- oder Abbau des Gerüsts",
                "risiko": "hoch",
                "massnahmen": "Voreilender Seitenschutz, PSAgA während Montage, nur geschultes und unterwiesenes Personal (Gerüstbauer). Montage nach Aufbau- und Verwendungsanleitung des Herstellers.",
                "rechtsgrundlage": "TRBS 2121 Teil 1, DGUV Vorschrift 38, BetrSichV Anhang 1",
            },
            {
                "nr": 4,
                "bereich": "Gerüstbau",
                "gefaehrdung": "Umkippen oder Versagen der Gerüstkonstruktion",
                "risiko": "hoch",
                "massnahmen": "Standsicherheitsnachweis, ordnungsgemäße Verankerung nach Herstellerangaben, regelmäßige Prüfung durch befähigte Person. Lastannahmen dokumentieren.",
                "rechtsgrundlage": "TRBS 2121 Teil 1, DIN EN 12811",
            },
            {
                "nr": 5,
                "bereich": "Gerüst (Nutzung)",
                "gefaehrdung": "Fehlender oder unvollständiger Seitenschutz (Geländer, Zwischenholm, Bordbrett)",
                "risiko": "hoch",
                "massnahmen": "Dreiteiliger Seitenschutz: Geländerholm (1,00 m), Zwischenholm (0,50 m), Bordbrett (mind. 15 cm). Prüfung vor jeder Arbeitsschicht. Freigabe-Kennzeichnung (Prüfprotokoll).",
                "rechtsgrundlage": "TRBS 2121 Teil 1, ArbStättV",
            },
            {
                "nr": 6,
                "bereich": "Transport / Materiallagerung",
                "gefaehrdung": "Herabfallende Gegenstände, Materialien oder Werkzeuge",
                "risiko": "mittel",
                "massnahmen": "Bordbretter am Gerüst, Werkzeug-Sicherungsbänder, Absperrung des Gefahrenbereichs unter der Arbeitsstelle. Schutzhelmpflicht (EN 397).",
                "rechtsgrundlage": "DGUV Vorschrift 38, ArbStättV",
            },
            {
                "nr": 7,
                "bereich": "Transport / Heben",
                "gefaehrdung": "Manuelle Handhabung schwerer Lasten (Dachziegel, Gerüstteile)",
                "risiko": "mittel",
                "massnahmen": "Einsatz von Aufzügen/Kranen, maximale Traglasten beachten, ergonomische Unterweisung, Wechsel zwischen Tätigkeiten.",
                "rechtsgrundlage": "LasthandhabV, DGUV Information 208-033",
            },
            {
                "nr": 8,
                "bereich": "Allgemein",
                "gefaehrdung": "Witterungseinflüsse (Sturm, Regen, Eis, Hitze)",
                "risiko": "mittel",
                "massnahmen": "Arbeitsunterbrechung bei Windstärke ≥ 6 (Dacharbeiten) bzw. ≥ 8 (Gerüstmontage). Rutschfeste Schuhe bei Nässe. UV-Schutz und Trinkwasser bei Hitze. Tägliche Witterungsprüfung.",
                "rechtsgrundlage": "DGUV Vorschrift 38, ArbStättV §3a, TRBS 2121",
            },
            {
                "nr": 9,
                "bereich": "Elektrik",
                "gefaehrdung": "Kontakt mit elektrischen Freileitungen oder Installationen",
                "risiko": "hoch",
                "massnahmen": "Mindestabstand 3 m (bis 1 kV) bzw. 5 m (über 1 kV) zu Freileitungen. Absprache mit Energieversorger. Bei Gerüststellung: Abschaltung oder Abdeckung.",
                "rechtsgrundlage": "DGUV Vorschrift 3, BetrSichV",
            },
            {
                "nr": 10,
                "bereich": "Allgemein",
                "gefaehrdung": "Fehlende oder unzureichende PSA (Schutzhelm, Sicherheitsschuhe, Handschuhe)",
                "risiko": "mittel",
                "massnahmen": "Bereitstellung und Tragepflicht: Schutzhelm (EN 397), Sicherheitsschuhe S3 (EN 20345), Schutzhandschuhe bei Bedarf, Schutzbrille bei Schneidarbeiten. Regelmäßige Unterweisung.",
                "rechtsgrundlage": "PSA-BV, DGUV Vorschrift 1, DGUV Regel 112-989",
            },
        ]

        return json.dumps({
            "success": True,
            "standards": standards,
            "hinweis": "Diese Standard-Gefährdungen sind als Ausgangsbasis gedacht. "
                       "Ergänze projektspezifische Gefährdungen basierend auf der "
                       "Baustellenanalyse (Fotos/Videos).",
        })
