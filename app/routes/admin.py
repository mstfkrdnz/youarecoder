"""
Admin routes for system management and compliance.

Endpoints:
- GET /admin/users/<id>/export-logs - Export user activity logs for PayTR chargeback evidence
"""
import logging
from datetime import datetime
from flask import Blueprint, jsonify, abort
from flask_login import login_required, current_user

from app import db
from app.models import User, Company, AuditLog, WorkspaceSession, Payment, Invoice
from app.utils.decorators import require_company_admin

logger = logging.getLogger(__name__)

# Create admin blueprint
bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/users/<int:user_id>/export-logs')
@login_required
@require_company_admin
def export_user_logs(user_id):
    """
    Export comprehensive user activity logs for PayTR chargeback evidence.

    This endpoint provides a complete audit trail combining:
    - Audit logs (login, workspace access, payments)
    - Workspace sessions (usage duration, activity)
    - Payment history with status
    - Invoice records
    - Terms and privacy acceptance with IP tracking

    Args:
        user_id: User ID to export logs for

    Returns:
        JSON response with comprehensive activity data:
        {
            'user': {user info},
            'company': {company info},
            'legal_acceptance': {terms/privacy with IP and timestamp},
            'audit_logs': [{log entries}],
            'workspace_sessions': [{session data}],
            'payments': [{payment records}],
            'invoices': [{invoice records}],
            'summary': {aggregate stats}
        }

    Authentication:
        Requires authenticated admin user

    HTTP Codes:
        200: Success
        403: Not authorized (not admin)
        404: User not found
    """
    try:
        # Get user and company
        user = User.query.get_or_404(user_id)
        company = user.company

        # Get all audit logs for user
        audit_logs = AuditLog.query.filter_by(user_id=user_id)\
            .order_by(AuditLog.timestamp.desc())\
            .all()

        # Get all workspace sessions for user
        workspace_sessions = WorkspaceSession.query.filter_by(user_id=user_id)\
            .order_by(WorkspaceSession.started_at.desc())\
            .all()

        # Get all payments for company
        payments = Payment.query.filter_by(company_id=company.id)\
            .order_by(Payment.created_at.desc())\
            .all()

        # Get all invoices for company
        invoices = Invoice.query.filter_by(company_id=company.id)\
            .order_by(Invoice.created_at.desc())\
            .all()

        # Calculate summary statistics
        total_workspace_hours = sum(
            (session.duration_seconds or 0) / 3600
            for session in workspace_sessions
        )
        total_payments = sum(payment.amount for payment in payments if payment.status == 'completed')
        login_count = sum(1 for log in audit_logs if log.action_type == 'login' and log.success)

        # Build export data
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'export_purpose': 'PayTR chargeback evidence / compliance audit',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at.isoformat(),
                'is_active': user.is_active
            },
            'company': {
                'id': company.id,
                'name': company.name,
                'subdomain': company.subdomain,
                'plan': company.plan,
                'max_workspaces': company.max_workspaces,
                'created_at': company.created_at.isoformat()
            },
            'legal_acceptance': {
                'terms_accepted': user.terms_accepted,
                'terms_accepted_at': user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
                'terms_accepted_ip': user.terms_accepted_ip,
                'terms_version': user.terms_version,
                'privacy_accepted': user.privacy_accepted,
                'privacy_accepted_at': user.privacy_accepted_at.isoformat() if user.privacy_accepted_at else None,
                'privacy_accepted_ip': user.privacy_accepted_ip,
                'privacy_version': user.privacy_version
            },
            'audit_logs': [
                {
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'action_type': log.action_type,
                    'resource_type': log.resource_type,
                    'resource_id': log.resource_id,
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent,
                    'request_method': log.request_method,
                    'request_path': log.request_path,
                    'details': log.details,
                    'success': log.success,
                    'error_message': log.error_message
                }
                for log in audit_logs
            ],
            'workspace_sessions': [
                {
                    'id': session.id,
                    'workspace_id': session.workspace_id,
                    'started_at': session.started_at.isoformat(),
                    'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                    'duration_seconds': session.duration_seconds,
                    'duration_hours': round(session.duration_seconds / 3600, 2) if session.duration_seconds else None,
                    'activity_count': session.activity_count,
                    'ip_address': session.ip_address,
                    'user_agent': session.user_agent,
                    'access_method': session.access_method
                }
                for session in workspace_sessions
            ],
            'payments': [
                {
                    'id': payment.id,
                    'merchant_oid': payment.merchant_oid,
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'status': payment.status,
                    'plan': payment.plan,
                    'created_at': payment.created_at.isoformat(),
                    'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                    'payment_type': payment.payment_type,
                    'failed_reason': payment.failed_reason
                }
                for payment in payments
            ],
            'invoices': [
                {
                    'id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'amount': float(invoice.amount),
                    'status': invoice.status,
                    'created_at': invoice.created_at.isoformat(),
                    'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
                    'paid_at': invoice.paid_at.isoformat() if invoice.paid_at else None
                }
                for invoice in invoices
            ],
            'summary': {
                'total_audit_logs': len(audit_logs),
                'total_workspace_sessions': len(workspace_sessions),
                'total_workspace_hours': round(total_workspace_hours, 2),
                'total_payments_count': len(payments),
                'total_payments_amount': float(total_payments),
                'total_invoices': len(invoices),
                'successful_login_count': login_count,
                'first_activity': audit_logs[-1].timestamp.isoformat() if audit_logs else None,
                'last_activity': audit_logs[0].timestamp.isoformat() if audit_logs else None
            }
        }

        logger.info(f"Admin {current_user.id} exported logs for user {user_id}")

        return jsonify(export_data), 200

    except Exception as e:
        logger.error(f"Error exporting user logs: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to export user logs'}), 500
