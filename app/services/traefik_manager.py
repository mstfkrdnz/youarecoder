"""
Traefik configuration manager for dynamic workspace routing.
"""
import os
import yaml
import subprocess
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
                if 'http' not in config or config['http'] is None:
                    config['http'] = {}
                if 'routers' not in config['http'] or config['http']['routers'] is None:
                    config['http']['routers'] = {}
                if 'services' not in config['http'] or config['http']['services'] is None:
                    config['http']['services'] = {}
                if 'middlewares' not in config['http'] or config['http']['middlewares'] is None:
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

    def _generate_htpasswd(self, username: str, password: str) -> str:
        """Generate htpasswd hash for BasicAuth.

        Args:
            username: Username for authentication
            password: Plain text password

        Returns:
            Htpasswd formatted string (username:hash)
        """
        try:
            # Use htpasswd command to generate hash (use full path for systemd service)
            result = subprocess.run(
                ['/usr/bin/htpasswd', '-nbB', username, password],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"htpasswd generation failed: {e.stderr}")
            raise
        except FileNotFoundError:
            current_app.logger.error("htpasswd command not found - install apache2-utils")
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
            },
            'workspaceAuth': {
                'forwardAuth': {
                    'address': 'https://youarecoder.com/api/auth/verify',
                    'trustForwardHeader': True,
                    'authResponseHeaders': ['X-Auth-User', 'X-Auth-User-ID', 'X-Auth-Company'],
                    'authRequestHeaders': ['Cookie'],
                    # Redirect to login page when authentication fails
                    'authResponseHeadersRegex': '^X-Auth-',
                    'addAuthCookiesToResponse': []
                }
            }
        }

    def add_workspace_route(self, workspace_subdomain: str, port: int, username: str = None, password: str = None) -> Dict[str, Any]:
        """Add Traefik route for a workspace with ForwardAuth.

        Args:
            workspace_subdomain: Full subdomain (e.g., 'dev.testco')
            port: Code-server port number
            username: DEPRECATED - kept for backward compatibility
            password: DEPRECATED - kept for backward compatibility

        Returns:
            Dictionary with operation result
        """
        try:
            config = self._load_workspaces_config()

            # Sanitize router/service name (replace dots with dashes)
            router_name = f"workspace-{workspace_subdomain.replace('.', '-')}"

            # Create workspace-specific middleware to preserve original hostname
            workspace_header_middleware = f"{router_name}-headers"
            config['http']['middlewares'][workspace_header_middleware] = {
                'headers': {
                    'customRequestHeaders': {
                        'X-Workspace-Host': f"{workspace_subdomain}.youarecoder.com"
                    }
                }
            }

            # Use ForwardAuth middleware for Flask session-based authentication
            # IMPORTANT: workspace-specific headers middleware MUST be first in the chain
            # so that X-Workspace-Host header is set before ForwardAuth is called
            middlewares = [workspace_header_middleware, 'workspaceAuth', 'secureHeaders', 'rateLimitWorkspace']

            # Add router with high priority to override Flask app wildcard
            config['http']['routers'][router_name] = {
                'rule': f"Host(`{workspace_subdomain}.youarecoder.com`)",
                'entryPoints': ['websecure'],
                'service': router_name,
                'middlewares': middlewares,
                'tls': {},  # Use default certificate from tls.yml
                'priority': 100  # Higher priority than Flask app wildcard (default is 0)
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
            import traceback
            current_app.logger.error(f"Error adding Traefik route: {str(e)}")
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
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

            # Remove workspace-specific headers middleware if exists
            workspace_header_middleware = f"{router_name}-headers"
            if workspace_header_middleware in config['http']['middlewares']:
                del config['http']['middlewares'][workspace_header_middleware]

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
