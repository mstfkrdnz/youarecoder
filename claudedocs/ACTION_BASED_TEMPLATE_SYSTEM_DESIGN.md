# Action-Based İteratif Template Sistemi - Tasarım Dökümanı

## 📋 Mevcut Sistem Analizi

### Mevcut Mimari
Şu anda `WorkspaceTemplate` modeli tek bir monolitik JSON yapısı kullanıyor:

```python
# Mevcut Template Yapısı (seed_odoo_template.sql'den)
config = {
    "ssh_required": bool,
    "packages": ["paket1", "paket2"],
    "extensions": ["ext1", "ext2"],
    "repositories": [...],
    "settings": {...},
    "postgresql": {...},
    "launch_json": {...},
    "workspace_file": {...},
    "environment": {...},
    "post_create_script": "bash komutları"
}
```

### Mevcut Provisioning Akışı
`WorkspaceProvisioner.provision_workspace()` metodu:
1. State machine ile sabit adımlar kullanıyor (`POSTGRESQL_STEPS`, `TEMPLATE_WITH_SSH_STEPS`)
2. Template config'i `apply_workspace_template()` içinde tek seferde işliyor
3. Her adım hard-coded ve sıralı
4. Retry logic sadece workspace seviyesinde, action seviyesinde değil

### Sorunlar
- ❌ Template'ler arasında action paylaşımı yok (kod tekrarı)
- ❌ Conditional execution yok (her template için farklı step sequence)
- ❌ Action-level retry/rollback yok
- ❌ Fine-grained progress tracking yok
- ❌ Template versiyonlama ve inheritance yok
- ❌ Yeni action eklemek kod değişikliği gerektiriyor

---

## 🎯 Önerilen Action-Based Mimari

### 1. Yeni Database Şeması

#### TemplateAction Tablosu
```sql
CREATE TABLE template_actions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,  -- "install_postgresql", "create_venv"
    display_name VARCHAR(200) NOT NULL,  -- "PostgreSQL Kurulumu"
    category VARCHAR(50) NOT NULL,  -- "system", "database", "environment", "repository", "configuration"
    description TEXT,
    
    -- Action behavior
    action_type VARCHAR(50) NOT NULL,  -- "shell", "python_function", "template_copy", "api_call"
    execution_handler TEXT NOT NULL,  -- Function name or shell script
    validation_handler TEXT,  -- Validation logic
    rollback_handler TEXT,  -- Rollback logic
    
    -- Configuration schema
    config_schema JSONB,  -- JSON Schema for required/optional parameters
    default_config JSONB,  -- Default parameter values
    
    -- Retry and timeout
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 300,
    retry_delay_seconds INTEGER DEFAULT 5,
    exponential_backoff BOOLEAN DEFAULT TRUE,
    
    -- Dependencies and conditions
    requires_actions INTEGER[],  -- Array of action IDs that must complete first
    conflicts_with_actions INTEGER[],  -- Actions that can't run together
    condition_expression TEXT,  -- SQL/Python expression for conditional execution
    
    -- Resource requirements
    estimated_duration_seconds INTEGER,
    requires_sudo BOOLEAN DEFAULT FALSE,
    requires_network BOOLEAN DEFAULT FALSE,
    disk_space_required_mb INTEGER,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    is_system BOOLEAN DEFAULT TRUE,  -- System vs user-defined
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);

CREATE INDEX idx_action_category ON template_actions(category);
CREATE INDEX idx_action_type ON template_actions(action_type);
```

#### TemplateActionSequence Tablosu
```sql
CREATE TABLE template_action_sequences (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES workspace_templates(id) ON DELETE CASCADE,
    action_id INTEGER NOT NULL REFERENCES template_actions(id) ON DELETE CASCADE,
    
    -- Execution order
    sequence_order INTEGER NOT NULL,  -- Execution order within template
    phase VARCHAR(50),  -- "pre_setup", "main", "post_setup", "validation"
    
    -- Action-specific configuration for this template
    action_config JSONB,  -- Override default config
    
    -- Conditional execution
    condition_expression TEXT,  -- Template-specific condition
    skip_on_error BOOLEAN DEFAULT FALSE,  -- Continue even if this action fails
    
    -- Retry configuration (template-specific override)
    max_retries INTEGER,  -- NULL = use action default
    timeout_seconds INTEGER,  -- NULL = use action default
    
    UNIQUE(template_id, sequence_order),
    UNIQUE(template_id, action_id)  -- Action can only appear once per template
);

CREATE INDEX idx_sequence_template ON template_action_sequences(template_id, sequence_order);
```

