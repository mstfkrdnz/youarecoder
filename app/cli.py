"""
Flask CLI commands for workspace management and scheduling tasks.
"""
import click
from flask import current_app
from flask.cli import with_appcontext
from app.services.auto_stop_scheduler import AutoStopScheduler
from app.services.resource_metrics_collector import ResourceMetricsCollector


@click.command('auto-stop-check')
@with_appcontext
def auto_stop_check_command():
    """
    Run auto-stop check for idle workspaces.

    Usage:
        $ flask auto-stop-check
    """
    click.echo('Starting auto-stop check...')

    scheduler = AutoStopScheduler()
    summary = scheduler.check_and_stop_idle_workspaces()

    click.echo('\nAuto-Stop Scheduler Run Summary:')
    click.echo(f'  Workspaces checked: {summary["checked"]}')
    click.echo(f'  Workspaces stopped: {summary["stopped"]}')
    click.echo(f'  Workspaces skipped: {summary["skipped"]}')
    click.echo(f'  Errors: {summary["errors"]}')

    if summary['workspace_ids_stopped']:
        click.echo(f'  Stopped workspace IDs: {", ".join(map(str, summary["workspace_ids_stopped"]))}')

    if summary['errors_detail']:
        click.echo('\nError details:')
        for error in summary['errors_detail']:
            click.echo(f'  - {error}')

    click.echo('\nAuto-stop check complete.')


@click.command('collect-metrics')
@with_appcontext
def collect_metrics_command():
    """
    Collect resource usage metrics for all running workspaces.

    Usage:
        $ flask collect-metrics
    """
    click.echo('Starting metrics collection...')

    collector = ResourceMetricsCollector()
    summary = collector.collect_all_running_workspaces()

    click.echo('\nMetrics Collection Summary:')
    click.echo(f'  Workspaces checked: {summary["checked"]}')
    click.echo(f'  Metrics collected: {summary["collected"]}')
    click.echo(f'  Errors: {summary["errors"]}')

    if summary['workspace_ids_collected']:
        click.echo(f'  Collected for workspace IDs: {", ".join(map(str, summary["workspace_ids_collected"]))}')

    if summary['errors_detail']:
        click.echo('\nError details:')
        for error in summary['errors_detail']:
            click.echo(f'  - {error}')

    click.echo('\nMetrics collection complete.')


@click.command('cleanup-metrics')
@click.option('--days', default=30, help='Number of days to retain metrics (default: 30)')
@with_appcontext
def cleanup_metrics_command(days):
    """
    Clean up old workspace metrics.

    Usage:
        $ flask cleanup-metrics
        $ flask cleanup-metrics --days 60
    """
    click.echo(f'Cleaning up metrics older than {days} days...')

    collector = ResourceMetricsCollector()
    deleted = collector.cleanup_old_metrics(retention_days=days)

    click.echo(f'\nDeleted {deleted} old metrics records.')


def init_app(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(auto_stop_check_command)
    app.cli.add_command(collect_metrics_command)
    app.cli.add_command(cleanup_metrics_command)
