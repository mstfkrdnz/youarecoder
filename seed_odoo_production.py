#!/usr/bin/env python3
"""
Production script to seed Odoo 18.4 template into database.
Run this on the production server after deployment.
"""
import sys
import os
import json

# Add app directory to path
sys.path.insert(0, '/home/mustafa/youarecoder')

from app import create_app, db
from app.models import WorkspaceTemplate

def seed_odoo_template():
    """Seed Odoo 18.4 Development template into production database."""

    app = create_app()

    with app.app_context():
        template_file = '/home/mustafa/youarecoder/seeds/odoo_18_4_template.json'

        if not os.path.exists(template_file):
            print(f"❌ Error: Template file not found at {template_file}")
            sys.exit(1)

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
                print(f"⚠️  Template '{template_data['name']}' already exists (ID: {existing_template.id})")

                # Update existing template
                existing_template.description = template_data['description']
                existing_template.category = template_data['category']
                existing_template.config = template_data['config']
                existing_template.is_active = template_data.get('is_active', True)

                db.session.commit()
                print(f"✅ Template '{template_data['name']}' updated successfully!")
                print(f"   Template ID: {existing_template.id}")
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

            print(f"✅ Odoo 18.4 Development template created successfully!")
            print(f"   Template ID: {template.id}")
            print(f"   Name: {template.name}")
            print(f"   Category: {template.category}")
            print(f"   Visibility: {template.visibility}")
            print(f"\nTemplate Components:")
            print(f"   - System Packages: {len(template.config.get('packages', []))}")
            print(f"   - VS Code Extensions: {len(template.config.get('vscode_extensions', []))}")
            print(f"   - Git Repositories: {len(template.config.get('git_repositories', []))}")
            print(f"   - PostgreSQL Database: {template.config.get('postgresql', {}).get('database_name', 'N/A')}")
            print(f"   - Workspace Folders: {len(template.config.get('workspace_file', {}).get('folders', []))}")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error seeding template: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    seed_odoo_template()