#### WorkspaceActionExecution Tablosu
```sql
CREATE TABLE workspace_action_executions (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    action_id INTEGER NOT NULL REFERENCES template_actions(id),
    sequence_id INTEGER REFERENCES template_action_sequences(id),
    
    -- Execution tracking
    status VARCHAR(20) NOT NULL,  -- "pending", "running", "completed", "failed", "skipped", "rolled_back"
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Retry tracking
    attempt_number INTEGER DEFAULT 1,
    max_retries INTEGER NOT NULL,
    next_retry_at TIMESTAMP,
    
    -- Execution context
    action_config JSONB,  -- Actual config used
    execution_output TEXT,  -- stdout/stderr
    error_message TEXT,
    exit_code INTEGER,
    
    -- Result data
    result_data JSONB,  -- Structured result data
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_workspace_executions ON workspace_action_executions(workspace_id, started_at);
CREATE INDEX idx_execution_status ON workspace_action_executions(workspace_id, status);
```

### 2. Action Kategorileri ve Örnekler

#### System Actions
```json
{
  "name": "install_system_packages",
  "display_name": "Sistem Paketlerini Kur",
  "category": "system",
  "action_type": "shell",
  "execution_handler": "apt_install_packages",
  "config_schema": {
    "type": "object",
    "properties": {
      "packages": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1
      }
    },
    "required": ["packages"]
  },
  "max_retries": 3,
  "timeout_seconds": 600
}
```

#### Database Actions
```json
{
  "name": "create_postgresql_database",
  "display_name": "PostgreSQL Veritabanı Oluştur",
  "category": "database",
  "action_type": "python_function",
  "execution_handler": "create_postgres_db",
  "validation_handler": "validate_postgres_db",
  "rollback_handler": "drop_postgres_db",
  "config_schema": {
    "type": "object",
    "properties": {
      "database_name": {"type": "string"},
      "owner": {"type": "string"},
      "encoding": {"type": "string", "default": "UTF8"}
    },
    "required": ["database_name", "owner"]
  },
  "requires_actions": [1],  -- Requires "create_postgresql_user" action
  "max_retries": 2
}
```

#### Environment Actions
```json
{
  "name": "create_python_venv",
  "display_name": "Python Virtual Environment Oluştur",
  "category": "environment",
  "action_type": "shell",
  "execution_handler": "create_venv",
  "validation_handler": "validate_venv",
  "config_schema": {
    "type": "object",
    "properties": {
      "python_version": {"type": "string", "default": "python3"},
      "venv_path": {"type": "string"},
      "requirements_file": {"type": "string"}
    },
    "required": ["venv_path"]
  },
  "max_retries": 3,
  "timeout_seconds": 300
}
```

#### Repository Actions
```json
{
  "name": "clone_git_repository",
  "display_name": "Git Deposunu Klonla",
  "category": "repository",
  "action_type": "python_function",
  "execution_handler": "clone_repository",
  "validation_handler": "validate_repository",
  "config_schema": {
    "type": "object",
    "properties": {
      "url": {"type": "string", "format": "uri"},
      "branch": {"type": "string", "default": "main"},
      "target_dir": {"type": "string"},
      "shallow": {"type": "boolean", "default": false},
      "private": {"type": "boolean", "default": false}
    },
    "required": ["url"]
  },
  "condition_expression": "workspace.ssh_public_key IS NOT NULL OR config.private = FALSE",
  "requires_network": true,
  "max_retries": 3
}
```

#### Configuration Actions
```json
{
  "name": "create_vscode_settings",
  "display_name": "VS Code Ayarlarını Oluştur",
  "category": "configuration",
  "action_type": "template_copy",
  "execution_handler": "copy_template_file",
  "config_schema": {
    "type": "object",
    "properties": {
      "settings": {"type": "object"},
      "target_path": {"type": "string"}
    },
    "required": ["settings"]
  },
  "max_retries": 2,
  "timeout_seconds": 30
}
```

### 3. Örnek Template Yapısı

