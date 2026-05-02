"""PDF generation helpers for damage reports."""

from fpdf import FPDF
from typing import Dict, List
import os


class DamageReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'KrishiBondhu Crop Damage Report', ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')


def generate_damage_pdf(report: Dict, images: List[str], output_path: str) -> str:
    pdf = DamageReportPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 8, f"Report ID: {report['id']}")
    pdf.multi_cell(0, 8, f"Farmer ID: {report['farmer_id']}")
    pdf.multi_cell(0, 8, f"Crop Type: {report['crop_type']}")
    pdf.multi_cell(0, 8, f"Damage Cause: {report['damage_cause']}")
    pdf.multi_cell(0, 8, f"Location: {report['location_lat']}, {report['location_lon']}")
    pdf.multi_cell(0, 8, f"Damage Estimate: {report['damage_estimate_percent']}%")
    pdf.multi_cell(0, 8, f"Yield Loss Estimate: {report['yield_loss_estimate_percent']}%")
    pdf.multi_cell(0, 8, f"Status: {report['status']}")
    pdf.multi_cell(0, 8, f"Submitted At: {report['submitted_at']}")
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Voice Statement:', ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 8, report.get('voice_statement_transcribed', 'No transcription available.'))
    pdf.ln(5)

    if images:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Images:', ln=True)
        for index, image_path in enumerate(images, start=1):
            if os.path.exists(image_path):
                pdf.image(image_path, w=100)
                pdf.ln(5)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    return output_path
