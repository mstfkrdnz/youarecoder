"""
Completion Message Action Handler
Displays completion message with workspace information
"""
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class CompletionMessageActionHandler(BaseActionHandler):
    """Display workspace provisioning completion message"""

    REQUIRED_PARAMETERS = []
    OPTIONAL_PARAMETERS = ['message', 'include_credentials', 'include_urls']

    DISPLAY_NAME = 'Display Completion Message'
    CATEGORY = 'notification'
    DESCRIPTION = 'Displays workspace provisioning completion message with credentials and URLs'

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Display completion message.

        Args:
            parameters: {
                'message': Optional custom message,
                'include_credentials': Show credentials info (default: True),
                'include_urls': Show workspace URLs (default: True)
            }

        Returns:
            Dict with message content
        """
        params = self.substitute_variables(parameters)

        custom_message = params.get('message', '')
        include_credentials = params.get('include_credentials', True)
        include_urls = params.get('include_urls', True)

        self.log_info("Generating completion message")

        # Build message parts
        message_parts = []

        if custom_message:
            message_parts.append(custom_message)
            message_parts.append('')

        message_parts.append("✅ Workspace provisioning completed successfully!")
        message_parts.append('')
        message_parts.append(f"Workspace: {self.workspace_name}")
        message_parts.append(f"User: {self.linux_username}")

        if include_credentials:
            message_parts.append('')
            message_parts.append("📋 Access Information:")
            message_parts.append(f"  • Username: {self.linux_username}")
            message_parts.append(f"  • Home Directory: {self.home_directory}")

        if include_urls and self.subdomain:
            message_parts.append('')
            message_parts.append("🌐 Workspace URLs:")
            message_parts.append(f"  • Code Editor: https://{self.subdomain}")

        message_parts.append('')
        message_parts.append("🚀 Your workspace is ready to use!")

        full_message = '\n'.join(message_parts)

        # Log the message
        for line in message_parts:
            if line:
                self.log_info(line)

        return {
            'success': True,
            'message': full_message,
            'workspace_name': self.workspace_name,
            'username': self.linux_username,
            'home_directory': self.home_directory,
            'subdomain': self.subdomain
        }

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate completion message parameters"""
        # No required parameters, always valid
        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """No rollback needed for display message"""
        return True
