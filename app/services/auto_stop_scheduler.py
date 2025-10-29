"""
Auto-Stop Scheduler Service for Workspace Lifecycle Management.

Automatically stops workspaces that have exceeded their auto_stop_hours threshold
based on last_accessed_at timestamp.
"""
import logging
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import Workspace
from app.services.workspace_provisioner import WorkspaceProvisioner, WorkspaceProvisionerError


class AutoStopScheduler:
    """
    Service for automatically stopping idle workspaces.

    This scheduler should be run periodically (e.g., every 15 minutes) via cron
    or systemd timer to check for workspaces that need to be stopped.
    """

    def __init__(self):
        self.provisioner = WorkspaceProvisioner()
        self.logger = logging.getLogger(__name__)

    def check_and_stop_idle_workspaces(self) -> dict:
        """
        Check all running workspaces and stop those that have exceeded auto-stop threshold.

        Returns:
            dict: Summary of operations performed
        """
        summary = {
            'checked': 0,
            'stopped': 0,
            'errors': 0,
            'skipped': 0,
            'workspace_ids_stopped': [],
            'errors_detail': []
        }

        try:
            # Get all running workspaces with auto_stop_hours > 0
            workspaces = Workspace.query.filter(
                Workspace.is_running == True,
                Workspace.auto_stop_hours > 0
            ).all()

            summary['checked'] = len(workspaces)
            self.logger.info(f"Checking {len(workspaces)} workspaces for auto-stop")

            current_time = datetime.utcnow()

            for workspace in workspaces:
                try:
                    # Calculate idle time
                    if workspace.last_accessed_at:
                        idle_time = current_time - workspace.last_accessed_at
                        idle_hours = idle_time.total_seconds() / 3600

                        if idle_hours >= workspace.auto_stop_hours:
                            # Workspace has been idle too long - stop it
                            self._stop_workspace(workspace)
                            summary['stopped'] += 1
                            summary['workspace_ids_stopped'].append(workspace.id)

                            self.logger.info(
                                f"Auto-stopped workspace {workspace.id} ({workspace.name}) "
                                f"after {idle_hours:.1f} hours idle (threshold: {workspace.auto_stop_hours}h)"
                            )
                        else:
                            # Still within threshold
                            remaining_hours = workspace.auto_stop_hours - idle_hours
                            self.logger.debug(
                                f"Workspace {workspace.id} ({workspace.name}) "
                                f"will auto-stop in {remaining_hours:.1f} hours"
                            )
                            summary['skipped'] += 1
                    else:
                        # No last_accessed_at timestamp - use last_started_at
                        if workspace.last_started_at:
                            running_time = current_time - workspace.last_started_at
                            running_hours = running_time.total_seconds() / 3600

                            if running_hours >= workspace.auto_stop_hours:
                                self._stop_workspace(workspace)
                                summary['stopped'] += 1
                                summary['workspace_ids_stopped'].append(workspace.id)

                                self.logger.info(
                                    f"Auto-stopped workspace {workspace.id} ({workspace.name}) "
                                    f"after {running_hours:.1f} hours running (no access tracking)"
                                )
                            else:
                                summary['skipped'] += 1
                        else:
                            # No timestamps at all - skip
                            self.logger.warning(
                                f"Workspace {workspace.id} has no access/start timestamp - skipping"
                            )
                            summary['skipped'] += 1

                except Exception as e:
                    summary['errors'] += 1
                    error_detail = {
                        'workspace_id': workspace.id,
                        'workspace_name': workspace.name,
                        'error': str(e)
                    }
                    summary['errors_detail'].append(error_detail)
                    self.logger.error(
                        f"Error processing workspace {workspace.id}: {str(e)}",
                        exc_info=True
                    )

            self.logger.info(
                f"Auto-stop check complete: "
                f"checked={summary['checked']}, stopped={summary['stopped']}, "
                f"skipped={summary['skipped']}, errors={summary['errors']}"
            )

            return summary

        except Exception as e:
            self.logger.error(f"Auto-stop scheduler failed: {str(e)}", exc_info=True)
            summary['errors'] += 1
            summary['errors_detail'].append({'error': str(e)})
            return summary

    def _stop_workspace(self, workspace: Workspace) -> None:
        """
        Stop a workspace and update its status.

        Args:
            workspace: Workspace model instance to stop
        """
        try:
            # Stop the workspace service
            result = self.provisioner.stop_workspace_service(workspace)

            if result['success']:
                # Update workspace status
                workspace.is_running = False
                workspace.last_stopped_at = datetime.utcnow()
                workspace.status = 'stopped'
                db.session.commit()

                self.logger.info(f"Successfully auto-stopped workspace {workspace.id}")
            else:
                raise WorkspaceProvisionerError(
                    f"Failed to stop workspace: {result.get('message', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Failed to stop workspace {workspace.id}: {str(e)}")
            raise

    def get_workspaces_due_for_stop(self) -> list:
        """
        Get list of workspaces that will be stopped in next check.

        Returns:
            list: Workspaces that are due for auto-stop
        """
        workspaces_due = []

        try:
            workspaces = Workspace.query.filter(
                Workspace.is_running == True,
                Workspace.auto_stop_hours > 0
            ).all()

            current_time = datetime.utcnow()

            for workspace in workspaces:
                if workspace.last_accessed_at:
                    idle_time = current_time - workspace.last_accessed_at
                    idle_hours = idle_time.total_seconds() / 3600

                    if idle_hours >= workspace.auto_stop_hours:
                        workspaces_due.append({
                            'id': workspace.id,
                            'name': workspace.name,
                            'idle_hours': round(idle_hours, 1),
                            'threshold_hours': workspace.auto_stop_hours
                        })
                elif workspace.last_started_at:
                    running_time = current_time - workspace.last_started_at
                    running_hours = running_time.total_seconds() / 3600

                    if running_hours >= workspace.auto_stop_hours:
                        workspaces_due.append({
                            'id': workspace.id,
                            'name': workspace.name,
                            'running_hours': round(running_hours, 1),
                            'threshold_hours': workspace.auto_stop_hours
                        })

            return workspaces_due

        except Exception as e:
            self.logger.error(f"Error getting workspaces due for stop: {str(e)}")
            return []


def run_auto_stop_check():
    """
    Standalone function to run auto-stop check.

    This function can be called from CLI, cron, or systemd timer.

    Example usage:
        $ flask shell
        >>> from app.services.auto_stop_scheduler import run_auto_stop_check
        >>> run_auto_stop_check()
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        scheduler = AutoStopScheduler()
        summary = scheduler.check_and_stop_idle_workspaces()

        print(f"Auto-Stop Scheduler Run Summary:")
        print(f"  Workspaces checked: {summary['checked']}")
        print(f"  Workspaces stopped: {summary['stopped']}")
        print(f"  Workspaces skipped: {summary['skipped']}")
        print(f"  Errors: {summary['errors']}")

        if summary['workspace_ids_stopped']:
            print(f"  Stopped workspace IDs: {', '.join(map(str, summary['workspace_ids_stopped']))}")

        if summary['errors_detail']:
            print(f"\n  Error details:")
            for error in summary['errors_detail']:
                print(f"    - {error}")

        return summary
