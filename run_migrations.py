#!/usr/bin/env python3
"""
Manual migration runner for YouAreCoder.
Runs migrations 006 and 007 to add template and lifecycle fields.
"""
from app import create_app, db
from sqlalchemy import text
import sys

def run_migrations():
    """Run pending migrations."""
    app = create_app()

    with app.app_context():
        # Check which migrations need to be run
        print("Checking database schema...")

        # Check if template_id exists in workspaces
        try:
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='workspaces' AND column_name='template_id'
            """))
            has_template_id = result.fetchone() is not None
            print(f"✓ template_id column: {'exists' if has_template_id else 'missing'}")
        except Exception as e:
            print(f"✗ Error checking template_id: {e}")
            has_template_id = False

        # Check if is_running exists in workspaces
        try:
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='workspaces' AND column_name='is_running'
            """))
            has_is_running = result.fetchone() is not None
            print(f"✓ is_running column: {'exists' if has_is_running else 'missing'}")
        except Exception as e:
            print(f"✗ Error checking is_running: {e}")
            has_is_running = False

        # Import and run migration 006 if needed
        if not has_template_id:
            print("\n📦 Running migration 006: Add workspace templates...")
            try:
                from migrations.versions import a006_add_workspace_templates as migration_006
                migration_006.upgrade()
                print("✅ Migration 006 completed successfully")
            except Exception as e:
                print(f"❌ Migration 006 failed: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("\n⏭️  Skipping migration 006 (already applied)")

        # Import and run migration 007 if needed
        if not has_is_running:
            print("\n📦 Running migration 007: Add workspace lifecycle...")
            try:
                from migrations.versions import a007_add_workspace_lifecycle as migration_007
                migration_007.upgrade()
                print("✅ Migration 007 completed successfully")
            except Exception as e:
                print(f"❌ Migration 007 failed: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("\n⏭️  Skipping migration 007 (already applied)")

        print("\n✅ All migrations completed successfully!")
        return True

if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)
