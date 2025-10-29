"""
Metrics API endpoints for workspace resource usage monitoring.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import Workspace, WorkspaceMetrics
from app.decorators import admin_required


bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


@bp.route('/workspaces/<int:workspace_id>', methods=['GET'])
@login_required
def get_workspace_metrics(workspace_id):
    """
    Get time-series metrics for a specific workspace.

    Query Parameters:
        start_date: ISO format datetime (default: 24 hours ago)
        end_date: ISO format datetime (default: now)
        limit: Maximum number of records (default: 1000)

    Returns:
        JSON with workspace metrics data
    """
    # Check workspace access
    workspace = Workspace.query.get_or_404(workspace_id)

    if not current_user.is_admin and workspace.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403

    # Parse query parameters
    try:
        end_date = request.args.get('end_date')
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_date = datetime.utcnow()

        start_date = request.args.get('start_date')
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_date = end_date - timedelta(hours=24)

        limit = int(request.args.get('limit', 1000))
        limit = min(limit, 10000)  # Cap at 10k records

    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400

    # Query metrics
    metrics = WorkspaceMetrics.query.filter(
        WorkspaceMetrics.workspace_id == workspace_id,
        WorkspaceMetrics.collected_at >= start_date,
        WorkspaceMetrics.collected_at <= end_date
    ).order_by(
        WorkspaceMetrics.collected_at.asc()
    ).limit(limit).all()

    return jsonify({
        'workspace_id': workspace_id,
        'workspace_name': workspace.name,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'metrics_count': len(metrics),
        'metrics': [m.to_dict() for m in metrics]
    })


@bp.route('/workspaces/<int:workspace_id>/current', methods=['GET'])
@login_required
def get_current_metrics(workspace_id):
    """
    Get the most recent metrics snapshot for a workspace.

    Returns:
        JSON with latest metrics data
    """
    # Check workspace access
    workspace = Workspace.query.get_or_404(workspace_id)

    if not current_user.is_admin and workspace.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403

    # Get latest metrics
    latest_metrics = WorkspaceMetrics.query.filter(
        WorkspaceMetrics.workspace_id == workspace_id
    ).order_by(
        WorkspaceMetrics.collected_at.desc()
    ).first()

    if not latest_metrics:
        return jsonify({
            'workspace_id': workspace_id,
            'workspace_name': workspace.name,
            'metrics': None,
            'message': 'No metrics data available'
        })

    return jsonify({
        'workspace_id': workspace_id,
        'workspace_name': workspace.name,
        'metrics': latest_metrics.to_dict()
    })


@bp.route('/workspaces/<int:workspace_id>/summary', methods=['GET'])
@login_required
def get_metrics_summary(workspace_id):
    """
    Get aggregated metrics summary for a workspace.

    Query Parameters:
        period: Time period (1h, 6h, 24h, 7d, 30d) (default: 24h)

    Returns:
        JSON with aggregated statistics
    """
    # Check workspace access
    workspace = Workspace.query.get_or_404(workspace_id)

    if not current_user.is_admin and workspace.company_id != current_user.company_id:
        return jsonify({'error': 'Access denied'}), 403

    # Parse period
    period = request.args.get('period', '24h')
    period_hours = {
        '1h': 1,
        '6h': 6,
        '24h': 24,
        '7d': 24 * 7,
        '30d': 24 * 30
    }.get(period, 24)

    start_date = datetime.utcnow() - timedelta(hours=period_hours)

    # Query aggregated metrics
    stats = db.session.query(
        func.avg(WorkspaceMetrics.cpu_percent).label('avg_cpu'),
        func.max(WorkspaceMetrics.cpu_percent).label('max_cpu'),
        func.min(WorkspaceMetrics.cpu_percent).label('min_cpu'),
        func.avg(WorkspaceMetrics.memory_used_mb).label('avg_memory_mb'),
        func.max(WorkspaceMetrics.memory_used_mb).label('max_memory_mb'),
        func.min(WorkspaceMetrics.memory_used_mb).label('min_memory_mb'),
        func.avg(WorkspaceMetrics.memory_percent).label('avg_memory_percent'),
        func.max(WorkspaceMetrics.memory_percent).label('max_memory_percent'),
        func.count(WorkspaceMetrics.id).label('data_points')
    ).filter(
        WorkspaceMetrics.workspace_id == workspace_id,
        WorkspaceMetrics.collected_at >= start_date
    ).first()

    if not stats or stats.data_points == 0:
        return jsonify({
            'workspace_id': workspace_id,
            'workspace_name': workspace.name,
            'period': period,
            'summary': None,
            'message': 'No metrics data available for this period'
        })

    return jsonify({
        'workspace_id': workspace_id,
        'workspace_name': workspace.name,
        'period': period,
        'start_date': start_date.isoformat(),
        'end_date': datetime.utcnow().isoformat(),
        'summary': {
            'cpu': {
                'avg': round(float(stats.avg_cpu), 2) if stats.avg_cpu else 0,
                'max': round(float(stats.max_cpu), 2) if stats.max_cpu else 0,
                'min': round(float(stats.min_cpu), 2) if stats.min_cpu else 0
            },
            'memory': {
                'avg_mb': int(stats.avg_memory_mb) if stats.avg_memory_mb else 0,
                'max_mb': int(stats.max_memory_mb) if stats.max_memory_mb else 0,
                'min_mb': int(stats.min_memory_mb) if stats.min_memory_mb else 0,
                'avg_percent': round(float(stats.avg_memory_percent), 2) if stats.avg_memory_percent else 0,
                'max_percent': round(float(stats.max_memory_percent), 2) if stats.max_memory_percent else 0
            },
            'data_points': stats.data_points
        }
    })


@bp.route('/overview', methods=['GET'])
@admin_required
def get_metrics_overview():
    """
    Get metrics overview for all workspaces (admin only).

    Returns:
        JSON with system-wide metrics summary
    """
    # Get latest metrics for all workspaces
    subquery = db.session.query(
        WorkspaceMetrics.workspace_id,
        func.max(WorkspaceMetrics.collected_at).label('latest_collected_at')
    ).group_by(
        WorkspaceMetrics.workspace_id
    ).subquery()

    latest_metrics = db.session.query(
        WorkspaceMetrics,
        Workspace
    ).join(
        Workspace, WorkspaceMetrics.workspace_id == Workspace.id
    ).join(
        subquery,
        (WorkspaceMetrics.workspace_id == subquery.c.workspace_id) &
        (WorkspaceMetrics.collected_at == subquery.c.latest_collected_at)
    ).all()

    workspaces_data = []
    for metrics, workspace in latest_metrics:
        workspaces_data.append({
            'workspace_id': workspace.id,
            'workspace_name': workspace.name,
            'company_id': workspace.company_id,
            'is_running': workspace.is_running,
            'metrics': metrics.to_dict()
        })

    # Calculate system-wide aggregates
    total_cpu = sum(w['metrics']['cpu_percent'] for w in workspaces_data)
    total_memory_mb = sum(w['metrics']['memory_used_mb'] for w in workspaces_data)
    avg_cpu = total_cpu / len(workspaces_data) if workspaces_data else 0
    avg_memory_mb = total_memory_mb / len(workspaces_data) if workspaces_data else 0

    return jsonify({
        'workspaces_count': len(workspaces_data),
        'system_summary': {
            'total_cpu_percent': round(total_cpu, 2),
            'total_memory_mb': total_memory_mb,
            'avg_cpu_percent': round(avg_cpu, 2),
            'avg_memory_mb': int(avg_memory_mb)
        },
        'workspaces': workspaces_data
    })
