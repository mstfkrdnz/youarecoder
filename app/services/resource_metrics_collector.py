"""
Resource Metrics Collector Service for Workspace Monitoring.

Collects CPU and memory usage metrics for running workspaces using Linux
system tools (ps, systemctl) and stores time-series data in the database.
"""
import subprocess
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from flask import current_app
from app import db
from app.models import Workspace, WorkspaceMetrics


class ResourceMetricsCollectorError(Exception):
    """Exception raised for metrics collection errors."""
    pass


class ResourceMetricsCollector:
    """
    Service for collecting resource usage metrics from running workspaces.

    Collects CPU, memory, process count, and uptime metrics for workspaces
    that are currently running (is_running=True).
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_process_metrics(self, linux_username: str) -> Optional[Dict]:
        """
        Get CPU and memory metrics for all processes owned by the user.

        Args:
            linux_username: Linux username of the workspace

        Returns:
            dict with cpu_percent, memory_mb, process_count, or None if error
        """
        try:
            # Get all processes for the user
            # ps aux output: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.logger.error(f"ps command failed: {result.stderr}")
                return None

            # Parse ps output and filter by username
            total_cpu = 0.0
            total_memory_kb = 0
            process_count = 0

            for line in result.stdout.splitlines():
                # Skip header line
                if line.startswith('USER'):
                    continue

                # Check if line starts with the username
                if line.startswith(linux_username):
                    parts = line.split()
                    if len(parts) >= 6:
                        try:
                            cpu_percent = float(parts[2])
                            rss_kb = int(parts[5])  # RSS in KB

                            total_cpu += cpu_percent
                            total_memory_kb += rss_kb
                            process_count += 1
                        except (ValueError, IndexError) as e:
                            self.logger.warning(f"Failed to parse ps line: {line} - {e}")
                            continue

            if process_count == 0:
                # No processes found for user
                return {
                    'cpu_percent': 0.0,
                    'memory_mb': 0,
                    'process_count': 0
                }

            # Convert memory from KB to MB
            memory_mb = int(total_memory_kb / 1024)

            return {
                'cpu_percent': round(total_cpu, 2),
                'memory_mb': memory_mb,
                'process_count': process_count
            }

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout getting process metrics for {linux_username}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting process metrics for {linux_username}: {e}")
            return None

    def get_systemd_service_metrics(self, service_name: str) -> Optional[Dict]:
        """
        Get uptime and status from systemd service.

        Args:
            service_name: Name of the systemd service (e.g., code-server-devuser1)

        Returns:
            dict with uptime_seconds, is_active, or None if error
        """
        try:
            # Get service properties
            result = subprocess.run(
                ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp,ActiveState'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.logger.warning(f"systemctl show failed for {service_name}: {result.stderr}")
                return None

            # Parse output
            # Format: ActiveEnterTimestamp=Wed 2025-10-29 10:00:00 UTC
            #         ActiveState=active
            active_timestamp = None
            is_active = False

            for line in result.stdout.splitlines():
                if line.startswith('ActiveEnterTimestamp='):
                    timestamp_str = line.split('=', 1)[1]
                    if timestamp_str and timestamp_str != 'n/a':
                        try:
                            # Parse systemd timestamp format
                            active_timestamp = datetime.strptime(
                                timestamp_str.strip(),
                                '%a %Y-%m-%d %H:%M:%S %Z'
                            )
                        except ValueError as e:
                            self.logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")

                elif line.startswith('ActiveState='):
                    state = line.split('=', 1)[1].strip()
                    is_active = (state == 'active')

            if not is_active:
                return None

            if not active_timestamp:
                # Service is active but no start timestamp
                return {
                    'uptime_seconds': 0,
                    'is_active': True
                }

            # Calculate uptime
            uptime = datetime.utcnow() - active_timestamp
            uptime_seconds = int(uptime.total_seconds())

            return {
                'uptime_seconds': uptime_seconds,
                'is_active': True
            }

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout getting systemd metrics for {service_name}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting systemd metrics for {service_name}: {e}")
            return None

    def collect_workspace_metrics(self, workspace: Workspace) -> Optional[WorkspaceMetrics]:
        """
        Collect complete metrics for a single workspace.

        Args:
            workspace: Workspace model instance

        Returns:
            WorkspaceMetrics instance or None if collection failed
        """
        try:
            # Get process metrics
            process_metrics = self.get_process_metrics(workspace.linux_username)
            if process_metrics is None:
                self.logger.warning(f"Failed to get process metrics for workspace {workspace.id}")
                return None

            # Get systemd service metrics
            service_name = f"code-server-{workspace.linux_username}"
            systemd_metrics = self.get_systemd_service_metrics(service_name)
            if systemd_metrics is None:
                self.logger.warning(f"Failed to get systemd metrics for workspace {workspace.id}")
                # Use default uptime
                systemd_metrics = {'uptime_seconds': 0, 'is_active': False}

            # Calculate memory percentage relative to workspace limit
            memory_limit_mb = workspace.memory_limit_mb or 2048
            memory_percent = (process_metrics['memory_mb'] / memory_limit_mb) * 100

            # Create metrics record
            metrics = WorkspaceMetrics(
                workspace_id=workspace.id,
                collected_at=datetime.utcnow(),
                cpu_percent=process_metrics['cpu_percent'],
                memory_used_mb=process_metrics['memory_mb'],
                memory_percent=min(memory_percent, 100.0),  # Cap at 100%
                process_count=process_metrics['process_count'],
                uptime_seconds=systemd_metrics['uptime_seconds']
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting metrics for workspace {workspace.id}: {e}")
            return None

    def collect_all_running_workspaces(self) -> Dict:
        """
        Collect metrics for all running workspaces and store in database.

        Returns:
            dict: Summary of collection results
        """
        summary = {
            'checked': 0,
            'collected': 0,
            'errors': 0,
            'workspace_ids_collected': [],
            'errors_detail': []
        }

        try:
            # Get all running workspaces
            workspaces = Workspace.query.filter(
                Workspace.is_running == True
            ).all()

            summary['checked'] = len(workspaces)
            self.logger.info(f"Collecting metrics for {len(workspaces)} running workspaces")

            for workspace in workspaces:
                try:
                    # Collect metrics
                    metrics = self.collect_workspace_metrics(workspace)

                    if metrics:
                        # Store in database
                        db.session.add(metrics)
                        summary['collected'] += 1
                        summary['workspace_ids_collected'].append(workspace.id)

                        self.logger.info(
                            f"Collected metrics for workspace {workspace.id} ({workspace.name}): "
                            f"CPU={metrics.cpu_percent}%, Memory={metrics.memory_used_mb}MB "
                            f"({metrics.memory_percent:.1f}%), Processes={metrics.process_count}"
                        )
                    else:
                        summary['errors'] += 1
                        error_detail = {
                            'workspace_id': workspace.id,
                            'workspace_name': workspace.name,
                            'error': 'Failed to collect metrics'
                        }
                        summary['errors_detail'].append(error_detail)

                except Exception as e:
                    summary['errors'] += 1
                    error_detail = {
                        'workspace_id': workspace.id,
                        'workspace_name': workspace.name,
                        'error': str(e)
                    }
                    summary['errors_detail'].append(error_detail)
                    self.logger.error(f"Error collecting metrics for workspace {workspace.id}: {e}")

            # Commit all collected metrics
            db.session.commit()

            return summary

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Metrics collection failed: {str(e)}", exc_info=True)
            summary['errors'] += 1
            summary['errors_detail'].append({'error': str(e)})
            return summary

    def cleanup_old_metrics(self, retention_days: int = 30) -> int:
        """
        Delete metrics older than retention_days.

        Args:
            retention_days: Number of days to retain metrics

        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            deleted = WorkspaceMetrics.query.filter(
                WorkspaceMetrics.collected_at < cutoff_date
            ).delete()

            db.session.commit()

            self.logger.info(f"Deleted {deleted} metrics records older than {retention_days} days")
            return deleted

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error cleaning up old metrics: {e}")
            return 0
