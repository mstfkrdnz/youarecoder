"""
PostgreSQL Database Action Handler
Creates PostgreSQL databases and users
"""
import subprocess
from typing import Dict, Any
from app.services.action_handlers.base import BaseActionHandler


class PostgreSQLDatabaseActionHandler(BaseActionHandler):
    """Create PostgreSQL database and user"""

    REQUIRED_PARAMETERS = ['database_name']
    OPTIONAL_PARAMETERS = ['username', 'password', 'owner', 'encoding', 'locale']

    DISPLAY_NAME = 'Create PostgreSQL Database'
    CATEGORY = 'database'
    DESCRIPTION = 'Creates PostgreSQL databases with user authentication and permissions'

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create PostgreSQL database.

        Args:
            parameters: {
                'database_name': Name of database to create,
                'username': Optional user to create (default: workspace username),
                'password': Optional password for user,
                'owner': Database owner (default: created user),
                'encoding': Database encoding (default: UTF8),
                'locale': Database locale (default: en_US.UTF-8)
            }

        Returns:
            Dict with database info
        """
        params = self.substitute_variables(parameters)

        db_name = params['database_name']
        username = params.get('username', self.linux_username)
        password = params.get('password')
        owner = params.get('owner', username)
        encoding = params.get('encoding', 'UTF8')
        locale = params.get('locale', 'en_US.UTF-8')

        self.log_info(f"Creating PostgreSQL database: {db_name} (owner: {owner})")

        created_user = False
        created_db = False

        try:
            # Check if user exists, create if not
            check_user = subprocess.run(
                ['sudo', '-u', 'postgres', 'psql', '-tAc',
                 f"SELECT 1 FROM pg_roles WHERE rolname='{username}'"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if check_user.stdout.strip() != '1':
                # Create user
                create_user_cmd = f"CREATE USER {username}"
                if password:
                    create_user_cmd += f" WITH PASSWORD '{password}'"

                subprocess.run(
                    ['sudo', '-u', 'postgres', 'psql', '-c', create_user_cmd],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                created_user = True
                self.log_info(f"Created PostgreSQL user: {username}")
            else:
                self.log_info(f"PostgreSQL user already exists: {username}")

            # Check if database exists
            check_db = subprocess.run(
                ['sudo', '-u', 'postgres', 'psql', '-tAc',
                 f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if check_db.stdout.strip() == '1':
                self.log_info(f"Database already exists: {db_name}")
                return {
                    'success': True,
                    'database_name': db_name,
                    'username': username,
                    'owner': owner,
                    'already_existed': True,
                    'user_created': created_user
                }

            # Create database
            subprocess.run(
                ['sudo', '-u', 'postgres', 'createdb',
                 '-O', owner,
                 '-E', encoding,
                 '-l', locale,
                 db_name],
                check=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            created_db = True
            self.log_info(f"Created database: {db_name}")

            # Grant all privileges
            subprocess.run(
                ['sudo', '-u', 'postgres', 'psql', '-c',
                 f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {username}"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            self.log_info(f"Granted privileges to {username} on {db_name}")

            return {
                'success': True,
                'database_name': db_name,
                'username': username,
                'owner': owner,
                'encoding': encoding,
                'locale': locale,
                'user_created': created_user,
                'database_created': created_db
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"PostgreSQL operation failed: {e.stderr}"
            self.log_error(error_msg)
            raise Exception(error_msg)

    def validate(self, parameters: Dict[str, Any]) -> bool:
        """Validate PostgreSQL parameters"""
        self.validate_parameters(parameters)

        db_name = parameters['database_name']

        if not db_name:
            raise ValueError("Database name cannot be empty")

        # Check valid database name (alphanumeric, underscore, no spaces)
        if not db_name.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Invalid database name: {db_name}")

        # Check if PostgreSQL is available
        try:
            subprocess.run(
                ['sudo', '-u', 'postgres', 'psql', '--version'],
                check=True,
                capture_output=True,
                timeout=10
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ValueError("PostgreSQL is not installed or not accessible")

        return True

    def rollback(self, parameters: Dict[str, Any], execution_result: Dict[str, Any]) -> bool:
        """Drop created database and user"""
        if not execution_result.get('success'):
            return True

        # Don't rollback if already existed
        if execution_result.get('already_existed'):
            return True

        try:
            db_name = execution_result.get('database_name')
            username = execution_result.get('username')
            database_created = execution_result.get('database_created', False)
            user_created = execution_result.get('user_created', False)

            # Drop database if created
            if database_created and db_name:
                try:
                    subprocess.run(
                        ['sudo', '-u', 'postgres', 'dropdb', db_name],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    self.log_info(f"Dropped database: {db_name}")
                except subprocess.CalledProcessError as e:
                    self.log_warning(f"Could not drop database {db_name}: {e.stderr}")

            # Drop user if created
            if user_created and username:
                try:
                    subprocess.run(
                        ['sudo', '-u', 'postgres', 'psql', '-c',
                         f"DROP USER {username}"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    self.log_info(f"Dropped user: {username}")
                except subprocess.CalledProcessError as e:
                    self.log_warning(f"Could not drop user {username}: {e.stderr}")

            return True

        except Exception as e:
            self.log_error(f"Rollback failed: {e}")
            return False
