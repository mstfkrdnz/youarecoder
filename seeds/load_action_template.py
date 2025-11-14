#!/usr/bin/env python3
"""
Load action-based template from JSON into database.

Usage:
    python3 load_action_template.py <template_json_file>
"""
import sys
import json
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import WorkspaceTemplate, TemplateActionSequence

def load_template(json_file_path):
    """Load template from JSON file into database."""

    # Read JSON file
    with open(json_file_path, 'r') as f:
        template_data = json.load(f)

    # Extract template metadata
    name = template_data['name']
    description = template_data.get('description', '')
    category = template_data.get('category', 'general')
    visibility = template_data.get('visibility', 'official')
    is_active = template_data.get('is_active', True)
    is_action_based = template_data.get('is_action_based', True)

    # Extract config (template_metadata + actions)
    config = template_data.get('config', {})

    print(f"\n📋 Loading Template: {name}")
    print(f"   Description: {description}")
    print(f"   Category: {category}")
    print(f"   Is Action-Based: {is_action_based}")

    # Check if template exists
    existing_template = WorkspaceTemplate.query.filter_by(name=name).first()

    if existing_template:
        print(f"\n⚠️  Template '{name}' already exists (ID: {existing_template.id})")
        response = input("   Update existing template? (y/N): ")
        if response.lower() != 'y':
            print("   Aborted.")
            return

        template = existing_template
        print(f"   Updating template ID {template.id}...")

        # Delete existing action sequences
        TemplateActionSequence.query.filter_by(template_id=template.id).delete()
        print(f"   Deleted existing action sequences")

    else:
        # Create new template
        template = WorkspaceTemplate(
            name=name,
            description=description,
            category=category,
            visibility=visibility,
            is_active=is_active,
            is_action_based=is_action_based
        )
        db.session.add(template)
        db.session.flush()  # Get template ID
        print(f"\n✅ Created new template (ID: {template.id})")

    # Update template fields
    template.description = description
    template.category = category
    template.visibility = visibility
    template.is_active = is_active
    template.is_action_based = is_action_based
    template.config = config

    # Create action sequences
    actions = config.get('actions', [])
    print(f"\n📦 Creating {len(actions)} action sequences...")

    for action_data in actions:
        action_seq = TemplateActionSequence(
            template_id=template.id,
            name=action_data['name'],
            order=action_data['order'],
            action_type=action_data['action_type'],
            description=action_data.get('description', ''),
            parameters=action_data.get('parameters', {}),
            conditions=action_data.get('conditions', {}),
            depends_on=action_data.get('depends_on', []),
            enabled=action_data.get('enabled', True)
        )
        db.session.add(action_seq)
        print(f"   [{action_seq.order:2d}] {action_seq.name} ({action_seq.action_type})")

    # Commit all changes
    db.session.commit()

    print(f"\n✅ Template loaded successfully!")
    print(f"   Template ID: {template.id}")
    print(f"   Total Actions: {len(actions)}")

    # Display metadata
    metadata = config.get('template_metadata', {})
    if metadata:
        print(f"\n📊 Template Metadata:")
        if 'additional_services' in metadata:
            print(f"   Additional Services:")
            for svc in metadata['additional_services']:
                print(f"     • {svc['name']} (port {svc['port']}, priority {svc.get('priority', 50)})")

        if 'environment_defaults' in metadata:
            print(f"   Environment Variables: {len(metadata['environment_defaults'])} defined")

    print("")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 load_action_template.py <template_json_file>")
        sys.exit(1)

    json_file = sys.argv[1]

    if not os.path.exists(json_file):
        print(f"Error: File not found: {json_file}")
        sys.exit(1)

    # Create Flask app context
    app = create_app()

    with app.app_context():
        load_template(json_file)

if __name__ == '__main__':
    main()
