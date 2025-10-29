"""Add workspace templates system

Revision ID: 006
Revises: 005
Create Date: 2025-10-29

Implements workspace template system with:
- workspace_templates table for pre-configured environments
- JSON config field for template configuration
- template_id and template_applied_at fields in workspaces table
- Visibility control (official, company, user)
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Add workspace templates table and workspace template references."""

    # Create workspace_templates table
    op.create_table(
        'workspace_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('visibility', sa.String(length=20), nullable=False, server_default='company'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Add foreign keys
    op.create_foreign_key(
        'fk_workspace_templates_company_id',
        'workspace_templates', 'companies',
        ['company_id'], ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_workspace_templates_created_by',
        'workspace_templates', 'users',
        ['created_by'], ['id'],
        ondelete='CASCADE'
    )

    # Add indexes
    op.create_index(
        'ix_workspace_templates_company_id',
        'workspace_templates',
        ['company_id']
    )

    op.create_index(
        'ix_workspace_templates_category',
        'workspace_templates',
        ['category']
    )

    op.create_index(
        'ix_workspace_templates_visibility',
        'workspace_templates',
        ['visibility']
    )

    # Add template reference columns to workspaces table
    op.add_column('workspaces',
        sa.Column('template_id', sa.Integer(), nullable=True)
    )
    op.add_column('workspaces',
        sa.Column('template_applied_at', sa.DateTime(), nullable=True)
    )

    # Add foreign key constraint for template_id
    op.create_foreign_key(
        'fk_workspaces_template_id',
        'workspaces', 'workspace_templates',
        ['template_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create sample official templates
    connection = op.get_bind()

    # Get first admin user as creator (fallback to id=1 if no admin exists)
    admin_result = connection.execute(
        sa.text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    ).fetchone()
    admin_id = admin_result[0] if admin_result else 1

    # Official templates (no company_id, visibility='official')
    official_templates = [
        {
            'name': 'Python Development',
            'description': 'Python 3.11 environment with popular packages and debugging tools',
            'category': 'python',
            'visibility': 'official',
            'config': {
                'base_image': 'python:3.11',
                'packages': ['pytest', 'black', 'pylint', 'mypy', 'ipython'],
                'extensions': [
                    'ms-python.python',
                    'ms-python.vscode-pylance',
                    'ms-python.debugpy'
                ],
                'settings': {
                    'python.defaultInterpreterPath': '/usr/local/bin/python3',
                    'python.linting.enabled': True,
                    'python.formatting.provider': 'black'
                },
                'environment': {
                    'PYTHONUNBUFFERED': '1'
                }
            }
        },
        {
            'name': 'Node.js Development',
            'description': 'Node.js 20 LTS with TypeScript and popular frameworks',
            'category': 'nodejs',
            'visibility': 'official',
            'config': {
                'base_image': 'node:20',
                'packages': ['typescript', 'ts-node', 'nodemon', 'eslint', 'prettier'],
                'extensions': [
                    'dbaeumer.vscode-eslint',
                    'esbenp.prettier-vscode',
                    'ms-vscode.vscode-typescript-next'
                ],
                'settings': {
                    'editor.formatOnSave': True,
                    'editor.defaultFormatter': 'esbenp.prettier-vscode'
                },
                'environment': {
                    'NODE_ENV': 'development'
                }
            }
        },
        {
            'name': 'React Development',
            'description': 'React with TypeScript, Vite, and modern development tools',
            'category': 'web',
            'visibility': 'official',
            'config': {
                'base_image': 'node:20',
                'packages': ['create-vite', 'typescript', 'eslint', 'prettier'],
                'extensions': [
                    'dsznajder.es7-react-js-snippets',
                    'dbaeumer.vscode-eslint',
                    'esbenp.prettier-vscode',
                    'bradlc.vscode-tailwindcss'
                ],
                'settings': {
                    'emmet.includeLanguages': {
                        'javascript': 'javascriptreact',
                        'typescript': 'typescriptreact'
                    }
                },
                'post_create_script': 'npm install'
            }
        },
        {
            'name': 'Data Science',
            'description': 'Python data science stack with Jupyter, pandas, numpy, matplotlib',
            'category': 'data-science',
            'visibility': 'official',
            'config': {
                'base_image': 'python:3.11',
                'packages': [
                    'jupyter', 'jupyterlab', 'pandas', 'numpy',
                    'matplotlib', 'seaborn', 'scikit-learn', 'scipy'
                ],
                'extensions': [
                    'ms-python.python',
                    'ms-toolsai.jupyter',
                    'ms-python.vscode-pylance'
                ],
                'settings': {
                    'jupyter.notebookFileRoot': '${workspaceFolder}'
                }
            }
        },
        {
            'name': 'Go Development',
            'description': 'Go 1.21 with development tools and debugger',
            'category': 'go',
            'visibility': 'official',
            'config': {
                'base_image': 'golang:1.21',
                'packages': [],
                'extensions': [
                    'golang.go',
                    'golang.go-nightly'
                ],
                'settings': {
                    'go.useLanguageServer': True,
                    'go.toolsManagement.autoUpdate': True
                },
                'environment': {
                    'GO111MODULE': 'on'
                }
            }
        }
    ]

    for template in official_templates:
        connection.execute(
            sa.text("""
                INSERT INTO workspace_templates (name, description, category, visibility, is_active, config, company_id, created_by, usage_count, created_at, updated_at)
                VALUES (:name, :description, :category, :visibility, true, :config, NULL, :created_by, 0, :created_at, :updated_at)
            """),
            {
                'name': template['name'],
                'description': template['description'],
                'category': template['category'],
                'visibility': template['visibility'],
                'config': sa.text(f"'{sa.engine.url.make_url.__self__.json.dumps(template['config'])}'::json"),
                'created_by': admin_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        )

    connection.commit()


def downgrade():
    """Remove workspace templates table and workspace template references."""

    # Remove foreign key and columns from workspaces
    op.drop_constraint('fk_workspaces_template_id', 'workspaces', type_='foreignkey')
    op.drop_column('workspaces', 'template_applied_at')
    op.drop_column('workspaces', 'template_id')

    # Drop indexes
    op.drop_index('ix_workspace_templates_visibility', table_name='workspace_templates')
    op.drop_index('ix_workspace_templates_category', table_name='workspace_templates')
    op.drop_index('ix_workspace_templates_company_id', table_name='workspace_templates')

    # Drop foreign keys
    op.drop_constraint('fk_workspace_templates_created_by', 'workspace_templates', type_='foreignkey')
    op.drop_constraint('fk_workspace_templates_company_id', 'workspace_templates', type_='foreignkey')

    # Drop table
    op.drop_table('workspace_templates')
