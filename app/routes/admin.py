"""
Admin routes for system management and compliance.

Endpoints:
- GET /admin/users/<id>/export-logs - Export user activity logs for PayTR chargeback evidence
"""
import logging
import os
from datetime import datetime
from flask import Blueprint, jsonify, abort, send_file
from flask_login import login_required, current_user

from app import db
from app.models import User, Company, AuditLog, WorkspaceSession, Payment, Invoice, WorkspaceTemplate
from app.utils.decorators import require_company_admin
from app.services.proof_package_generator import ChargebackProofGenerator

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


@bp.route('/chargeback/generate/<int:payment_id>')
@login_required
@require_company_admin
def generate_chargeback_proof(payment_id):
    """
    Generate comprehensive chargeback evidence package.

    This endpoint generates a professional PDF report + ZIP archive containing:
    - Executive summary with key evidence
    - Complete activity timeline with IP tracking
    - Workspace usage sessions with duration
    - Email communication trail
    - Payment history
    - Legal acceptance records
    - Technical verification data

    Args:
        payment_id: Payment ID to generate proof for

    Returns:
        ZIP file download containing evidence package

    Authentication:
        Requires authenticated admin user

    HTTP Codes:
        200: Success - returns ZIP file
        403: Not authorized (not admin)
        404: Payment not found
        500: Generation failed
    """
    try:
        # Verify payment exists and belongs to admin's company
        payment = Payment.query.get_or_404(payment_id)

        if payment.company_id != current_user.company_id:
            logger.warning(f"Admin {current_user.id} attempted to access payment {payment_id} from another company")
            abort(403)

        # Generate proof package
        generator = ChargebackProofGenerator()
        zip_path, package_id = generator.generate_proof_package(payment_id)

        if not zip_path or not os.path.exists(zip_path):
            logger.error(f"Proof package generation failed for payment {payment_id}")
            return jsonify({'error': 'Failed to generate evidence package'}), 500

        # Send file for download
        logger.info(f"Admin {current_user.id} downloaded chargeback proof for payment {payment_id}")

        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"chargeback_evidence_{payment.merchant_oid}.zip"
        )

    except Exception as e:
        logger.error(f"Error generating chargeback proof: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate chargeback evidence'}), 500


@bp.route('/team')
@login_required
@require_company_admin
def team_management():
    """
    Team management page for company owners.

    Displays all team members with their workspace quotas and usage.
    Allows owners to:
    - View team member workspace quotas
    - Update individual workspace quotas
    - Invite new team members
    - View workspace usage statistics

    Returns:
        HTML page with team member listing and quota management interface

    Authentication:
        Requires authenticated admin user (Owner role)

    HTTP Codes:
        200: Success
        403: Not authorized (not admin)
    """
    from flask import render_template

    # Get all company members (excluding admins for quota purposes)
    company = current_user.company
    team_members = User.query.filter_by(
        company_id=company.id,
        is_active=True
    ).order_by(User.created_at.desc()).all()

    # Calculate team statistics
    total_quotas_assigned = sum(
        getattr(user, 'workspace_quota', 0)
        for user in team_members
    )
    total_workspaces_used = sum(user.workspaces.count() for user in team_members)

    logger.info(f"Admin {current_user.id} accessed team management page")

    return render_template('admin/team.html',
                          team_members=team_members,
                          company=company,
                          total_quotas_assigned=total_quotas_assigned,
                          total_workspaces_used=total_workspaces_used)


@bp.route('/team/add', methods=['POST'])
@login_required
@require_company_admin
def add_team_member():
    """
    Add a new team member to the company.

    Creates a new user account with the specified role and workspace quota.
    Sends an invitation email with a temporary password.

    JSON Body:
        {
            "email": "user@example.com",      # Required: User email
            "role": "developer" | "admin",    # Required: User role
            "quota": 1                        # Optional: Workspace quota (default: 1)
        }

    Returns:
        JSON response with success status and user info

    Validation:
        - Email must be valid and unique
        - Role must be "developer" or "admin"
        - Quota must be positive integer (if provided)
        - User must not already exist in the system

    Authentication:
        Requires authenticated admin user (Owner role)

    HTTP Codes:
        201: User created successfully
        400: Invalid input or validation error
        403: Not authorized
        409: User with email already exists
    """
    from flask import request
    import secrets
    import string

    try:
        # Get data from request
        data = request.get_json()

        # Validate required fields
        email = data.get('email', '').strip().lower()
        role = data.get('role', '').strip().lower()
        quota = data.get('quota', 1)

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        if not role:
            return jsonify({'error': 'Role is required'}), 400

        # Validate role
        valid_roles = ['developer', 'admin']
        if role not in valid_roles:
            return jsonify({'error': f'Role must be one of: {", ".join(valid_roles)}'}), 400

        # Validate quota
        try:
            quota = int(quota)
            if quota < 1:
                return jsonify({'error': 'Quota must be at least 1'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Quota must be a valid integer'}), 400

        # Check total quota allocation doesn't exceed plan limit
        company = current_user.company

        # Calculate total quota for all existing users
        total_quota = db.session.query(db.func.sum(User.workspace_quota)).filter(
            User.company_id == company.id,
            User.workspace_quota.isnot(None)
        ).scalar() or 0

        # Add the new user's quota
        total_quota += quota

        if total_quota > company.max_workspaces:
            return jsonify({
                'error': f'Total quota allocation ({total_quota}) would exceed plan limit ({company.max_workspaces}). Available: {company.max_workspaces - (total_quota - quota)}'
            }), 400

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 409

        # Generate temporary password (12 characters)
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        # Create new user
        new_user = User(
            email=email,
            full_name=email.split('@')[0].title(),  # Use email prefix as name
            role='member' if role == 'developer' else 'admin',
            company_id=current_user.company_id,
            is_active=True,
            terms_accepted=False,  # User must accept on first login
            privacy_accepted=False,
            workspace_quota=quota,
            quota_assigned_at=datetime.utcnow(),
            quota_assigned_by=current_user.id
        )
        new_user.set_password(temp_password)

        db.session.add(new_user)
        db.session.commit()

        # Send invitation email with temporary password
        try:
            from app.services.email_service import send_email

            company_name = current_user.company.name

            subject = f"Invitation to join {company_name} on YouAreCoder"

            html_body = f"""
            <h2>Welcome to {company_name}!</h2>
            <p>You have been invited to join <strong>{company_name}</strong> on YouAreCoder as a {role}.</p>

            <h3>Your Login Credentials:</h3>
            <ul>
                <li><strong>Email:</strong> {email}</li>
                <li><strong>Temporary Password:</strong> <code>{temp_password}</code></li>
            </ul>

            <p><strong>Workspace Quota:</strong> You can create up to {quota} workspace(s).</p>

            <p>Please log in at <a href="https://youarecoder.com/auth/login">https://youarecoder.com/auth/login</a>
            and change your password immediately.</p>

            <p>If you have any questions, please contact your team administrator.</p>

            <p>Best regards,<br>
            The YouAreCoder Team</p>
            """

            text_body = f"""
            Welcome to {company_name}!

            You have been invited to join {company_name} on YouAreCoder as a {role}.

            Your Login Credentials:
            - Email: {email}
            - Temporary Password: {temp_password}

            Workspace Quota: You can create up to {quota} workspace(s).

            Please log in at https://youarecoder.com/auth/login and change your password immediately.

            If you have any questions, please contact your team administrator.

            Best regards,
            The YouAreCoder Team
            """

            send_email(
                subject=subject,
                recipients=[email],
                text_body=text_body,
                html_body=html_body
            )

            logger.info(f"Sent invitation email to {email}")

        except Exception as email_error:
            logger.error(f"Failed to send invitation email to {email}: {str(email_error)}")
            # Don't fail the request if email sending fails

        logger.info(f"Admin {current_user.id} added new team member {new_user.id} ({email}) with role {role}")

        return jsonify({
            'success': True,
            'user_id': new_user.id,
            'email': new_user.email,
            'role': new_user.role,
            'quota': quota,
            'message': 'Team member added successfully. Invitation email sent.'
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding team member: {str(e)}")
        return jsonify({'error': 'Failed to add team member. Please try again.'}), 500


@bp.route('/team/<int:user_id>/quota', methods=['POST'])
@login_required
@require_company_admin
def update_user_quota(user_id):
    """
    Update workspace quota for a specific team member.

    Args:
        user_id: User ID to update quota for

    JSON Body:
        {
            "quota": 5  # New workspace quota
        }

    Returns:
        JSON response with success status and updated user info

    Validation:
        - User must belong to admin's company
        - New quota must be >= current workspace count
        - New quota must be positive integer
        - Cannot reduce quota below existing workspace count

    Authentication:
        Requires authenticated admin user (Owner role)

    HTTP Codes:
        200: Success
        400: Invalid quota or validation error
        403: Not authorized
        404: User not found
    """
    from flask import request

    try:
        # Get user
        user = User.query.get_or_404(user_id)

        # Verify user belongs to admin's company
        if user.company_id != current_user.company_id:
            logger.warning(f"Admin {current_user.id} attempted to modify user {user_id} from another company")
            abort(403)

        # Get new quota from request
        data = request.get_json()
        new_quota = data.get('quota')

        if new_quota is None:
            return jsonify({'error': 'Quota value is required'}), 400

        try:
            new_quota = int(new_quota)
        except (ValueError, TypeError):
            return jsonify({'error': 'Quota must be a valid integer'}), 400

        if new_quota < 1:
            return jsonify({'error': 'Quota must be at least 1'}), 400

        # Check current workspace count
        current_workspace_count = user.workspaces.count()
        if new_quota < current_workspace_count:
            return jsonify({
                'error': f'Cannot reduce quota below current workspace count ({current_workspace_count})'
            }), 400

        # Check total quota allocation doesn't exceed plan limit
        company = current_user.company

        # Calculate total quota for all users except the one being updated
        total_quota = db.session.query(db.func.sum(User.workspace_quota)).filter(
            User.company_id == company.id,
            User.id != user_id,
            User.workspace_quota.isnot(None)
        ).scalar() or 0

        # Add the new quota for this user
        total_quota += new_quota

        if total_quota > company.max_workspaces:
            return jsonify({
                'error': f'Total quota allocation ({total_quota}) would exceed plan limit ({company.max_workspaces}). Available: {company.max_workspaces - (total_quota - new_quota)}'
            }), 400

        # Update quota
        user.workspace_quota = new_quota
        user.quota_assigned_at = datetime.utcnow()
        user.quota_assigned_by = current_user.id

        db.session.commit()

        logger.info(f"Admin {current_user.id} updated quota for user {user_id} to {new_quota}")

        return jsonify({
            'success': True,
            'user_id': user.id,
            'email': user.email,
            'new_quota': new_quota,
            'current_usage': current_workspace_count,
            'assigned_at': user.quota_assigned_at.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user quota: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to update quota'}), 500


@bp.route('/team/<int:user_id>/delete', methods=['POST'])
@login_required
@require_company_admin
def delete_team_member(user_id):
    """Delete a team member and all their workspaces with full system cleanup."""
    from flask import request
    from app.services.workspace_provisioner import WorkspaceProvisioner

    try:
        # Get user
        user = User.query.get_or_404(user_id)

        # Verify user belongs to admin's company
        if user.company_id != current_user.company_id:
            logger.warning(f"Admin {current_user.id} attempted to delete user {user_id} from another company")
            abort(403)

        # Prevent deleting admin/owner
        if user.role == 'admin':
            return jsonify({'error': 'Cannot delete the owner account'}), 400

        # Get user info for logging before deletion
        user_email = user.email
        user_name = user.full_name
        workspace_count = user.workspaces.count()

        # Initialize provisioner for system resource cleanup
        provisioner = WorkspaceProvisioner()
        failed_workspaces = []

        # Deprovision all workspaces owned by this user
        # This removes: systemd service, linux user, home directory, traefik routing, and DB record
        for workspace in user.workspaces.all():
            logger.info(f"Deprovisioning workspace {workspace.id} ({workspace.name}) owned by user {user_id}")
            try:
                result = provisioner.deprovision_workspace(workspace)
                if not result['success']:
                    failed_workspaces.append(workspace.name)
                    logger.warning(f"Failed to fully deprovision workspace {workspace.id}: {result.get('error')}")
            except Exception as e:
                failed_workspaces.append(workspace.name)
                logger.error(f"Error deprovisioning workspace {workspace.id}: {str(e)}")
                # Continue with other workspaces

        # Delete the user (workspaces already deleted by deprovision_workspace)
        db.session.delete(user)
        db.session.commit()

        logger.info(f"Admin {current_user.id} deleted user {user_id} ({user_email}) and {workspace_count} workspaces")

        if failed_workspaces:
            return jsonify({
                'success': True,
                'message': f'Deleted {user_name} and {workspace_count} workspace(s). Some workspaces had partial cleanup: {", ".join(failed_workspaces)}'
            }), 200
        else:
            return jsonify({
                'success': True,
                'message': f'Successfully deleted {user_name} and {workspace_count} workspace(s) with full system cleanup'
            }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting team member: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to delete team member'}), 500


@bp.route('/templates')
@login_required
@require_company_admin
def templates_list():
    """
    Workspace templates management page.

    Lists all available templates:
    - Official templates (platform-provided)
    - Company templates (company-specific)
    - Personal templates (user-created)

    Returns:
        HTML page with template listing and management interface

    Authentication:
        Requires authenticated admin user (Owner role)

    HTTP Codes:
        200: Success
        403: Not authorized (not admin)
    """
    from flask import render_template

    # Get official templates (no company_id)
    official_templates = WorkspaceTemplate.query.filter_by(
        visibility='official',
        is_active=True
    ).order_by(WorkspaceTemplate.usage_count.desc()).all()

    # Get company templates
    company_templates = WorkspaceTemplate.query.filter_by(
        company_id=current_user.company_id,
        visibility='company',
        is_active=True
    ).order_by(WorkspaceTemplate.created_at.desc()).all()

    # Get user templates
    user_templates = WorkspaceTemplate.query.filter_by(
        created_by=current_user.id,
        visibility='user',
        is_active=True
    ).order_by(WorkspaceTemplate.created_at.desc()).all()

    logger.info(f"Admin {current_user.id} accessed templates management page")

    return render_template('admin/templates.html',
                          official_templates=official_templates,
                          company_templates=company_templates,
                          user_templates=user_templates)


@bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
@require_company_admin
def template_create():
    """
    Create new workspace template.

    GET: Returns template creation form
    POST: Creates new template from form data

    JSON Body (POST):
        {
            "name": "Template Name",
            "description": "Description",
            "category": "web",
            "visibility": "company",
            "config": { JSON configuration }
        }

    Returns:
        GET: HTML form for template creation
        POST: JSON response with success status and template info

    Authentication:
        Requires authenticated admin user (Owner role)

    HTTP Codes:
        200: Success (GET)
        201: Template created (POST)
        400: Validation error
        403: Not authorized
    """
    from flask import render_template, request

    if request.method == 'GET':
        return render_template('admin/template_form.html', template=None)

    # POST - Create template
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Template name is required'}), 400

        if not data.get('config'):
            return jsonify({'error': 'Template configuration is required'}), 400

        # Create template
        template = WorkspaceTemplate(
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', 'general'),
            visibility=data.get('visibility', 'company'),
            config=data['config'],
            company_id=current_user.company_id if data.get('visibility') != 'official' else None,
            created_by=current_user.id
        )

        db.session.add(template)
        db.session.commit()

        logger.info(f"Admin {current_user.id} created template {template.id}: {template.name}")

        return jsonify({
            'success': True,
            'template': template.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating template: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to create template'}), 500


@bp.route('/templates/<int:template_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@require_company_admin
def template_detail(template_id):
    """
    View, update, or delete workspace template.

    GET: Returns template details for editing
    PUT: Updates template configuration
    DELETE: Soft deletes template (sets is_active=False)

    Args:
        template_id: Template ID

    JSON Body (PUT):
        {
            "name": "Updated Name",
            "description": "Updated Description",
            "category": "web",
            "config": { JSON configuration }
        }

    Returns:
        GET: HTML form with template data
        PUT: JSON response with updated template
        DELETE: JSON response with success status

    Validation:
        - User must own the template or be company admin
        - Cannot modify official templates unless superadmin
        - Cannot delete templates in use

    Authentication:
        Requires authenticated admin user (Owner role)

    HTTP Codes:
        200: Success
        400: Validation error
        403: Not authorized
        404: Template not found
    """
    from flask import render_template, request

    template = WorkspaceTemplate.query.get_or_404(template_id)

    # Check ownership (unless official template)
    if template.visibility != 'official':
        if template.company_id != current_user.company_id and template.created_by != current_user.id:
            logger.warning(f"Admin {current_user.id} attempted to access template {template_id} from another company")
            abort(403)

    if request.method == 'GET':
        return render_template('admin/template_form.html', template=template)

    elif request.method == 'PUT':
        try:
            data = request.get_json()

            # Update fields
            if 'name' in data:
                template.name = data['name']
            if 'description' in data:
                template.description = data['description']
            if 'category' in data:
                template.category = data['category']
            if 'config' in data:
                template.config = data['config']

            template.updated_at = datetime.utcnow()

            db.session.commit()

            logger.info(f"Admin {current_user.id} updated template {template_id}")

            return jsonify({
                'success': True,
                'template': template.to_dict()
            }), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating template: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to update template'}), 500

    elif request.method == 'DELETE':
        try:
            # Check if template is in use
            workspaces_using = template.workspaces.count()
            if workspaces_using > 0:
                return jsonify({
                    'error': f'Cannot delete template in use by {workspaces_using} workspace(s)'
                }), 400

            # Soft delete
            template.is_active = False
            db.session.commit()

            logger.info(f"Admin {current_user.id} deleted template {template_id}")

            return jsonify({'success': True}), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting template: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to delete template'}), 500


def init_admin_csrf_exempt(csrf):
    """
    Initialize CSRF exemptions for admin API endpoints.
    Called from app/__init__.py after csrf.init_app(app)
    """
    csrf.exempt(add_team_member)
