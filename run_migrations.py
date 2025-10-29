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

        # Check if workspace_metrics table exists
        try:
            result = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='workspace_metrics'
            """))
            has_metrics_table = result.fetchone() is not None
            print(f"✓ workspace_metrics table: {'exists' if has_metrics_table else 'missing'}")
        except Exception as e:
            print(f"✗ Error checking workspace_metrics: {e}")
            has_metrics_table = False

        # Import and run migration 006 if needed
        if not has_template_id:
            print("\n📦 Running migration 006: Add workspace templates...")
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "migration_006",
                    "migrations/versions/006_add_workspace_templates.py"
                )
                migration_006 = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration_006)
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
                # Add lifecycle tracking columns
                db.session.execute(text("""
                    ALTER TABLE workspaces
                    ADD COLUMN is_running BOOLEAN NOT NULL DEFAULT false
                """))
                print("  ✓ Added is_running column")

                db.session.execute(text("""
                    ALTER TABLE workspaces
                    ADD COLUMN last_started_at TIMESTAMP
                """))
                print("  ✓ Added last_started_at column")

                db.session.execute(text("""
                    ALTER TABLE workspaces
                    ADD COLUMN last_stopped_at TIMESTAMP
                """))
                print("  ✓ Added last_stopped_at column")

                db.session.execute(text("""
                    ALTER TABLE workspaces
                    ADD COLUMN last_accessed_at TIMESTAMP
                """))
                print("  ✓ Added last_accessed_at column")

                # Add resource management columns
                db.session.execute(text("""
                    ALTER TABLE workspaces
                    ADD COLUMN auto_stop_hours INTEGER NOT NULL DEFAULT 0
                """))
                print("  ✓ Added auto_stop_hours column")

                db.session.execute(text("""
                    ALTER TABLE workspaces
                    ADD COLUMN cpu_limit_percent INTEGER NOT NULL DEFAULT 100
                """))
                print("  ✓ Added cpu_limit_percent column")

                db.session.execute(text("""
                    ALTER TABLE workspaces
                    ADD COLUMN memory_limit_mb INTEGER NOT NULL DEFAULT 2048
                """))
                print("  ✓ Added memory_limit_mb column")

                # Create indexes for lifecycle queries
                db.session.execute(text("""
                    CREATE INDEX ix_workspaces_is_running
                    ON workspaces (is_running)
                """))
                print("  ✓ Created index on is_running")

                db.session.execute(text("""
                    CREATE INDEX ix_workspaces_last_accessed_at
                    ON workspaces (last_accessed_at)
                """))
                print("  ✓ Created index on last_accessed_at")

                db.session.commit()
                print("✅ Migration 007 completed successfully")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Migration 007 failed: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("\n⏭️  Skipping migration 007 (already applied)")

        # Import and run migration 008 if needed
        if not has_metrics_table:
            print("\n📦 Running migration 008: Add workspace metrics...")
            try:
                # Create workspace_metrics table
                db.session.execute(text("""
                    CREATE TABLE workspace_metrics (
                        id SERIAL PRIMARY KEY,
                        workspace_id INTEGER NOT NULL,
                        collected_at TIMESTAMP NOT NULL DEFAULT now(),
                        cpu_percent FLOAT NOT NULL,
                        memory_used_mb INTEGER NOT NULL,
                        memory_percent FLOAT NOT NULL,
                        process_count INTEGER NOT NULL,
                        uptime_seconds INTEGER NOT NULL
                    )
                """))
                print("  ✓ Created workspace_metrics table")

                # Add foreign key
                db.session.execute(text("""
                    ALTER TABLE workspace_metrics
                    ADD CONSTRAINT fk_workspace_metrics_workspace_id
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
                    ON DELETE CASCADE
                """))
                print("  ✓ Added foreign key constraint")

                # Create indexes
                db.session.execute(text("""
                    CREATE INDEX ix_workspace_metrics_workspace_id
                    ON workspace_metrics (workspace_id)
                """))
                print("  ✓ Created index on workspace_id")

                db.session.execute(text("""
                    CREATE INDEX ix_workspace_metrics_collected_at
                    ON workspace_metrics (collected_at)
                """))
                print("  ✓ Created index on collected_at")

                # Composite index for time-range queries
                db.session.execute(text("""
                    CREATE INDEX ix_workspace_metrics_workspace_time
                    ON workspace_metrics (workspace_id, collected_at)
                """))
                print("  ✓ Created composite index on workspace_id and collected_at")

                db.session.commit()
                print("✅ Migration 008 completed successfully")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Migration 008 failed: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("\n⏭️  Skipping migration 008 (already applied)")

        print("\n✅ All migrations completed successfully!")
        return True

if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)
