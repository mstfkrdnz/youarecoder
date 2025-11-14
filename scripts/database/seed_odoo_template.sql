-- Insert Odoo 18.4 Development Template
-- Run with: psql -d youarecoder -f seed_odoo_template.sql

-- Check if template already exists
DO $$
DECLARE
    template_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM workspace_templates
        WHERE name = 'Odoo 18.4 Development'
        AND visibility = 'official'
    ) INTO template_exists;

    IF template_exists THEN
        -- Update existing template
        UPDATE workspace_templates
        SET
            description = 'Complete Odoo 18.4 development environment with PostgreSQL, Python venv, community/enterprise repositories, and VS Code configuration',
            category = 'backend',
            is_active = TRUE,
            config = '{"ssh_required":true,"packages":["python3","python3-pip","python3-venv","postgresql","postgresql-contrib","libpq-dev","python3-dev","build-essential","libxml2-dev","libxslt1-dev","libldap2-dev","libsasl2-dev","libjpeg-dev","libpng-dev","libfreetype6-dev","liblcms2-dev","libwebp-dev","libtiff5-dev","libopenjp2-7-dev","zlib1g-dev","git","curl","wget","wkhtmltopdf","node-less"],"extensions":["anthropic.claude-code","ms-python.python","ms-python.debugpy","jigar-patel.odoosnippets"],"repositories":[{"url":"https://github.com/odoo/odoo.git","branch":"18.0","target":"odoo-community","private":false},{"url":"git@github.com:odoo/enterprise.git","branch":"18.0","target":"odoo-enterprise","private":true},{"url":"https://github.com/alkedos/m0-odoo-development.git","branch":"main","target":"odoo-dev-tools","private":false}],"settings":{"workbench.colorTheme":"Default Dark Modern","python.defaultInterpreterPath":"${workspaceFolder:odoo-dev-tools}/venv/bin/python","python.linting.enabled":true,"python.linting.pylintEnabled":true,"python.formatting.provider":"black","files.exclude":{"**/__pycache__":true,"**/*.pyc":true,"**/.pytest_cache":true},"editor.formatOnSave":true,"editor.rulers":[80,120],"python.analysis.extraPaths":["${workspaceFolder:odoo-community}","${workspaceFolder:odoo-enterprise}","${workspaceFolder:odoo-customs}"]},"postgresql":{"database":"odoo_dev"},"launch_json":{"version":"0.2.0","configurations":[{"name":"Odoo: Run Development Server","type":"debugpy","request":"launch","program":"${workspaceFolder:odoo-dev-tools}/odoo-run.py","console":"integratedTerminal","args":["--config=${workspaceFolder:odoo-dev-tools}/odoo.conf","-d","odoo_dev","-i","base","--dev=all"],"justMyCode":false,"env":{"PYTHONPATH":"${workspaceFolder:odoo-community}:${workspaceFolder:odoo-enterprise}:${workspaceFolder:odoo-customs}"}},{"name":"Odoo: Update Module","type":"debugpy","request":"launch","program":"${workspaceFolder:odoo-dev-tools}/odoo-run.py","console":"integratedTerminal","args":["--config=${workspaceFolder:odoo-dev-tools}/odoo.conf","-d","odoo_dev","-u","${input:moduleName}","--dev=all"],"justMyCode":false,"env":{"PYTHONPATH":"${workspaceFolder:odoo-community}:${workspaceFolder:odoo-enterprise}:${workspaceFolder:odoo-customs}"}}],"inputs":[{"id":"moduleName","type":"promptString","description":"Enter the module name to update","default":"base"}]},"workspace_file":{"folders":[{"name":"Odoo Community","path":"odoo-community"},{"name":"Odoo Enterprise","path":"odoo-enterprise"},{"name":"Custom Modules","path":"odoo-customs"},{"name":"Development Tools","path":"odoo-dev-tools"}],"settings":{"workbench.colorTheme":"Default Dark Modern"}},"environment":{"ODOO_RC":"${HOME}/odoo-dev-tools/odoo.conf","PYTHONPATH":"${HOME}/odoo-community:${HOME}/odoo-enterprise:${HOME}/odoo-customs"},"post_create_script":"#!/bin/bash\nset -e\n\n# Create custom modules directory\nmkdir -p ~/odoo-customs\n\n# Create Python virtual environment in odoo-dev-tools\ncd ~/odoo-dev-tools\npython3 -m venv venv\nsource venv/bin/activate\n\n# Install Odoo requirements\nif [ -f ~/odoo-community/requirements.txt ]; then\n    pip install --upgrade pip\n    pip install -r ~/odoo-community/requirements.txt\nfi\n\n# Install odoo-dev-tools requirements\nif [ -f requirements.txt ]; then\n    pip install -r requirements.txt\nfi\n\n# Create Odoo configuration file\ncat > odoo.conf << ''EOF''\n[options]\naddons_path = ~/odoo-community/addons,~/odoo-enterprise,~/odoo-customs\ndata_dir = ~/odoo-data\ndb_host = localhost\ndb_port = 5432\ndb_user = ${USER}\ndb_password = False\ndb_name = odoo_dev\nhttp_port = 8069\nlogfile = ~/odoo.log\nlog_level = info\nEOF\n\n# Create data directory\nmkdir -p ~/odoo-data\n\necho \"Odoo 18.4 development environment setup complete!\"\necho \"Virtual environment: ~/odoo-dev-tools/venv\"\necho \"Configuration file: ~/odoo-dev-tools/odoo.conf\"\necho \"Database: odoo_dev (initialized with -i base parameter)\"\necho \"\"\necho \"To start Odoo manually:\"\necho \"  cd ~/odoo-dev-tools\"\necho \"  source venv/bin/activate\"\necho \"  python odoo-run.py --config=odoo.conf -d odoo_dev\"\necho \"\"\necho \"Or use VS Code Run/Debug button (F5) to start with debugger!\"\n"}'::jsonb
        WHERE name = 'Odoo 18.4 Development' AND visibility = 'official';

        RAISE NOTICE 'Template "Odoo 18.4 Development" updated successfully';
    ELSE
        -- Insert new template
        -- Get first admin user for created_by
        WITH first_admin AS (
            SELECT id FROM users WHERE role = 'admin' LIMIT 1
        )
        INSERT INTO workspace_templates (
            name,
            description,
            category,
            visibility,
            is_active,
            config,
            company_id,
            created_by,
            created_at
        )
        SELECT
            'Odoo 18.4 Development',
            'Complete Odoo 18.4 development environment with PostgreSQL, Python venv, community/enterprise repositories, and VS Code configuration',
            'backend',
            'official',
            TRUE,
            '{"ssh_required":true,"packages":["python3","python3-pip","python3-venv","postgresql","postgresql-contrib","libpq-dev","python3-dev","build-essential","libxml2-dev","libxslt1-dev","libldap2-dev","libsasl2-dev","libjpeg-dev","libpng-dev","libfreetype6-dev","liblcms2-dev","libwebp-dev","libtiff5-dev","libopenjp2-7-dev","zlib1g-dev","git","curl","wget","wkhtmltopdf","node-less"],"extensions":["anthropic.claude-code","ms-python.python","ms-python.debugpy","jigar-patel.odoosnippets"],"repositories":[{"url":"https://github.com/odoo/odoo.git","branch":"18.0","target":"odoo-community","private":false},{"url":"git@github.com:odoo/enterprise.git","branch":"18.0","target":"odoo-enterprise","private":true},{"url":"https://github.com/alkedos/m0-odoo-development.git","branch":"main","target":"odoo-dev-tools","private":false}],"settings":{"workbench.colorTheme":"Default Dark Modern","python.defaultInterpreterPath":"${workspaceFolder:odoo-dev-tools}/venv/bin/python","python.linting.enabled":true,"python.linting.pylintEnabled":true,"python.formatting.provider":"black","files.exclude":{"**/__pycache__":true,"**/*.pyc":true,"**/.pytest_cache":true},"editor.formatOnSave":true,"editor.rulers":[80,120],"python.analysis.extraPaths":["${workspaceFolder:odoo-community}","${workspaceFolder:odoo-enterprise}","${workspaceFolder:odoo-customs}"]},"postgresql":{"database":"odoo_dev"},"launch_json":{"version":"0.2.0","configurations":[{"name":"Odoo: Run Development Server","type":"debugpy","request":"launch","program":"${workspaceFolder:odoo-dev-tools}/odoo-run.py","console":"integratedTerminal","args":["--config=${workspaceFolder:odoo-dev-tools}/odoo.conf","-d","odoo_dev","-i","base","--dev=all"],"justMyCode":false,"env":{"PYTHONPATH":"${workspaceFolder:odoo-community}:${workspaceFolder:odoo-enterprise}:${workspaceFolder:odoo-customs}"}},{"name":"Odoo: Update Module","type":"debugpy","request":"launch","program":"${workspaceFolder:odoo-dev-tools}/odoo-run.py","console":"integratedTerminal","args":["--config=${workspaceFolder:odoo-dev-tools}/odoo.conf","-d","odoo_dev","-u","${input:moduleName}","--dev=all"],"justMyCode":false,"env":{"PYTHONPATH":"${workspaceFolder:odoo-community}:${workspaceFolder:odoo-enterprise}:${workspaceFolder:odoo-customs}"}}],"inputs":[{"id":"moduleName","type":"promptString","description":"Enter the module name to update","default":"base"}]},"workspace_file":{"folders":[{"name":"Odoo Community","path":"odoo-community"},{"name":"Odoo Enterprise","path":"odoo-enterprise"},{"name":"Custom Modules","path":"odoo-customs"},{"name":"Development Tools","path":"odoo-dev-tools"}],"settings":{"workbench.colorTheme":"Default Dark Modern"}},"environment":{"ODOO_RC":"${HOME}/odoo-dev-tools/odoo.conf","PYTHONPATH":"${HOME}/odoo-community:${HOME}/odoo-enterprise:${HOME}/odoo-customs"},"post_create_script":"#!/bin/bash\nset -e\n\n# Create custom modules directory\nmkdir -p ~/odoo-customs\n\n# Create Python virtual environment in odoo-dev-tools\ncd ~/odoo-dev-tools\npython3 -m venv venv\nsource venv/bin/activate\n\n# Install Odoo requirements\nif [ -f ~/odoo-community/requirements.txt ]; then\n    pip install --upgrade pip\n    pip install -r ~/odoo-community/requirements.txt\nfi\n\n# Install odoo-dev-tools requirements\nif [ -f requirements.txt ]; then\n    pip install -r requirements.txt\nfi\n\n# Create Odoo configuration file\ncat > odoo.conf << ''EOF''\n[options]\naddons_path = ~/odoo-community/addons,~/odoo-enterprise,~/odoo-customs\ndata_dir = ~/odoo-data\ndb_host = localhost\ndb_port = 5432\ndb_user = ${USER}\ndb_password = False\ndb_name = odoo_dev\nhttp_port = 8069\nlogfile = ~/odoo.log\nlog_level = info\nEOF\n\n# Create data directory\nmkdir -p ~/odoo-data\n\necho \"Odoo 18.4 development environment setup complete!\"\necho \"Virtual environment: ~/odoo-dev-tools/venv\"\necho \"Configuration file: ~/odoo-dev-tools/odoo.conf\"\necho \"Database: odoo_dev (initialized with -i base parameter)\"\necho \"\"\necho \"To start Odoo manually:\"\necho \"  cd ~/odoo-dev-tools\"\necho \"  source venv/bin/activate\"\necho \"  python odoo-run.py --config=odoo.conf -d odoo_dev\"\necho \"\"\necho \"Or use VS Code Run/Debug button (F5) to start with debugger!\"\n"}'::jsonb,
            NULL,
            id,
            NOW()
        FROM first_admin;

        RAISE NOTICE 'Template "Odoo 18.4 Development" created successfully';
    END IF;
END $$;

-- Display result
SELECT id, name, category, visibility, is_active, created_at
FROM workspace_templates
WHERE name = 'Odoo 18.4 Development' AND visibility = 'official';