#### Odoo 18.4 Template - Yeni Action-Based Format
```json
{
  "template_id": 1,
  "name": "Odoo 18.4 Development",
  "description": "Complete Odoo 18.4 development environment",
  "version": "1.0.0",
  "base_template_id": null,
  
  "actions": [
    {
      "sequence_order": 10,
      "action_id": 1,
      "action_name": "install_system_packages",
      "phase": "pre_setup",
      "action_config": {
        "packages": [
          "python3", "python3-pip", "python3-venv",
          "postgresql", "postgresql-contrib", "libpq-dev",
          "python3-dev", "build-essential",
          "libxml2-dev", "libxslt1-dev", "wkhtmltopdf"
        ]
      },
      "skip_on_error": false
    },
    {
      "sequence_order": 20,
      "action_id": 5,
      "action_name": "create_postgresql_user",
      "phase": "pre_setup",
      "action_config": {
        "username": "{{workspace.linux_username}}",
        "database": "{{workspace.linux_username}}_odoo"
      }
    },
    {
      "sequence_order": 30,
      "action_id": 6,
      "action_name": "create_postgresql_database",
      "phase": "main",
      "action_config": {
        "database_name": "{{workspace.linux_username}}_odoo",
        "owner": "{{workspace.linux_username}}",
        "encoding": "UTF8"
      },
      "requires": [20]  -- Requires postgresql user creation
    },
    {
      "sequence_order": 40,
      "action_id": 10,
      "action_name": "create_python_venv",
      "phase": "main",
      "action_config": {
        "python_version": "python3",
        "venv_path": "~/odoo-dev-tools/venv"
      }
    },
    {
      "sequence_order": 50,
      "action_id": 11,
      "action_name": "install_pip_requirements",
      "phase": "main",
      "action_config": {
        "venv_path": "~/odoo-dev-tools/venv",
        "requirements_file": "~/odoo-community/requirements.txt"
      },
      "requires": [40],  -- Requires venv creation
      "condition_expression": "file_exists('~/odoo-community/requirements.txt')"
    },
    {
      "sequence_order": 60,
      "action_id": 15,
      "action_name": "clone_git_repository",
      "phase": "main",
      "action_config": {
        "url": "https://github.com/odoo/odoo.git",
        "branch": "18.0",
        "target_dir": "~/odoo-community",
        "shallow": false
      },
      "max_retries": 5
    },
    {
      "sequence_order": 70,
      "action_id": 15,
      "action_name": "clone_git_repository",
      "phase": "main",
      "action_config": {
        "url": "git@github.com:odoo/enterprise.git",
        "branch": "18.0",
        "target_dir": "~/odoo-enterprise",
        "private": true
      },
      "condition_expression": "workspace.ssh_public_key IS NOT NULL",
      "skip_on_error": true  -- Optional repository
    },
    {
      "sequence_order": 80,
      "action_id": 20,
      "action_name": "install_vscode_extensions",
      "phase": "post_setup",
      "action_config": {
        "extensions": [
          "ms-python.python",
          "ms-python.debugpy",
          "jigar-patel.odoosnippets"
        ]
      }
    },
    {
      "sequence_order": 90,
      "action_id": 25,
      "action_name": "create_vscode_settings",
      "phase": "post_setup",
      "action_config": {
        "settings": {
          "python.defaultInterpreterPath": "~/odoo-dev-tools/venv/bin/python",
          "python.linting.enabled": true
        }
      }
    },
    {
      "sequence_order": 100,
      "action_id": 30,
      "action_name": "execute_custom_script",
      "phase": "post_setup",
      "action_config": {
        "script": "#!/bin/bash\nset -e\nmkdir -p ~/odoo-customs\ncat > ~/odoo-dev-tools/odoo.conf << 'CONF'\n[options]\naddons_path = ~/odoo-community/addons,~/odoo-enterprise,~/odoo-customs\ndb_name = {{workspace.db_name}}\nCONF\n"
      }
    }
  ],
  
  "global_config": {
    "continue_on_non_critical_errors": true,
    "parallel_execution_enabled": false,
    "rollback_on_failure": true
  }
}
```

### 4. Template Inheritance Örneği

#### Base Python Template
```json
{
  "template_id": 100,
  "name": "Python Base",
  "version": "1.0.0",
  "actions": [
    {
      "sequence_order": 10,
      "action_name": "install_system_packages",
      "action_config": {
        "packages": ["python3", "python3-pip", "python3-venv"]
      }
    },
    {
      "sequence_order": 20,
      "action_name": "create_python_venv",
      "action_config": {
        "venv_path": "~/venv"
      }
    }
  ]
}
```

