"""
Traefik configuration manager for dynamic workspace routing.
"""
import os
import yaml
from typing import Dict, Any
from flask import current_app


class TraefikManager:
    """Manages Traefik dynamic configuration for workspaces."""

    def __init__(self, config_dir: str = '/etc/traefik/config'):
        """Initialize TraefikManager.

        Args:
            config_dir: Directory where Traefik dynamic config files are stored
        """
        self.config_dir = config_dir
        self.workspaces_config_file = os.path.join(config_dir, 'workspaces.yml')

    def _load_workspaces_config(self) -> Dict[str, Any]:
        """Load existing workspaces configuration.

        Returns:
            Dictionary with current workspaces configuration
        """
        if not os.path.exists(self.workspaces_config_file):
            return {
                'http': {
                    'routers': {},
                    'services': {},
                    'middlewares': self._get_default_middlewares()
                }
            }

        try:
            with open(self.workspaces_config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
                # Ensure structure exists
                if 'http' not in config:
                    config['http'] = {}
                if 'routers' not in config['http']:
                    config['http']['routers'] = {}
                if 'services' not in config['http']:
                    config['http']['services'] = {}
                if 'middlewares' not in config['http']:
                    config['http']['middlewares'] = self._get_default_middlewares()
                return config
        except Exception as e:
            current_app.logger.error(f"Error loading Traefik config: {str(e)}")
            return {
                'http': {
                    'routers': {},
                    'services': {},
                    'middlewares': self._get_default_middlewares()
                }
            }

    def _save_workspaces_config(self, config: Dict[str, Any]) -> None:
        """Save workspaces configuration to file.

        Args:
            config: Configuration dictionary to save
        """
        try:
            # Ensure directory exists
            os.makedirs(self.config_dir, exist_ok=True)

            with open(self.workspaces_config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            current_app.logger.info(f"Traefik config updated: {self.workspaces_config_file}")
        except Exception as e:
            current_app.logger.error(f"Error saving Traefik config: {str(e)}")
            raise

    def _get_default_middlewares(self) -> Dict[str, Any]:
        """Get default middleware configuration.

        Returns:
            Dictionary with default middlewares
        """
        return {
            'secureHeaders': {
                'headers': {
                    'sslRedirect': True,
                    'browserXssFilter': True,
                    'contentTypeNosniff': True,
                    'forceSTSHeader': True,
                    'stsIncludeSubdomains': True,
                    'stsPreload': True,
                    'stsSeconds': 31536000,
                    'customFrameOptionsValue': 'SAMEORIGIN'
                }
            },
            'rateLimitWorkspace': {
                'rateLimit': {
                    'average': 100,
                    'burst': 50,
                    'period': '1m'
                }
            }
        }

    def add_workspace_route(self, workspace_subdomain: str, port: int) -> Dict[str, Any]:
        """Add Traefik route for a workspace.

        Args:
            workspace_subdomain: Full subdomain (e.g., 'dev.testco')
            port: Code-server port number

        Returns:
            Dictionary with operation result
        """
        try:
            config = self._load_workspaces_config()

            # Sanitize router/service name (replace dots with dashes)
            router_name = f"workspace-{workspace_subdomain.replace('.', '-')}"

            # Add router
            config['http']['routers'][router_name] = {
                'rule': f"Host(`{workspace_subdomain}.youarecoder.com`)",
                'entryPoints': ['websecure'],
                'service': router_name,
                'middlewares': ['secureHeaders', 'rateLimitWorkspace'],
                'tls': {}  # Use default certificate from tls.yml
            }

            # Add service
            config['http']['services'][router_name] = {
                'loadBalancer': {
                    'servers': [
                        {'url': f"http://127.0.0.1:{port}"}
                    ]
                }
            }

            # Save configuration
            self._save_workspaces_config(config)

            current_app.logger.info(f"Added Traefik route: {workspace_subdomain}.youarecoder.com -> 127.0.0.1:{port}")

            return {
                'success': True,
                'router': router_name,
                'url': f"https://{workspace_subdomain}.youarecoder.com"
            }

        except Exception as e:
            current_app.logger.error(f"Error adding Traefik route: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def remove_workspace_route(self, workspace_subdomain: str) -> Dict[str, Any]:
        """Remove Traefik route for a workspace.

        Args:
            workspace_subdomain: Full subdomain (e.g., 'dev.testco')

        Returns:
            Dictionary with operation result
        """
        try:
            config = self._load_workspaces_config()

            # Sanitize router/service name
            router_name = f"workspace-{workspace_subdomain.replace('.', '-')}"

            # Remove router if exists
            if router_name in config['http']['routers']:
                del config['http']['routers'][router_name]

            # Remove service if exists
            if router_name in config['http']['services']:
                del config['http']['services'][router_name]

            # Save configuration
            self._save_workspaces_config(config)

            current_app.logger.info(f"Removed Traefik route: {workspace_subdomain}.youarecoder.com")

            return {
                'success': True,
                'router': router_name
            }

        except Exception as e:
            current_app.logger.error(f"Error removing Traefik route: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def update_workspace_route(self, workspace_subdomain: str, new_port: int) -> Dict[str, Any]:
        """Update Traefik route for a workspace (e.g., port change).

        Args:
            workspace_subdomain: Full subdomain (e.g., 'dev.testco')
            new_port: New code-server port number

        Returns:
            Dictionary with operation result
        """
        try:
            config = self._load_workspaces_config()

            # Sanitize router/service name
            router_name = f"workspace-{workspace_subdomain.replace('.', '-')}"

            # Update service URL
            if router_name in config['http']['services']:
                config['http']['services'][router_name]['loadBalancer']['servers'][0]['url'] = \
                    f"http://127.0.0.1:{new_port}"

                # Save configuration
                self._save_workspaces_config(config)

                current_app.logger.info(f"Updated Traefik route: {workspace_subdomain}.youarecoder.com -> 127.0.0.1:{new_port}")

                return {
                    'success': True,
                    'router': router_name,
                    'port': new_port
                }
            else:
                return {
                    'success': False,
                    'error': f"Router {router_name} not found"
                }

        except Exception as e:
            current_app.logger.error(f"Error updating Traefik route: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def list_workspace_routes(self) -> Dict[str, Any]:
        """List all workspace routes in Traefik configuration.

        Returns:
            Dictionary with all workspace routes
        """
        try:
            config = self._load_workspaces_config()

            routes = []
            for router_name, router_config in config['http']['routers'].items():
                if router_name.startswith('workspace-'):
                    service_config = config['http']['services'].get(router_name, {})
                    server_url = service_config.get('loadBalancer', {}).get('servers', [{}])[0].get('url', '')

                    routes.append({
                        'router': router_name,
                        'rule': router_config.get('rule', ''),
                        'backend': server_url,
                        'tls': router_config.get('tls', {}).get('certResolver', '')
                    })

            return {
                'success': True,
                'routes': routes,
                'count': len(routes)
            }

        except Exception as e:
            current_app.logger.error(f"Error listing Traefik routes: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
