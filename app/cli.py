"""
Flask CLI commands for workspace management and scheduling tasks.
"""
import click
from flask import current_app
from flask.cli import with_appcontext
from app.services.auto_stop_scheduler import AutoStopScheduler


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


def init_app(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(auto_stop_check_command)