#### Django Template (Inherits from Python Base)
```json
{
  "template_id": 101,
  "name": "Django Development",
  "version": "1.0.0",
  "base_template_id": 100,  -- Inherits from Python Base
  
  "actions": [
    // Inherited actions from base template run first (10, 20)
    {
      "sequence_order": 30,
      "action_name": "install_pip_requirements",
      "action_config": {
        "venv_path": "~/venv",
        "packages": ["django", "djangorestframework", "psycopg2-binary"]
      }
    },
    {
      "sequence_order": 40,
      "action_name": "create_django_project",
      "action_config": {
        "project_name": "myproject"
      }
    }
  ]
}
```

---

## 🔧 Kod Değişiklikleri

### 1. Yeni Action Handler Sistemi

#### `/app/services/action_handlers.py` (YENİ)
```python
"""
Action execution handlers for workspace provisioning.
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import subprocess
import json


class ActionHandler(ABC):
    """Base class for action handlers."""
    
    @abstractmethod
    def execute(self, workspace, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the action."""
        pass
    
    @abstractmethod
    def validate(self, workspace, result: Dict[str, Any]) -> bool:
        """Validate action execution."""
        pass
    
    @abstractmethod
    def rollback(self, workspace, result: Dict[str, Any]) -> bool:
        """Rollback action if failed."""
        pass


class ShellActionHandler(ActionHandler):
    """Handler for shell script actions."""
    
    def execute(self, workspace, config: Dict[str, Any]) -> Dict[str, Any]:
        script = config.get('script', '')
        # Interpolate variables
        script = self._interpolate_variables(script, workspace, config)
        
        result = subprocess.run(
            script,
            shell=True,
            capture_output=True,
            text=True,
            timeout=config.get('timeout_seconds', 300)
        )
        
        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    
    def validate(self, workspace, result: Dict[str, Any]) -> bool:
        return result.get('success', False)
    
    def rollback(self, workspace, result: Dict[str, Any]) -> bool:
        # Shell actions typically don't have automatic rollback
        return True
    
    def _interpolate_variables(self, script: str, workspace, config: Dict) -> str:
        """Replace {{variable}} placeholders."""
        variables = {
            'workspace.linux_username': workspace.linux_username,
            'workspace.db_name': workspace.db_name,
            'workspace.port': str(workspace.port),
            **{f'config.{k}': str(v) for k, v in config.items()}
        }
        
        for key, value in variables.items():
            script = script.replace(f'{{{{{key}}}}}', value)
        
        return script


class PythonFunctionHandler(ActionHandler):
    """Handler for Python function actions."""
    
    def __init__(self, provisioner):
        self.provisioner = provisioner
    
    def execute(self, workspace, config: Dict[str, Any]) -> Dict[str, Any]:
        function_name = config.get('function_name')
        function_params = config.get('params', {})
        
        # Get function from provisioner
        if hasattr(self.provisioner, function_name):
            func = getattr(self.provisioner, function_name)
            result = func(workspace, **function_params)
            return {'success': True, 'result': result}
        else:
            return {'success': False, 'error': f'Function {function_name} not found'}
    
    def validate(self, workspace, result: Dict[str, Any]) -> bool:
        return result.get('success', False)
    
    def rollback(self, workspace, result: Dict[str, Any]) -> bool:
        # Implement based on specific function
        return True


class ActionHandlerRegistry:
    """Registry for action handlers."""
    
    _handlers = {}
    
    @classmethod
    def register(cls, action_type: str, handler_class):
        """Register an action handler."""
        cls._handlers[action_type] = handler_class
    
    @classmethod
    def get_handler(cls, action_type: str, provisioner=None) -> ActionHandler:
        """Get handler for action type."""
        handler_class = cls._handlers.get(action_type)
        if not handler_class:
            raise ValueError(f'No handler registered for action type: {action_type}')
        
        if action_type == 'python_function':
            return handler_class(provisioner)
        return handler_class()


# Register default handlers
ActionHandlerRegistry.register('shell', ShellActionHandler)
ActionHandlerRegistry.register('python_function', PythonFunctionHandler)
```

### 2. Action Executor Engine

