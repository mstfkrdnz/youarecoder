"""
Flask CLI commands for workspace management and scheduling tasks.
"""
import click
import json
import os
from flask import current_app
from flask.cli import with_appcontext
from app import db
from app.models import WorkspaceTemplate
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


@click.command('update-exchange-rates')
@click.option('--date', default=None, help='Target date (YYYY-MM-DD format, default: today)')
@with_appcontext
def update_exchange_rates_command(date):
    """
    Update exchange rates from TCMB (Turkish Central Bank).

    This command fetches the latest USD/TRY and EUR/TRY exchange rates
    from TCMB and updates the database for dynamic currency conversion.

    Usage:
        $ flask update-exchange-rates
        $ flask update-exchange-rates --date 2025-10-31
    """
    from app.services.tcmb_scraper import TCMBScraper
    from datetime import datetime

    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            click.echo(f'Updating exchange rates for {target_date}...')
        except ValueError:
            click.echo('❌ Error: Invalid date format. Use YYYY-MM-DD')
            return
    else:
        click.echo('Updating exchange rates for today...')

    scraper = TCMBScraper()
    result = scraper.update_database(target_date)

    click.echo('\n📊 Exchange Rate Update Summary:')
    click.echo(f'  Effective Date: {result.get("effective_date")}')
    click.echo(f'  Updated Currencies: {", ".join(result["updated"])}')
    click.echo(f'  Success: {"✓" if result["success"] else "✗"}')

    if result['errors']:
        click.echo('\n⚠️  Errors:')
        for error in result['errors']:
            click.echo(f'  - {error}')
    else:
        # Show current rates
        summary = scraper.get_rate_summary()
        click.echo('\n💱 Current Rates:')
        if summary['usd']:
            click.echo(f'  USD/TRY: {summary["usd"]["rate"]} (as of {summary["usd"]["date"]})')
        if summary['eur']:
            click.echo(f'  EUR/TRY: {summary["eur"]["rate"]} (as of {summary["eur"]["date"]})')
        click.echo(f'  Total records: {summary["total_records"]}')

        click.echo('\n✅ Exchange rates updated successfully.')


@click.command('seed-odoo-template')
@with_appcontext
def seed_odoo_template_command():
    """
    Seed Odoo 18.4 Development template into database.

    Usage:
        $ flask seed-odoo-template
    """
    template_file = os.path.join(
        current_app.root_path,
        '..',
        'seeds',
        'odoo_18_4_template.json'
    )

    if not os.path.exists(template_file):
        current_app.logger.error(f"Template file not found: {template_file}")
        click.echo(f"❌ Error: Template file not found at {template_file}")
        return

    try:
        # Load template configuration
        with open(template_file, 'r') as f:
            template_data = json.load(f)

        # Check if template already exists
        existing_template = WorkspaceTemplate.query.filter_by(
            name=template_data['name'],
            visibility='official'
        ).first()

        if existing_template:
            click.echo(f"⚠️  Template '{template_data['name']}' already exists (ID: {existing_template.id})")

            if not click.confirm('Update existing template?', default=False):
                click.echo('Skipping template update.')
                return

            # Update existing template
            existing_template.description = template_data['description']
            existing_template.category = template_data['category']
            existing_template.config = template_data['config']
            existing_template.is_active = template_data.get('is_active', True)

            db.session.commit()
            click.echo(f"✅ Template '{template_data['name']}' updated successfully!")
            click.echo(f"   ID: {existing_template.id}")
            click.echo(f"   Category: {existing_template.category}")
            click.echo(f"   Visibility: {existing_template.visibility}")
            return

        # Create new template
        template = WorkspaceTemplate(
            name=template_data['name'],
            description=template_data['description'],
            category=template_data['category'],
            visibility=template_data['visibility'],
            config=template_data['config'],
            is_active=template_data.get('is_active', True),
            company_id=None  # Official template (no company)
        )

        db.session.add(template)
        db.session.commit()

        click.echo(f"✅ Odoo 18.4 Development template created successfully!")
        click.echo(f"   Template ID: {template.id}")
        click.echo(f"   Name: {template.name}")
        click.echo(f"   Category: {template.category}")
        click.echo(f"   Visibility: {template.visibility}")
        click.echo(f"   Components:")
        click.echo(f"      - {len(template.config.get('packages', []))} system packages")
        click.echo(f"      - {len(template.config.get('extensions', []))} VS Code extensions")
        click.echo(f"      - {len(template.config.get('repositories', []))} Git repositories")
        click.echo(f"      - PostgreSQL database: {template.config.get('postgresql', {}).get('database', 'N/A')}")
        click.echo(f"      - SSH required: {template.config.get('ssh_required', False)}")
        click.echo(f"      - Multi-folder workspace: {len(template.config.get('workspace_file', {}).get('folders', []))} folders")

        current_app.logger.info(f"Odoo 18.4 template seeded successfully (ID: {template.id})")

    except json.JSONDecodeError as e:
        click.echo(f"❌ Error: Invalid JSON in template file: {str(e)}")
        current_app.logger.error(f"Template JSON decode error: {str(e)}")
    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Error seeding template: {str(e)}")
        current_app.logger.error(f"Template seeding error: {str(e)}")


def init_app(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(auto_stop_check_command)
    app.cli.add_command(collect_metrics_command)
    app.cli.add_command(cleanup_metrics_command)
    app.cli.add_command(update_exchange_rates_command)
    app.cli.add_command(seed_odoo_template_command)
