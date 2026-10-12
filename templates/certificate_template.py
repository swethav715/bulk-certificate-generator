"""ReportLab PDF Certificate Template.

Generates a professional, landscape A4 certificate of completion with decorative
borders, gold/navy accents, clean typography, verification badge, and signature block.
"""

from pathlib import Path
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def generate_certificate_pdf(
    file_path: str,
    recipient_name: str,
    event_name: str,
    completion_date: str,
    organization_name: str,
    certificate_id: str,
    certificate_title: str = "Certificate of Completion",
    extra_info: Optional[str] = None,
) -> str:
    """Generate a single landscape A4 PDF certificate.

    Args:
        file_path: The filesystem path where the PDF will be saved.
        recipient_name: Recipient's full name.
        event_name: Course, workshop, or event name.
        completion_date: Formatted completion date string.
        organization_name: Name of the issuing organization.
        certificate_id: Unique certificate verification ID.
        certificate_title: Title heading on the certificate.
        extra_info: Optional additional text (e.g. Distinction, Grade).

    Returns:
        The absolute path to the generated PDF.
    """
    dest = Path(file_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Page dimensions (Landscape A4: 841.89 x 595.27 points)
    page_width, page_height = landscape(A4)
    center_x = page_width / 2.0

    # Initialize canvas
    c = canvas.Canvas(str(dest), pagesize=landscape(A4))
    c.setTitle(f"{certificate_title} - {recipient_name}")
    c.setAuthor(organization_name)
    c.setSubject(event_name)

    # Colors
    c_navy = colors.HexColor("#0F294A")
    c_gold = colors.HexColor("#C59B27")
    c_gold_light = colors.HexColor("#EED07A")
    c_text_dark = colors.HexColor("#1A202C")
    c_text_muted = colors.HexColor("#4A5568")
    c_bg_tint = colors.HexColor("#FCFDFD")

    # 1. Subtle Background Tint
    c.setFillColor(c_bg_tint)
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # 2. Outer Border (Deep Navy)
    c.setStrokeColor(c_navy)
    c.setLineWidth(4.0)
    c.rect(20, 20, page_width - 40, page_height - 40)

    # 3. Inner Decorative Border (Gold)
    c.setStrokeColor(c_gold)
    c.setLineWidth(1.5)
    c.rect(28, 28, page_width - 56, page_height - 56)

    # Corner Decorative Squares
    corner_size = 14
    for cx, cy in [
        (28, 28),
        (page_width - 28 - corner_size, 28),
        (28, page_height - 28 - corner_size),
        (page_width - 28 - corner_size, page_height - 28 - corner_size),
    ]:
        c.setFillColor(c_gold)
        c.setStrokeColor(c_navy)
        c.rect(cx, cy, corner_size, corner_size, fill=1, stroke=1)

    # 4. Issuing Organization Header
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(c_gold)
    c.drawCentredString(center_x, page_height - 75, organization_name.upper())

    # Small decorative separator line
    c.setStrokeColor(c_gold_light)
    c.setLineWidth(1)
    c.line(center_x - 120, page_height - 85, center_x + 120, page_height - 85)

    # 5. Certificate Title Heading
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(c_navy)
    c.drawCentredString(center_x, page_height - 130, certificate_title.upper())

    # 6. Presentation Subtitle
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColor(c_text_muted)
    c.drawCentredString(center_x, page_height - 165, "THIS IS PROUDLY PRESENTED TO")

    # 7. Recipient's Full Name (Prominent & Elegant)
    c.setFont("Helvetica-Bold", 30)
    c.setFillColor(c_navy)
    c.drawCentredString(center_x, page_height - 220, recipient_name)

    # Decorative Underline for Recipient Name
    text_width = c.stringWidth(recipient_name, "Helvetica-Bold", 30)
    line_w = max(text_width + 40, 260)
    c.setStrokeColor(c_gold)
    c.setLineWidth(2)
    c.line(center_x - (line_w / 2), page_height - 232, center_x + (line_w / 2), page_height - 232)

    # 8. Achievement / Completion Statement
    c.setFont("Helvetica", 13)
    c.setFillColor(c_text_muted)
    c.drawCentredString(
        center_x,
        page_height - 275,
        "for successfully completing and demonstrating excellence in",
    )

    # 9. Event or Course Name
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(c_navy)
    c.drawCentredString(center_x, page_height - 315, event_name)

    # Optional extra info
    if extra_info:
        c.setFont("Helvetica-Oblique", 11)
        c.setFillColor(c_gold)
        c.drawCentredString(center_x, page_height - 340, f"Special Recognition: {extra_info}")

    # 10. Decorative Gold Rosette / Seal (Center Bottom Accent)
    seal_x = center_x
    seal_y = 125
    c.setFillColor(c_gold)
    c.setStrokeColor(c_navy)
    c.setLineWidth(1)
    c.circle(seal_x, seal_y, 28, fill=1, stroke=1)
    c.setStrokeColor(c_gold_light)
    c.circle(seal_x, seal_y, 23, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.white)
    c.drawCentredString(seal_x, seal_y + 4, "OFFICIAL")
    c.drawCentredString(seal_x, seal_y - 6, "SEAL")

    # 11. Signatures / Metadata Blocks (Left: Date, Right: Authority)
    # Left Block: Date
    date_x = 130
    c.setStrokeColor(c_text_muted)
    c.setLineWidth(1)
    c.line(date_x - 60, 115, date_x + 60, 115)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(c_text_dark)
    c.drawCentredString(date_x, 125, completion_date)
    c.setFont("Helvetica", 9)
    c.setFillColor(c_text_muted)
    c.drawCentredString(date_x, 100, "Date of Completion")

    # Right Block: Authorized Signatory
    auth_x = page_width - 130
    c.line(auth_x - 60, 115, auth_x + 60, 115)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(c_text_dark)
    c.drawCentredString(auth_x, 125, organization_name)
    c.setFont("Helvetica", 9)
    c.setFillColor(c_text_muted)
    c.drawCentredString(auth_x, 100, "Authorized Signatory")

    # 12. Bottom Verification Badge / Certificate ID
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(c_navy)
    c.drawCentredString(
        center_x,
        45,
        f"CERTIFICATE ID: {certificate_id}",
    )
    c.setFont("Helvetica", 8)
    c.setFillColor(c_text_muted)
    c.drawCentredString(
        center_x,
        34,
        "Authenticity verified by the issuing institution. Stored securely.",
    )

    # Save and finalize
    c.showPage()
    c.save()

    return str(dest.resolve())