#### `/app/services/action_executor.py` (YENİ)
```python
"""
Action execution engine for workspace provisioning.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app import db
from app.models import (
    Workspace, 
    TemplateAction, 
    TemplateActionSequence,
    WorkspaceActionExecution
)
from app.services.action_handlers import ActionHandlerRegistry
from flask import current_app
import time


class ActionExecutor:
    """Executes template actions with retry, validation, and rollback."""
    
    def __init__(self, workspace: Workspace, provisioner):
        self.workspace = workspace
        self.provisioner = provisioner
        self.execution_history = []
    
    def execute_template_actions(self, template) -> Dict[str, Any]:
        """
        Execute all actions in template sequence.
        
        Returns:
            dict: Execution summary with success/failure details
        """
        result = {
            'success': False,
            'total_actions': 0,
            'completed_actions': 0,
            'failed_actions': 0,
            'skipped_actions': 0,
            'execution_details': []
        }
        
        # Get action sequence for template
        sequences = TemplateActionSequence.query.filter_by(
            template_id=template.id
        ).order_by(TemplateActionSequence.sequence_order).all()
        
        result['total_actions'] = len(sequences)
        
        for sequence in sequences:
            action = TemplateAction.query.get(sequence.action_id)
            if not action or not action.is_active:
                continue
            
            # Check condition
            if not self._evaluate_condition(sequence, action):
                current_app.logger.info(
                    f"Skipping action {action.name} - condition not met"
                )
                result['skipped_actions'] += 1
                continue
            
            # Execute action with retry logic
            action_result = self._execute_action_with_retry(action, sequence)
            
            result['execution_details'].append({
                'action_name': action.name,
                'display_name': action.display_name,
                'status': action_result['status'],
                'duration_seconds': action_result.get('duration_seconds'),
                'attempts': action_result.get('attempts', 1)
            })
            
            if action_result['status'] == 'completed':
                result['completed_actions'] += 1
            elif action_result['status'] == 'failed':
                result['failed_actions'] += 1
                
                # Check if we should stop on error
                if not sequence.skip_on_error:
                    result['error'] = f"Critical action failed: {action.name}"
                    result['failed_action'] = action.name
                    
                    # Rollback if configured
                    if template.config.get('rollback_on_failure', True):
                        self._rollback_completed_actions()
                    
                    return result
        
        result['success'] = result['failed_actions'] == 0
        return result
    
    def _execute_action_with_retry(
        self, 
        action: TemplateAction, 
        sequence: TemplateActionSequence
    ) -> Dict[str, Any]:
        """Execute action with retry logic."""
        
        max_retries = sequence.max_retries or action.max_retries
        timeout_seconds = sequence.timeout_seconds or action.timeout_seconds
        
        for attempt in range(1, max_retries + 1):
            # Create execution record
            execution = WorkspaceActionExecution(
                workspace_id=self.workspace.id,
                action_id=action.id,
                sequence_id=sequence.id,
                status='running',
                started_at=datetime.utcnow(),
                attempt_number=attempt,
                max_retries=max_retries,
                action_config=sequence.action_config
            )
            db.session.add(execution)
            db.session.commit()
            
            try:
                # Get action handler
                handler = ActionHandlerRegistry.get_handler(
                    action.action_type, 
                    self.provisioner
                )
                
                # Execute action
                start_time = time.time()
                execution_result = handler.execute(
                    self.workspace,
                    sequence.action_config or action.default_config
                )
                duration = int(time.time() - start_time)
                
                # Validate result
                is_valid = handler.validate(self.workspace, execution_result)
                
                if is_valid:
                    execution.status = 'completed'
                    execution.completed_at = datetime.utcnow()
                    execution.duration_seconds = duration
                    execution.result_data = execution_result
                    execution.execution_output = execution_result.get('stdout', '')
                    db.session.commit()
                    
                    self.execution_history.append(execution)
                    
                    current_app.logger.info(
                        f"Action {action.name} completed in {duration}s "
                        f"(attempt {attempt}/{max_retries})"
                    )
                    
                    return {
                        'status': 'completed',
                        'duration_seconds': duration,
                        'attempts': attempt,
                        'execution_id': execution.id
                    }
                else:
                    raise Exception(f"Validation failed: {execution_result}")
                    
            except Exception as e:
                execution.status = 'failed'
                execution.completed_at = datetime.utcnow()
                execution.error_message = str(e)
                execution.execution_output = str(e)
                db.session.commit()
                
                current_app.logger.error(
                    f"Action {action.name} failed (attempt {attempt}/{max_retries}): {e}"
                )
                
                # Check if we should retry
                if attempt < max_retries:
                    # Calculate backoff delay
                    if action.exponential_backoff:
                        delay = action.retry_delay_seconds * (2 ** (attempt - 1))
                    else:
                        delay = action.retry_delay_seconds
                    
                    execution.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                    db.session.commit()
                    
                    current_app.logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    # All retries exhausted
                    return {
                        'status': 'failed',
                        'error': str(e),
                        'attempts': attempt,
                        'execution_id': execution.id
                    }
        
        return {'status': 'failed', 'error': 'Unknown error'}
    
    def _evaluate_condition(
        self, 
        sequence: TemplateActionSequence, 
        action: TemplateAction
    ) -> bool:
        """Evaluate if action should be executed based on conditions."""
        
        # Check sequence-specific condition first
        if sequence.condition_expression:
            return self._evaluate_expression(sequence.condition_expression)
        
        # Check action-level condition
        if action.condition_expression:
            return self._evaluate_expression(action.condition_expression)
        
        return True
    
    def _evaluate_expression(self, expression: str) -> bool:
        """
        Evaluate condition expression.
        
        Supports:
        - workspace.field_name checks
        - file_exists() checks
        - Simple boolean expressions
        """
        try:
            # Simple implementation - extend as needed
            if 'workspace.ssh_public_key IS NOT NULL' in expression:
                return self.workspace.ssh_public_key is not None
            
            if 'file_exists' in expression:
                # Extract file path
                import re
                match = re.search(r"file_exists\('([^']+)'\)", expression)
                if match:
                    file_path = match.group(1)
                    # Interpolate variables
                    file_path = file_path.replace(
                        '{{workspace.linux_username}}', 
                        self.workspace.linux_username
                    )
                    import os
                    return os.path.exists(file_path)
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Condition evaluation error: {e}")
            return False
    
    def _rollback_completed_actions(self) -> None:
        """Rollback all completed actions in reverse order."""
        current_app.logger.info(
            f"Rolling back {len(self.execution_history)} completed actions"
        )
        
        for execution in reversed(self.execution_history):
            action = TemplateAction.query.get(execution.action_id)
            if not action.rollback_handler:
                continue
            
            try:
                handler = ActionHandlerRegistry.get_handler(
                    action.action_type, 
                    self.provisioner
                )
                
                rollback_result = handler.rollback(
                    self.workspace,
                    execution.result_data
                )
                
                if rollback_result:
                    execution.status = 'rolled_back'
                    db.session.commit()
                    current_app.logger.info(f"Rolled back action: {action.name}")
                    
            except Exception as e:
                current_app.logger.error(f"Rollback failed for {action.name}: {e}")
```

