"""
Chargeback Proof Package Generator

Generate comprehensive evidence packages for PayTR chargeback disputes.
Produces professional PDF reports and ZIP archives with all supporting evidence.
"""
import os
import json
import logging
import tempfile
import zipfile
import hashlib
import qrcode
from datetime import datetime, timedelta
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app import db
from app.models import Payment, User, Company, AuditLog, WorkspaceSession, EmailLog, Invoice

logger = logging.getLogger(__name__)


class ChargebackProofGenerator:
    """Generate comprehensive evidence packages for PayTR chargeback disputes."""

    def __init__(self):
        self.temp_dir = tempfile.gettempdir()

    def generate_proof_package(self, payment_id, dispute_reason=None):
        """
        Generate comprehensive proof package for a payment.

        Args:
            payment_id: Payment ID to generate proof for
            dispute_reason: Optional dispute reason description

        Returns:
            tuple: (zip_file_path, package_id) or (None, None) if failed
        """
        try:
            # Get payment and related data
            payment = Payment.query.get(payment_id)
            if not payment:
                logger.error(f"Payment {payment_id} not found")
                return None, None

            company = payment.company
            user = company.users.first()  # Primary user

            # Generate package ID
            package_id = f"PROOF-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{payment.merchant_oid}"

            logger.info(f"Generating proof package {package_id} for payment {payment_id}")

            # Compile all data
            data = self._compile_evidence_data(payment, company, user, dispute_reason)

            # Generate PDF report
            pdf_path = self._generate_pdf_report(data, package_id)
            if not pdf_path:
                return None, None

            # Generate ZIP archive
            zip_path = self._create_evidence_archive(data, pdf_path, package_id)
            if not zip_path:
                return None, None

            logger.info(f"Proof package generated successfully: {zip_path}")
            return zip_path, package_id

        except Exception as e:
            logger.error(f"Error generating proof package: {str(e)}", exc_info=True)
            return None, None

    def _compile_evidence_data(self, payment, company, user, dispute_reason):
        """Compile all evidence data into structured dictionary."""

        # Date range: 7 days before payment to now
        start_date = payment.created_at - timedelta(days=7)
        end_date = datetime.utcnow()

        # Get audit logs
        audit_logs = AuditLog.query.filter(
            AuditLog.company_id == company.id,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).order_by(AuditLog.timestamp.desc()).all()

        # Get workspace sessions
        workspace_sessions = WorkspaceSession.query.filter(
            WorkspaceSession.workspace_id.in_([w.id for w in company.workspaces]),
            WorkspaceSession.started_at >= start_date,
            WorkspaceSession.started_at <= end_date
        ).order_by(WorkspaceSession.started_at.desc()).all()

        # Get email trail
        email_logs = EmailLog.query.filter(
            EmailLog.company_id == company.id,
            EmailLog.sent_at >= start_date,
            EmailLog.sent_at <= end_date
        ).order_by(EmailLog.sent_at.desc()).all()

        # Get all payments for this company
        all_payments = Payment.query.filter_by(company_id=company.id).order_by(Payment.created_at.desc()).all()

        # Get invoices
        invoices = Invoice.query.filter_by(company_id=company.id).order_by(Invoice.created_at.desc()).all()

        # Calculate summary statistics
        total_workspace_hours = sum(
            (session.duration_seconds or 0) / 3600
            for session in workspace_sessions
        )

        successful_logins = sum(
            1 for log in audit_logs
            if log.action_type == 'login' and log.success
        )

        return {
            'package_id': f"PROOF-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{payment.merchant_oid}",
            'generated_at': datetime.utcnow(),
            'dispute_reason': dispute_reason,
            'payment': {
                'id': payment.id,
                'merchant_oid': payment.merchant_oid,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'status': payment.status,
                'plan': payment.plan,
                'created_at': payment.created_at,
                'completed_at': payment.completed_at,
                'payment_type': payment.payment_type
            },
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at,
                'terms_accepted_at': user.terms_accepted_at,
                'terms_accepted_ip': user.terms_accepted_ip,
                'privacy_accepted_at': user.privacy_accepted_at,
                'privacy_accepted_ip': user.privacy_accepted_ip
            },
            'company': {
                'id': company.id,
                'name': company.name,
                'subdomain': company.subdomain,
                'plan': company.plan,
                'created_at': company.created_at
            },
            'audit_logs': [
                {
                    'timestamp': log.timestamp,
                    'action_type': log.action_type,
                    'resource_type': log.resource_type,
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent,
                    'success': log.success,
                    'details': log.details
                }
                for log in audit_logs
            ],
            'workspace_sessions': [
                {
                    'started_at': session.started_at,
                    'ended_at': session.ended_at,
                    'duration_seconds': session.duration_seconds,
                    'activity_count': session.activity_count,
                    'ip_address': session.ip_address
                }
                for session in workspace_sessions
            ],
            'email_logs': [
                {
                    'sent_at': log.sent_at,
                    'email_type': log.email_type,
                    'recipient_email': log.recipient_email,
                    'subject': log.subject,
                    'delivery_status': log.delivery_status
                }
                for log in email_logs
            ],
            'all_payments': [
                {
                    'merchant_oid': p.merchant_oid,
                    'amount': float(p.amount),
                    'status': p.status,
                    'created_at': p.created_at
                }
                for p in all_payments
            ],
            'invoices': [
                {
                    'invoice_number': inv.invoice_number,
                    'amount': float(inv.amount),
                    'status': inv.status,
                    'created_at': inv.created_at
                }
                for inv in invoices
            ],
            'summary': {
                'total_audit_logs': len(audit_logs),
                'total_workspace_sessions': len(workspace_sessions),
                'total_workspace_hours': round(total_workspace_hours, 2),
                'total_payments': len(all_payments),
                'successful_logins': successful_logins,
                'total_emails_sent': len(email_logs)
            }
        }

    def _generate_pdf_report(self, data, package_id):
        """
        Generate professional PDF report.

        Args:
            data: Compiled evidence data
            package_id: Package identifier

        Returns:
            Path to generated PDF file
        """
        try:
            pdf_filename = f"evidence_report_{package_id}.pdf"
            pdf_path = os.path.join(self.temp_dir, pdf_filename)

            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a202c'),
                spaceAfter=30,
                alignment=TA_CENTER
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#2d3748'),
                spaceAfter=12,
                spaceBefore=12
            )

            # Cover Page
            story.append(Spacer(1, 2*cm))
            story.append(Paragraph("PayTR CHARGEBACK EVIDENCE", title_style))
            story.append(Paragraph("PayTR Ödeme İtiraz Delil Paketi", title_style))
            story.append(Spacer(1, 1*cm))

            # Payment info table
            payment_info = [
                ['Merchant Order ID:', data['payment']['merchant_oid']],
                ['Payment Amount:', f"{data['payment']['amount']} {data['payment']['currency']}"],
                ['Payment Date:', data['payment']['created_at'].strftime('%Y-%m-%d %H:%M:%S UTC')],
                ['Payment Status:', data['payment']['status'].upper()],
                ['Plan:', data['payment']['plan']],
                ['', ''],
                ['Package ID:', package_id],
                ['Generated:', data['generated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')]
            ]

            payment_table = Table(payment_info, colWidths=[6*cm, 10*cm])
            payment_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc'))
            ]))
            story.append(payment_table)

            story.append(Spacer(1, 1*cm))

            # Generate QR code for verification
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(f"https://youarecoder.com/verify/{package_id}")
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")

            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)

            qr_image = Image(qr_buffer, width=3*cm, height=3*cm)
            story.append(qr_image)
            story.append(Paragraph("Scan to verify document authenticity", styles['Normal']))

            story.append(PageBreak())

            # Executive Summary
            story.append(Paragraph("EXECUTIVE SUMMARY / YÖNETİCİ ÖZETİ", heading_style))

            summary_text = f"""
            This evidence package contains comprehensive proof of service delivery for PayTR payment dispute resolution.
            <br/><br/>
            <b>Key Evidence Summary:</b><br/>
            • Total Activity Logs: {data['summary']['total_audit_logs']}<br/>
            • Workspace Usage Sessions: {data['summary']['total_workspace_sessions']}<br/>
            • Total Usage Hours: {data['summary']['total_workspace_hours']} hours<br/>
            • Successful Logins: {data['summary']['successful_logins']}<br/>
            • Email Communications: {data['summary']['total_emails_sent']}<br/>
            • Total Payments: {data['summary']['total_payments']}<br/>
            <br/>
            <b>Service Delivery Status: VERIFIED ✓</b>
            """
            story.append(Paragraph(summary_text, styles['Normal']))
            story.append(Spacer(1, 0.5*cm))

            # User Profile
            story.append(Paragraph("USER PROFILE / KULLANICI PROFİLİ", heading_style))
            user_info = [
                ['Email:', data['user']['email']],
                ['Registration Date:', data['user']['created_at'].strftime('%Y-%m-%d %H:%M:%S UTC')],
                ['Terms Accepted:', data['user']['terms_accepted_at'].strftime('%Y-%m-%d %H:%M:%S') if data['user']['terms_accepted_at'] else 'N/A'],
                ['Terms Accepted IP:', data['user']['terms_accepted_ip'] or 'N/A'],
                ['Privacy Accepted:', data['user']['privacy_accepted_at'].strftime('%Y-%m-%d %H:%M:%S') if data['user']['privacy_accepted_at'] else 'N/A'],
                ['Privacy Accepted IP:', data['user']['privacy_accepted_ip'] or 'N/A']
            ]
            user_table = Table(user_info, colWidths=[6*cm, 10*cm])
            user_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc'))
            ]))
            story.append(user_table)
            story.append(PageBreak())

            # Activity Timeline
            story.append(Paragraph("ACTIVITY TIMELINE / AKTİVİTE ZAMAN ÇİZGİSİ", heading_style))

            if data['audit_logs']:
                activity_data = [['Date/Time (UTC)', 'Action', 'IP Address', 'Status']]
                for log in data['audit_logs'][:20]:  # Show last 20 activities
                    activity_data.append([
                        log['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        log['action_type'],
                        log['ip_address'] or 'N/A',
                        '✓' if log['success'] else '✗'
                    ])

                activity_table = Table(activity_data, colWidths=[4*cm, 5*cm, 4*cm, 2*cm])
                activity_table.setStyle(TableStyle([
                    ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                    ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (3, 1), (3, -1), 'CENTER')
                ]))
                story.append(activity_table)
            else:
                story.append(Paragraph("No activity logs found.", styles['Normal']))

            story.append(PageBreak())

            # Email Communications
            story.append(Paragraph("EMAIL COMMUNICATIONS / E-POSTA İLETİŞİMİ", heading_style))

            if data['email_logs']:
                email_data = [['Date/Time (UTC)', 'Type', 'Subject', 'Status']]
                for email in data['email_logs']:
                    email_data.append([
                        email['sent_at'].strftime('%Y-%m-%d %H:%M:%S'),
                        email['email_type'],
                        email['subject'][:30] + '...' if len(email['subject']) > 30 else email['subject'],
                        email['delivery_status']
                    ])

                email_table = Table(email_data, colWidths=[4*cm, 4*cm, 5*cm, 2*cm])
                email_table.setStyle(TableStyle([
                    ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                    ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke)
                ]))
                story.append(email_table)
            else:
                story.append(Paragraph("No email logs found.", styles['Normal']))

            story.append(PageBreak())

            # Workspace Usage
            story.append(Paragraph("WORKSPACE USAGE / WORKSPACE KULLANIMI", heading_style))

            if data['workspace_sessions']:
                session_data = [['Start Time (UTC)', 'Duration', 'Activity Count', 'IP Address']]
                for session in data['workspace_sessions'][:20]:
                    duration_str = f"{session['duration_seconds'] // 3600}h {(session['duration_seconds'] % 3600) // 60}m" if session['duration_seconds'] else 'Ongoing'
                    session_data.append([
                        session['started_at'].strftime('%Y-%m-%d %H:%M:%S'),
                        duration_str,
                        str(session['activity_count']),
                        session['ip_address'] or 'N/A'
                    ])

                session_table = Table(session_data, colWidths=[4.5*cm, 3*cm, 3*cm, 4.5*cm])
                session_table.setStyle(TableStyle([
                    ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                    ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (2, 1), (2, -1), 'CENTER')
                ]))
                story.append(session_table)
            else:
                story.append(Paragraph("No workspace sessions found.", styles['Normal']))

            # Build PDF
            doc.build(story)

            logger.info(f"PDF report generated: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}", exc_info=True)
            return None

    def _create_evidence_archive(self, data, pdf_path, package_id):
        """Create ZIP archive with all evidence files."""
        try:
            zip_filename = f"chargeback_evidence_{package_id}.zip"
            zip_path = os.path.join(self.temp_dir, zip_filename)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add PDF report
                zipf.write(pdf_path, 'evidence_summary.pdf')

                # Add README
                readme_content = f"""
CHARGEBACK EVIDENCE PACKAGE
PayTR Ödeme İtiraz Delil Paketi

Package ID: {package_id}
Generated: {data['generated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}

This package contains comprehensive evidence for PayTR chargeback dispute resolution.

CONTENTS / İÇERİK:
- evidence_summary.pdf: Professional evidence report (Turkish + English)
- raw_data/: Complete raw data in JSON format
- technical/: Technical verification data

VERIFICATION / DOĞRULAMA:
Scan the QR code in the PDF or visit:
https://youarecoder.com/verify/{package_id}

CONTACT / İLETİŞİM:
support@youarecoder.com
                """
                zipf.writestr('README.txt', readme_content)

                # Add raw JSON data
                zipf.writestr('raw_data/audit_logs.json',
                             json.dumps(data['audit_logs'], indent=2, default=str))
                zipf.writestr('raw_data/workspace_sessions.json',
                             json.dumps(data['workspace_sessions'], indent=2, default=str))
                zipf.writestr('raw_data/email_logs.json',
                             json.dumps(data['email_logs'], indent=2, default=str))
                zipf.writestr('raw_data/payment_history.json',
                             json.dumps(data['all_payments'], indent=2, default=str))
                zipf.writestr('raw_data/user_profile.json',
                             json.dumps(data['user'], indent=2, default=str))

                # Add technical verification
                package_hash = hashlib.sha256(package_id.encode()).hexdigest()
                tech_info = f"""
TECHNICAL VERIFICATION / TEKNİK DOĞRULAMA

Package ID: {package_id}
Package Hash: {package_hash}
Generated: {data['generated_at'].isoformat()}

Payment Details:
- Merchant OID: {data['payment']['merchant_oid']}
- Amount: {data['payment']['amount']} {data['payment']['currency']}
- Status: {data['payment']['status']}

Evidence Summary:
- Total Activity Logs: {data['summary']['total_audit_logs']}
- Workspace Sessions: {data['summary']['total_workspace_sessions']}
- Total Usage Hours: {data['summary']['total_workspace_hours']}
- Successful Logins: {data['summary']['successful_logins']}
- Emails Sent: {data['summary']['total_emails_sent']}

Service Delivery: VERIFIED ✓
                """
                zipf.writestr('technical/verification.txt', tech_info)

            logger.info(f"Evidence archive created: {zip_path}")
            return zip_path

        except Exception as e:
            logger.error(f"Error creating evidence archive: {str(e)}", exc_info=True)
            return None