### 3. Provisioner İntegrasyonu

#### `workspace_provisioner.py` Değişiklikleri
```python
# Add to WorkspaceProvisioner class

from app.services.action_executor import ActionExecutor

def apply_workspace_template_v2(
    self, 
    workspace: Workspace, 
    template: WorkspaceTemplate
) -> Dict[str, any]:
    """
    Apply template using action-based system (v2).
    
    This replaces the monolithic apply_workspace_template() method.
    """
    result = {
        'success': False,
        'template_id': template.id,
        'template_name': template.name
    }
    
    try:
        # Initialize action executor
        executor = ActionExecutor(workspace, self)
        
        # Execute template actions
        execution_result = executor.execute_template_actions(template)
        
        result.update(execution_result)
        
        if execution_result['success']:
            # Update template usage and applied timestamp
            template.usage_count += 1
            workspace.template_applied_at = db.func.now()
            db.session.commit()
            
            result['message'] = (
                f"Template '{template.name}' applied successfully. "
                f"{execution_result['completed_actions']}/{execution_result['total_actions']} "
                f"actions completed"
            )
        
        return result
        
    except Exception as e:
        current_app.logger.error(f"Template application failed: {str(e)}")
        result['error'] = str(e)
        return result
```

---

## 🗄️ Migration Stratejisi

### Adım 1: Schema Migration
```python
# /migrations/versions/012_add_action_based_templates.py

def upgrade():
    # Create template_actions table
    op.create_table(
        'template_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        # ... (full schema from above)
    )
    
    # Create template_action_sequences table
    op.create_table('template_action_sequences', ...)
    
    # Create workspace_action_executions table
    op.create_table('workspace_action_executions', ...)
    
    # Add indexes
    op.create_index('idx_action_category', 'template_actions', ['category'])
    # ...


def downgrade():
    op.drop_table('workspace_action_executions')
    op.drop_table('template_action_sequences')
    op.drop_table('template_actions')
```

### Adım 2: Seed Actions
```python
# /seeds/seed_template_actions.py

"""Seed standard template actions."""

STANDARD_ACTIONS = [
    {
        'name': 'install_system_packages',
        'display_name': 'Sistem Paketlerini Kur',
        'category': 'system',
        'action_type': 'shell',
        'execution_handler': 'apt_install_packages',
        'config_schema': {...},
        'is_system': True
    },
    # ... all other actions
]

def seed_actions():
    for action_data in STANDARD_ACTIONS:
        action = TemplateAction(**action_data)
        db.session.add(action)
    
    db.session.commit()
```

### Adım 3: Migrate Existing Templates
```python
# /scripts/migrate_templates_to_actions.py

"""
Migrate existing monolithic templates to action-based format.
"""

def migrate_odoo_template():
    """Convert Odoo template to action-based."""
    
    odoo_template = WorkspaceTemplate.query.filter_by(
        name='Odoo 18.4 Development'
    ).first()
    
    if not odoo_template:
        return
    
    old_config = odoo_template.config
    
    # Create action sequences
    sequences = [
        {
            'action_name': 'install_system_packages',
            'sequence_order': 10,
            'action_config': {'packages': old_config.get('packages', [])}
        },
        {
            'action_name': 'create_postgresql_user',
            'sequence_order': 20,
            'action_config': {
                'username': '{{workspace.linux_username}}',
                'database': '{{workspace.linux_username}}_odoo'
            }
        },
        # ... convert all config items to actions
    ]
    
    for seq_data in sequences:
        action = TemplateAction.query.filter_by(
            name=seq_data['action_name']
        ).first()
        
        if action:
            sequence = TemplateActionSequence(
                template_id=odoo_template.id,
                action_id=action.id,
                sequence_order=seq_data['sequence_order'],
                action_config=seq_data['action_config']
            )
            db.session.add(sequence)
    
    db.session.commit()
```

### Adım 4: Backwards Compatibility
```python
# Keep old methods for backwards compatibility during transition

def apply_workspace_template_legacy(self, workspace, template):
    """Legacy template application (deprecated)."""
    # Original implementation
    pass

def apply_workspace_template(self, workspace, template, use_v2=True):
    """Apply template with version selection."""
    if use_v2 and self._template_has_action_sequences(template):
        return self.apply_workspace_template_v2(workspace, template)
    else:
        return self.apply_workspace_template_legacy(workspace, template)

def _template_has_action_sequences(self, template):
    """Check if template uses new action-based format."""
    count = TemplateActionSequence.query.filter_by(
        template_id=template.id
    ).count()
    return count > 0
```

---

## 📊 Avantajlar ve Faydalar

### Teknik Avantajlar
✅ **Modülerlik**: Actions yeniden kullanılabilir ve compose edilebilir
✅ **Esneklik**: Yeni action eklemek kod değişikliği gerektirmez
✅ **Debugging**: Her action'ın ayrı log ve execution record'u
✅ **Retry Logic**: Action-level retry ve rollback
✅ **Parallelization**: Bağımsız actionlar paralel çalıştırılabilir
✅ **Testing**: Her action bağımsız test edilebilir
✅ **Versioning**: Template ve action versiyonları yönetilebilir
✅ **Inheritance**: Template'ler birbirinden türetilebilir

### İşlevsel Avantajlar
✅ **Conditional Execution**: Runtime condition'lara göre action çalıştırma
✅ **Progress Tracking**: Fine-grained progress bar ve status
✅ **Error Recovery**: Spesifik action'dan devam edebilme
✅ **Resource Management**: Action-level resource requirement tracking
✅ **Audit Trail**: Detaylı execution history
✅ **User Visibility**: Kullanıcıya hangi action'ın çalıştığını gösterme

### Kullanıcı Deneyimi
✅ **Detaylı Progress**: "Installing PostgreSQL... 2/15 steps"
✅ **Better Errors**: "Failed at step: Clone Odoo Enterprise (attempt 3/3)"
✅ **Resume Capability**: "Resume from failed step" button
✅ **Transparency**: Execution log ile her action'ın ne yaptığını görebilme

---

## 🎯 İmplementasyon Planı

### Faz 1: Temel Altyapı (1 hafta)
- [ ] Database migration (3 tablo)
- [ ] TemplateAction, TemplateActionSequence, WorkspaceActionExecution modelleri
- [ ] ActionHandler base class ve registry
- [ ] ShellActionHandler ve PythonFunctionHandler
- [ ] Unit testler

### Faz 2: Action Executor (1 hafta)
- [ ] ActionExecutor engine
- [ ] Retry logic
- [ ] Condition evaluation
- [ ] Rollback mechanism
- [ ] Integration testler

### Faz 3: Standard Actions Library (1 hafta)
- [ ] System action'ları (package install, user create)
- [ ] Database action'ları (postgres user/db create)
- [ ] Environment action'ları (venv, pip install)
- [ ] Repository action'ları (git clone)
- [ ] Configuration action'ları (settings, launch.json)
- [ ] Seed script'leri

### Faz 4: Template Migration (1 hafta)
- [ ] Odoo template migration
- [ ] Mevcut template'leri action-based'e çevirme
- [ ] Backwards compatibility layer
- [ ] E2E testler

### Faz 5: UI ve API (1 hafta)
- [ ] Template action editor UI
- [ ] Action progress visualization
- [ ] Resume from failed action UI
- [ ] Action execution logs viewer
- [ ] API endpoints

### Faz 6: Advanced Features (opsiyonel)
- [ ] Template inheritance UI
- [ ] Action marketplace/library
- [ ] Parallel action execution
- [ ] Action dependency graph visualization
- [ ] Performance profiling

---

## 📝 Örnek API Endpoints

```python
# GET /api/templates/<id>/actions
# Get all actions for a template
{
  "template_id": 1,
  "name": "Odoo 18.4",
  "total_actions": 12,
  "actions": [
    {
      "sequence_order": 10,
      "action": {
        "id": 1,
        "name": "install_system_packages",
        "display_name": "Sistem Paketlerini Kur",
        "category": "system"
      },
      "config": {
        "packages": ["python3", "postgresql", ...]
      }
    }
  ]
}

# POST /api/workspaces/<id>/actions/resume
# Resume provisioning from failed action
{
  "resume_from_action_id": 45,
  "retry_failed_action": true
}

# GET /api/workspaces/<id>/action-executions
# Get execution history
{
  "workspace_id": 123,
  "total_actions": 12,
  "completed": 8,
  "failed": 1,
  "pending": 3,
  "executions": [
    {
      "action_name": "install_system_packages",
      "status": "completed",
      "duration_seconds": 45,
      "attempts": 1
    },
    {
      "action_name": "clone_git_repository",
      "status": "failed",
      "error": "Connection timeout",
      "attempts": 3
    }
  ]
}
```

---

## 🔐 Güvenlik Considerations

1. **Action Validation**: Kullanıcı tanımlı action'lar için sandbox execution
2. **Permission Checks**: System-level action'lar için sudo validation
3. **Script Injection**: Template variable interpolation için sanitization
4. **Resource Limits**: Timeout ve disk space limits enforcement
5. **Audit Logging**: Tüm action execution'ların loglanması

---

## 📚 Sonuç

Bu action-based sistem, mevcut monolitik template yapısından **modüler, esnek, ve yönetilebilir** bir sisteme geçişi sağlar. 

**Ana Kazançlar:**
- 🔄 Yeniden kullanılabilir action library
- 🎯 Fine-grained progress tracking
- 🛡️ Robust retry ve rollback mechanisms
- 📊 Detaylı execution analytics
- 🧩 Template inheritance ve composition
- 🚀 Gelecekteki genişlemelere hazır mimari

**Implementasyon Riski:** Orta-düşük
- Backwards compatibility layer ile mevcut template'ler çalışmaya devam eder
- Phased rollout ile risk minimize edilir
- Detaylı testing stratejisi ile güvenilirlik sağlanır

**Önerilen Aksiyon:** Faz 1-4'ü 4 haftalık sprint olarak planlayın, Faz 5-6'yı sonraki iterasyonda değerlendirin.
